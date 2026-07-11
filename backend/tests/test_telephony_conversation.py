from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agent.state_machine import ConversationState, advance_through_satisfied_states
from app.config import clear_settings_cache
from app.db.database import Base
from app.models.intake import IntakeRecord
from app.services.conversation import STATE_PROMPTS, create_session, process_user_message
from app.services.intake_extraction import extract_with_rules


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


def test_advance_through_satisfied_states_skips_completed_stages() -> None:
    intake = IntakeRecord()
    intake.consent.consent_to_store_information = True
    intake.care_needs.notes = "Father fell and needs help at home."

    state = advance_through_satisfied_states(ConversationState.DISCLOSURE_AND_CONSENT, intake)
    assert state == ConversationState.IDENTIFY_CARE_RECIPIENT


def test_extract_with_rules_accepts_city_only_location() -> None:
    intake = IntakeRecord()
    extract_with_rules(
        intake,
        "New York City.",
        ConversationState.COLLECT_LOCATION_REQUIREMENTS,
    )
    assert intake.location_preferences.preferred_city == "New York City"
    assert intake._has_location() is True


def test_extract_with_rules_captures_parent_relationship() -> None:
    intake = IntakeRecord()
    extract_with_rules(
        intake,
        "I'm looking for care for my father.",
        ConversationState.UNDERSTAND_REASON_FOR_CALL,
    )
    assert intake.caller.relationship_to_care_recipient == "family member"


def test_telephony_scripted_turn_skips_ollama_extraction(db_session) -> None:
    session = create_session(db_session)
    db_session.flush()

    with patch("app.services.conversation.extract_with_ollama") as mock_ollama:
        turn = process_user_message(
            db_session,
            session.id,
            "Yes, you may store my information.",
            scripted_reply=True,
        )

    mock_ollama.assert_not_called()
    assert turn.content == STATE_PROMPTS[ConversationState.UNDERSTAND_REASON_FOR_CALL]


def test_telephony_scripted_turn_advances_past_already_collected_fields(db_session) -> None:
    session = create_session(db_session)
    db_session.flush()

    process_user_message(
        db_session,
        session.id,
        "Yes, you may store my information.",
        scripted_reply=True,
    )
    turn = process_user_message(
        db_session,
        session.id,
        "My father is 82 and needs help with bathing and meals after a fall.",
        scripted_reply=True,
    )

    assert turn.state == ConversationState.ASSESS_URGENCY_AND_SAFETY.value
    assert turn.content == STATE_PROMPTS[ConversationState.ASSESS_URGENCY_AND_SAFETY]
