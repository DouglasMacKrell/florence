from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agent.consent_boundary import (
    FOLLOW_UP_CONTACT_CLARIFICATION,
    FOLLOW_UP_CONTACT_QUESTION,
)
from app.config import clear_settings_cache
from app.db.database import Base
from app.db.tables import SessionRecord
from app.models.intake import IntakeRecord
from app.services.conversation import (
    create_session,
    prepare_user_message_turn,
    process_user_message,
)
from app.services.intake_summary import build_intake_confirmation_message

OPENING = (
    "I'm looking for care for my 82-year-old mother in ZIP code 11375. "
    "She's starting to need help around the house."
)


@pytest.fixture()
def db_session(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("ENABLE_OLLAMA", "true")
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


def _seed_follow_up_consent_gate(db_session, session_id: str) -> None:
    from app.db.tables import MessageRecord, SessionRecord
    from app.models.enums import ConversationState as ConversationStateEnum

    record = db_session.get(SessionRecord, session_id)
    assert record is not None
    record.current_state = ConversationStateEnum.COLLECT_FOLLOWUP_CONSENT.value
    assert record.intake is not None
    record.intake.structured_json = IntakeRecord.model_validate(
        {
            "care_recipient": {"age": 82, "relationship_descriptor": "mother"},
            "location_preferences": {"postal_code": "11375"},
            "care_needs": {"notes": "help around the house"},
            "timing": {"urgency": "within_30_days"},
            "financial": {"monthly_budget_max": 7000},
            "consent": {"consent_to_store_information": True, "consent_to_contact": None},
        }
    ).model_dump()
    db_session.add(
        MessageRecord(
            session_id=session_id,
            role="assistant",
            content=FOLLOW_UP_CONTACT_QUESTION,
        )
    )
    db_session.flush()


def test_unclear_consent_turn_skips_extraction_even_when_llm_returns_name(
    db_session,
) -> None:
    session = create_session(db_session)
    db_session.flush()
    _seed_follow_up_consent_gate(db_session, session.id)

    record = db_session.get(SessionRecord, session.id)
    assert record is not None and record.intake is not None
    before = IntakeRecord.model_validate(record.intake.structured_json)
    mock_llm = MagicMock()
    mock_llm.is_available.return_value = True
    mock_llm.chat_json.return_value = {"caller_name": "tes"}

    with patch("app.services.intake_extraction.get_llm_client", return_value=mock_llm):
        prepared = prepare_user_message_turn(db_session, session.id, "tes")

    after = prepared.intake
    assert prepared.reply_override == FOLLOW_UP_CONTACT_CLARIFICATION
    assert after.consent.consent_to_contact is None
    assert after.caller.name is None
    assert after.model_dump() == before.model_dump()


def test_end_to_end_opener_through_summary_without_tes_as_name(
    db_session, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services.provider_loader import load_providers_from_seed

    monkeypatch.setenv("ENABLE_OLLAMA", "false")
    clear_settings_cache()

    load_providers_from_seed(db_session)
    session = create_session(db_session)
    db_session.flush()
    session_id = session.id

    steps = [
        OPENING,
        "yes",
        "within the next month",
        "11375 works for us.",
        "Our budget is about 7000 dollars per month.",
        "No special preferences.",
        "I make the decisions with my siblings.",
        "tes",
        "yes",
        "Douglas MacKrell",
        "347-495-1109",
        "Yes, that sounds accurate.",
    ]

    last = None
    for content in steps:
        last = process_user_message(db_session, session_id, content)

    assert last is not None
    intake = last.intake
    assert intake.caller.name == "Douglas MacKrell"
    assert intake.caller.phone is not None
    summary = build_intake_confirmation_message(intake)
    assert "tes —" not in summary
    assert "Douglas MacKrell" in summary
    assert "11375" in summary
    assert "82" in summary
