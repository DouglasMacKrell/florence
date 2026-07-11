from app.models.enums import ConversationState
from app.services.response_generation import sanitize_assistant_reply


def test_sanitize_replaces_repeated_intro_with_fallback() -> None:
    reply = sanitize_assistant_reply(
        "Hi! I'm Florence. Could you tell me more about your father?",
        ConversationState.UNDERSTAND_REASON_FOR_CALL,
        "Could you tell me what has been happening?",
    )
    assert reply == "Could you tell me what has been happening?"


def test_sanitize_keeps_greeting_intro() -> None:
    greeting = "Thank you for reaching out. I'm Florence, a care-navigation assistant."
    reply = sanitize_assistant_reply(
        greeting,
        ConversationState.GREETING,
        greeting,
    )
    assert reply == greeting
