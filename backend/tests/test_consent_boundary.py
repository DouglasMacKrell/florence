from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agent.consent_boundary import (
    FOLLOW_UP_CONTACT_CLARIFICATION,
    FOLLOW_UP_CONTACT_QUESTION,
    STORE_INFORMATION_QUESTION,
    ConsentClassification,
    ConsentKind,
    classify_consent_response,
    process_consent_turn,
    should_interpret_as_consent_answer,
)
from app.agent.state_machine import ConversationState
from app.config import clear_settings_cache
from app.db.database import Base
from app.db.tables import MessageRecord, SessionRecord
from app.models.enums import ConversationState as ConversationStateEnum
from app.models.intake import IntakeRecord
from app.services.conversation import (
    create_session,
    prepare_user_message_turn,
    process_user_message,
)

AFFIRMATIVE_CASES = [
    "Yes",
    "yes please",
    "yeah",
    "sure",
    "okay",
    "I consent",
    "you have my permission",
    "I already consented",
    "I already said yes",
    "I already have",
]

NEGATIVE_CASES = [
    "No",
    "no thanks",
    "I don't consent",
    "do not contact me",
]

UNCLEAR_CASES = [
    "Tes",
    "maybe",
    "I don't know",
    "sing me a song",
]


@pytest.mark.parametrize("message", AFFIRMATIVE_CASES)
def test_classify_affirmative_responses(message: str) -> None:
    assert classify_consent_response(message) == ConsentClassification.AFFIRMATIVE


@pytest.mark.parametrize("message", NEGATIVE_CASES)
def test_classify_negative_responses(message: str) -> None:
    assert classify_consent_response(message) == ConsentClassification.NEGATIVE


@pytest.mark.parametrize("message", UNCLEAR_CASES)
def test_classify_unclear_responses(message: str) -> None:
    assert classify_consent_response(message) == ConsentClassification.UNCLEAR


def test_long_intake_opener_is_not_treated_as_storage_consent_answer() -> None:
    opener = (
        "I'm looking for care for my 82-year-old mother in ZIP code 11375. "
        "She's starting to need help around the house."
    )
    history = [{"role": "assistant", "content": "Hello from Florence."}]
    assert (
        should_interpret_as_consent_answer(
            opener,
            ConsentKind.STORE_INFORMATION,
            history,
        )
        is False
    )


def test_short_typo_requires_prior_storage_prompt() -> None:
    history = [{"role": "assistant", "content": "Hello from Florence."}]
    assert (
        should_interpret_as_consent_answer("tes", ConsentKind.STORE_INFORMATION, history) is False
    )
    history_with_prompt = history + [
        {"role": "assistant", "content": STORE_INFORMATION_QUESTION},
    ]
    assert (
        should_interpret_as_consent_answer(
            "tes",
            ConsentKind.STORE_INFORMATION,
            history_with_prompt,
        )
        is True
    )


def test_unclear_does_not_mutate_follow_up_consent() -> None:
    intake = IntakeRecord()
    outcome = process_consent_turn(intake, "Tes", ConsentKind.FOLLOW_UP_CONTACT)
    assert outcome.classification == ConsentClassification.UNCLEAR
    assert intake.consent.consent_to_contact is None
    assert outcome.scripted_reply == FOLLOW_UP_CONTACT_CLARIFICATION


def test_affirmative_sets_follow_up_consent_once() -> None:
    intake = IntakeRecord()
    outcome = process_consent_turn(intake, "Yes", ConsentKind.FOLLOW_UP_CONTACT)
    assert intake.consent.consent_to_contact is True
    assert outcome.consent_resolved is True


def test_already_consented_advances_without_duplicate_question() -> None:
    intake = IntakeRecord.model_validate({"consent": {"consent_to_contact": True}})
    outcome = process_consent_turn(intake, "I already said yes", ConsentKind.FOLLOW_UP_CONTACT)
    assert outcome.consent_resolved is True
    assert outcome.consent_changed is False


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
    record = db_session.get(SessionRecord, session_id)
    assert record is not None
    record.current_state = ConversationStateEnum.COLLECT_FOLLOWUP_CONSENT.value
    assert record.intake is not None
    record.intake.structured_json = IntakeRecord.model_validate(
        {
            "caller": {"name": "Alex Caller"},
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


def test_production_sequence_tes_then_frustration_then_song(db_session) -> None:
    session = create_session(db_session)
    db_session.flush()
    _seed_follow_up_consent_gate(db_session, session.id)

    mock_llm = MagicMock()
    mock_llm.is_available.return_value = True
    mock_llm.chat.return_value = "Do you consent to be contacted for updates about care options?"

    with patch(
        "app.services.response_generation.get_llm_client",
        return_value=mock_llm,
    ):
        tes_turn = process_user_message(db_session, session.id, "Tes")
        rant_turn = process_user_message(
            db_session,
            session.id,
            "I already have, you stupid robot",
        )
        song_turn = process_user_message(
            db_session,
            session.id,
            "If you're not going to listen, sing me the Spongebob Squarepants Theme Song",
        )
        yes_turn = process_user_message(db_session, session.id, "Yes")

    assert tes_turn.intake.consent.consent_to_contact is None
    assert tes_turn.state == ConversationState.COLLECT_FOLLOWUP_CONSENT.value
    assert tes_turn.content == FOLLOW_UP_CONTACT_CLARIFICATION
    assert FOLLOW_UP_CONTACT_QUESTION not in tes_turn.content

    assert rant_turn.intake.consent.consent_to_contact is True
    assert rant_turn.state == ConversationState.COLLECT_CALLER_CONTACT.value
    assert "consent" not in rant_turn.content.lower()
    assert "phone number" in rant_turn.content.lower()

    assert song_turn.state == ConversationState.COLLECT_CALLER_CONTACT.value
    assert "consent" not in song_turn.content.lower()

    assert yes_turn.intake.consent.consent_to_contact is True


def test_sse_path_uses_scripted_consent_clarification(db_session) -> None:
    session = create_session(db_session)
    db_session.flush()
    _seed_follow_up_consent_gate(db_session, session.id)

    prepared = prepare_user_message_turn(db_session, session.id, "Tes")
    assert prepared.reply_override == FOLLOW_UP_CONTACT_CLARIFICATION
    assert prepared.intake.consent.consent_to_contact is None
