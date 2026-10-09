import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agent.state_machine import ConversationState
from app.config import clear_settings_cache
from app.db.database import Base
from app.db.tables import SessionRecord
from app.models.enums import ConversationState as ConversationStateEnum
from app.models.intake import IntakeRecord
from app.services.conversation import create_session, process_user_message
from app.services.intake_summary import SUMMARY_CONFIRMATION_QUESTION
from app.services.provider_loader import load_providers_from_seed


@pytest.fixture()
def db_session(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("ENABLE_OLLAMA", "false")
    clear_settings_cache()

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        clear_settings_cache()


def _qualified_intake() -> IntakeRecord:
    return IntakeRecord.model_validate(
        {
            "caller": {
                "name": "Douglas MacKrell",
                "phone": "555-123-4567",
                "relationship_to_care_recipient": "daughter",
            },
            "care_recipient": {"age": 82},
            "location_preferences": {"postal_code": "11375", "preferred_city": "Queens"},
            "care_needs": {"notes": "help around the house"},
            "timing": {"urgency": "within_30_days"},
            "financial": {"monthly_budget_max": 7000},
            "consent": {
                "consent_to_store_information": True,
                "consent_to_contact": True,
            },
        }
    )


def test_entering_confirm_summary_includes_persisted_intake_summary(db_session) -> None:
    session = create_session(db_session)
    load_providers_from_seed(db_session)
    db_session.flush()

    record = db_session.get(SessionRecord, session.id)
    assert record is not None
    record.current_state = ConversationStateEnum.COLLECT_CALLER_CONTACT.value
    intake = _qualified_intake()
    intake.caller.phone = None
    assert record.intake is not None
    record.intake.structured_json = intake.model_dump()
    db_session.flush()

    turn = process_user_message(db_session, session.id, "555-123-4567")

    assert turn.state == ConversationState.CONFIRM_SUMMARY.value
    assert SUMMARY_CONFIRMATION_QUESTION in turn.content
    assert "11375" in turn.content
    assert "help around the house" in turn.content
    assert "555-123-4567" in turn.content


def test_confirm_summary_yes_advances_to_matching(db_session) -> None:
    session = create_session(db_session)
    load_providers_from_seed(db_session)
    db_session.flush()

    record = db_session.get(SessionRecord, session.id)
    assert record is not None
    record.current_state = ConversationState.CONFIRM_SUMMARY.value
    assert record.intake is not None
    record.intake.structured_json = _qualified_intake().model_dump()
    db_session.flush()

    turn = process_user_message(db_session, session.id, "Yes, that sounds accurate.")

    assert turn.state == ConversationState.MATCH_PROVIDERS.value
    assert turn.matches is not None
    assert len(turn.matches) > 0
