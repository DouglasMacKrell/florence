from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agent.safety import detect_safety_signals
from app.agent.state_machine import ConversationState
from app.config import clear_settings_cache
from app.db.database import Base
from app.db.tables import SessionRecord
from app.models.enums import ConversationState as ConversationStateEnum
from app.models.intake import IntakeRecord, SafetyInfo
from app.services.conversation import (
    STATE_PROMPTS,
    create_session,
    prepare_user_message_turn,
    process_user_message,
)
from app.services.intake_extraction import apply_extraction_patch, extract_with_rules
from app.services.response_generation import EMERGENCY_REPLY, generate_assistant_reply


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


def _seed_pre_consent_intake(db_session, session_id: str) -> None:
    session = db_session.get(SessionRecord, session_id)
    intake = IntakeRecord.model_validate(
        {
            "caller": {
                "name": "Douglas MacKrell",
                "relationship_to_care_recipient": "daughter",
            },
            "care_recipient": {"age": 82},
            "location_preferences": {"postal_code": "11375", "preferred_city": "Queens"},
            "care_needs": {"notes": "help around the house"},
            "timing": {"urgency": "within_30_days"},
            "financial": {"monthly_budget_max": 7000},
            "consent": {"consent_to_store_information": True, "consent_to_contact": None},
        }
    )
    session.current_state = ConversationStateEnum.IDENTIFY_CARE_RECIPIENT.value
    orm = session.intake
    assert orm is not None
    orm.structured_json = intake.model_dump()
    orm.current_state = session.current_state
    db_session.flush()


def test_storage_consent_advances_from_disclosure(db_session) -> None:
    session = create_session(db_session)
    db_session.flush()

    turn = process_user_message(
        db_session,
        session.id,
        "Yes, you have my permission.",
        scripted_reply=True,
    )

    assert turn.intake.consent.consent_to_store_information is True
    assert turn.state == ConversationState.UNDERSTAND_REASON_FOR_CALL.value


def test_follow_up_consent_yes_routes_to_phone_without_repeating_consent(db_session) -> None:
    session = create_session(db_session)
    db_session.flush()
    _seed_pre_consent_intake(db_session, session.id)

    consent_question = "May I have your consent to contact you for updates and provider referrals?"

    def mock_extract(intake: IntakeRecord, content: str, state, history):
        if content.strip().lower() == "yes":
            apply_extraction_patch(intake, {"consent_to_contact": True}, state=state)
        return detect_safety_signals(content)

    mock_llm = MagicMock()
    mock_llm.is_available.return_value = True
    mock_llm.chat.return_value = consent_question

    with (
        patch("app.services.conversation.extract_with_ollama", side_effect=mock_extract),
        patch(
            "app.services.response_generation.get_llm_client",
            return_value=mock_llm,
        ),
    ):
        turn = process_user_message(db_session, session.id, "Yes")

    assert turn.intake.consent.consent_to_contact is True
    assert "consent.consent_to_contact" not in turn.intake.missing_required_fields()
    assert turn.state == ConversationState.COLLECT_CALLER_CONTACT.value
    assert consent_question.lower() not in turn.content.lower()
    assert "phone number" in turn.content.lower()


def test_follow_up_consent_decline_does_not_mark_contact(db_session) -> None:
    session = create_session(db_session)
    db_session.flush()
    _seed_pre_consent_intake(db_session, session.id)

    def mock_extract(intake: IntakeRecord, content: str, state, history):
        apply_extraction_patch(intake, {"consent_to_contact": False}, state=state)
        return detect_safety_signals(content)

    with patch("app.services.conversation.extract_with_ollama", side_effect=mock_extract):
        turn = process_user_message(
            db_session,
            session.id,
            "No, please do not contact me.",
            scripted_reply=True,
        )

    assert turn.intake.consent.consent_to_contact is not True
    assert "consent.consent_to_contact" in turn.intake.missing_required_fields()


def test_capture_follow_up_consent_keeps_share_separate(db_session) -> None:
    intake = IntakeRecord.model_validate(
        {
            "caller": {
                "name": "Jane",
                "phone": "555-123-4567",
                "relationship_to_care_recipient": "daughter",
            },
            "care_recipient": {"age": 82},
            "location_preferences": {"postal_code": "11101"},
            "care_needs": {"notes": "Memory and bathing support"},
            "timing": {"urgency": "within_30_days"},
            "financial": {"monthly_budget_max": 8000},
            "consent": {
                "consent_to_store_information": True,
                "consent_to_contact": True,
                "consent_to_share_with_matched_providers": None,
            },
        }
    )
    extract_with_rules(intake, "Yes", ConversationState.CAPTURE_FOLLOWUP_CONSENT)
    assert intake.consent.consent_to_share_with_matched_providers is True
    assert intake.consent.consent_to_contact is True


def test_emergency_reply_still_bypasses_llm() -> None:
    mock_llm = MagicMock()
    intake = IntakeRecord(safety=SafetyInfo(possible_emergency=True))
    reply = generate_assistant_reply(
        intake=intake,
        state=ConversationState.ASSESS_URGENCY_AND_SAFETY,
        history=[],
        fallback="How soon are you hoping care can start?",
        client=mock_llm,
    )
    assert reply == EMERGENCY_REPLY
    mock_llm.chat.assert_not_called()


def test_streamed_turn_uses_scripted_next_question_after_follow_up_consent(
    db_session,
) -> None:
    session = create_session(db_session)
    db_session.flush()
    _seed_pre_consent_intake(db_session, session.id)

    def mock_extract(intake: IntakeRecord, content: str, state, history):
        apply_extraction_patch(intake, {"consent_to_contact": True}, state=state)
        return detect_safety_signals(content)

    with patch("app.services.conversation.extract_with_ollama", side_effect=mock_extract):
        prepared = prepare_user_message_turn(db_session, session.id, "Yes")

    assert prepared.intake.consent.consent_to_contact is True
    assert prepared.conversation_state == ConversationState.COLLECT_CALLER_CONTACT
    assert prepared.reply_override == STATE_PROMPTS[ConversationState.COLLECT_CALLER_CONTACT]
