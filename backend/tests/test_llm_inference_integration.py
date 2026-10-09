from unittest.mock import MagicMock

import pytest

from app.models.enums import ConversationState
from app.models.intake import IntakeRecord, SafetyInfo
from app.services.intake_extraction import extract_with_ollama
from app.services.llm_client import LlmError
from app.services.response_generation import (
    EMERGENCY_REPLY,
    generate_assistant_reply,
    stream_assistant_reply,
)


def test_emergency_reply_does_not_call_llm() -> None:
    mock_llm = MagicMock()
    intake = IntakeRecord(safety=SafetyInfo(possible_emergency=True))
    reply = generate_assistant_reply(
        intake=intake,
        state=ConversationState.ASSESS_URGENCY_AND_SAFETY,
        history=[],
        fallback="Fallback text",
        client=mock_llm,
    )
    assert reply == EMERGENCY_REPLY
    mock_llm.chat.assert_not_called()
    mock_llm.is_available.assert_not_called()


def test_stream_emergency_does_not_call_llm() -> None:
    mock_llm = MagicMock()
    intake = IntakeRecord(safety=SafetyInfo(immediate_danger=True))
    chunks = list(
        stream_assistant_reply(
            intake=intake,
            state=ConversationState.ASSESS_URGENCY_AND_SAFETY,
            history=[],
            fallback="Fallback text",
            client=mock_llm,
        )
    )
    assert "".join(chunks) == EMERGENCY_REPLY
    mock_llm.chat_stream.assert_not_called()


def test_llm_failure_falls_back_to_scripted_reply(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_OLLAMA", "true")
    from app.config import clear_settings_cache

    clear_settings_cache()
    mock_llm = MagicMock()
    mock_llm.is_available.return_value = True
    mock_llm.chat.side_effect = LlmError("upstream error")
    fallback = "Scripted fallback"
    reply = generate_assistant_reply(
        intake=IntakeRecord(),
        state=ConversationState.UNDERSTAND_REASON_FOR_CALL,
        history=[],
        fallback=fallback,
        client=mock_llm,
    )
    assert reply == fallback


def test_extraction_llm_failure_returns_none_for_rules_fallback() -> None:
    mock_llm = MagicMock()
    mock_llm.chat_json.side_effect = LlmError("bad json")
    result = extract_with_ollama(
        IntakeRecord(),
        "My name is Jane",
        ConversationState.GREETING,
        [],
        client=mock_llm,
    )
    assert result is None


def test_groq_stream_maps_to_token_chunks() -> None:
    mock_llm = MagicMock()
    mock_llm.is_available.return_value = True
    mock_llm.chat_stream.return_value = iter(["One ", "two ", "three"])

    chunks = list(
        stream_assistant_reply(
            intake=IntakeRecord(),
            state=ConversationState.UNDERSTAND_REASON_FOR_CALL,
            history=[{"role": "user", "content": "hello"}],
            fallback="Fallback",
            client=mock_llm,
        )
    )
    assert chunks == ["One ", "two ", "three"]
