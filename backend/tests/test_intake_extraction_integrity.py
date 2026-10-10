from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import clear_settings_cache
from app.db.database import Base
from app.models.enums import ConversationState
from app.models.intake import IntakeRecord
from app.services.conversation import create_session, process_user_message
from app.services.intake_extraction import apply_extraction_patch, extract_with_rules
from app.services.intake_summary import build_intake_confirmation_message
from app.services.provider_loader import load_providers_from_seed


def test_mother_in_zip_message_sets_recipient_not_caller_as_daughter() -> None:
    intake = IntakeRecord()
    message = (
        "I'm looking for care for my 82-year-old mother in ZIP code 11375. "
        "She's starting to need help around the house."
    )
    extract_with_rules(intake, message, ConversationState.DISCLOSURE_AND_CONSENT)

    assert intake.care_recipient.relationship_descriptor == "mother"
    assert intake.care_recipient.age == 82
    assert intake.location_preferences.postal_code == "11375"
    assert intake.caller.relationship_to_care_recipient in {None, "family member", "child"}
    assert intake.care_needs.notes is not None


def test_consent_typo_does_not_become_caller_name_at_follow_up_gate() -> None:
    intake = IntakeRecord()
    extract_with_rules(
        intake,
        "tes",
        ConversationState.COLLECT_FOLLOWUP_CONSENT,
        skip_consent_fields=True,
    )
    assert intake.caller.name is None


def test_later_name_answer_does_not_overwrite_location_or_relationship() -> None:
    intake = IntakeRecord.model_validate(
        {
            "caller": {"relationship_to_care_recipient": "family member"},
            "care_recipient": {"age": 82, "relationship_descriptor": "mother"},
            "location_preferences": {"postal_code": "11375"},
            "care_needs": {"notes": "help around the house"},
        }
    )
    extract_with_rules(intake, "Cheeks O'Plenty", ConversationState.UNDERSTAND_DECISION_PROCESS)

    assert intake.caller.name == "Cheeks O'Plenty"
    assert intake.location_preferences.postal_code == "11375"
    assert intake.location_preferences.preferred_city is None
    assert intake.care_recipient.relationship_descriptor == "mother"


def test_llm_patch_cannot_overwrite_city_with_caller_name() -> None:
    intake = IntakeRecord.model_validate(
        {
            "caller": {"name": "Cheeks O'Plenty"},
            "location_preferences": {"postal_code": "11375"},
        }
    )
    apply_extraction_patch(
        intake,
        {"preferred_city": "Cheeks O'Plenty"},
        state=ConversationState.COLLECT_FINANCIAL_REQUIREMENTS,
    )

    assert intake.location_preferences.preferred_city is None


def test_llm_patch_does_not_replace_existing_postal_code_from_unrelated_turn() -> None:
    intake = IntakeRecord.model_validate({"location_preferences": {"postal_code": "11375"}})
    apply_extraction_patch(
        intake,
        {"postal_code": "99999", "preferred_city": "Cheeks O'Plenty"},
        state=ConversationState.COLLECT_FINANCIAL_REQUIREMENTS,
    )

    assert intake.location_preferences.postal_code == "11375"
    assert intake.location_preferences.preferred_city is None


def test_timing_normalization_keeps_single_clean_phrase() -> None:
    intake = IntakeRecord()
    extract_with_rules(
        intake,
        "By the end of the month. November 1st.",
        ConversationState.ASSESS_URGENCY_AND_SAFETY,
    )
    assert intake.timing.urgency == "By the end of the month"


def test_acceptance_style_summary_is_readable_and_deterministic() -> None:
    intake = IntakeRecord.model_validate(
        {
            "caller": {
                "name": "Cheeks O'Plenty",
                "phone": "9875553456",
                "relationship_to_care_recipient": "family member",
            },
            "care_recipient": {"age": 82, "relationship_descriptor": "mother"},
            "location_preferences": {"postal_code": "11375"},
            "care_needs": {"notes": "She's starting to need help around the house"},
            "timing": {"urgency": "By the end of the month"},
            "financial": {"monthly_budget_max": 500},
            "consent": {"consent_to_contact": True},
        }
    )

    summary = build_intake_confirmation_message(intake)

    assert "82-year-old mother" in summary
    assert "ZIP code 11375" in summary
    assert "987-555-3456" in summary
    assert "Cheeks O'Plenty" in summary
    assert "Help is needed with" not in summary
    assert ".." not in summary
    assert "Your daughter is" not in summary
    assert "near Cheeks" not in summary
    assert summary.count("by the end of the month") == 1


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


def test_integration_sequence_preserves_intake_and_summary(db_session) -> None:
    session = create_session(db_session)
    load_providers_from_seed(db_session)
    db_session.flush()

    opening = (
        "I'm looking for care for my 82-year-old mother in ZIP code 11375. "
        "She's starting to need help around the house."
    )

    def mock_extract(intake, content, state, history):
        extract_with_rules(intake, content, state)
        from app.agent.safety import detect_safety_signals

        return detect_safety_signals(content)

    with patch("app.services.conversation.extract_with_ollama", side_effect=mock_extract):
        process_user_message(db_session, session.id, opening)
        process_user_message(db_session, session.id, "Yes, you have my permission.")
        process_user_message(db_session, session.id, "By the end of the month.")
        process_user_message(db_session, session.id, "500")
        process_user_message(db_session, session.id, "Yes")
        process_user_message(db_session, session.id, "My name is Cheeks O'Plenty.")
        process_user_message(db_session, session.id, "9875553456")
        summary_turn = process_user_message(db_session, session.id, "Yes, that's accurate.")

    intake = summary_turn.intake
    assert intake.care_recipient.relationship_descriptor == "mother"
    assert intake.location_preferences.preferred_city is None
    assert intake.caller.name == "Cheeks O'Plenty"
    assert intake.caller.phone == "9875553456"
    assert intake.financial.monthly_budget_max == 500
    assert "82-year-old mother" in build_intake_confirmation_message(intake)
    assert "Cheeks O'Plenty" in build_intake_confirmation_message(intake)
