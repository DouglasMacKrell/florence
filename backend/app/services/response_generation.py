import json
import logging
from collections.abc import Iterator

from app.agent.prompts import RESPONSE_PROMPT, SYSTEM_PROMPT, state_instruction
from app.config import get_settings
from app.models.enums import ConversationState
from app.models.intake import IntakeRecord
from app.services.llm_client import LlmClient, LlmError, get_llm_client

logger = logging.getLogger(__name__)

EMERGENCY_REPLY = (
    "It sounds like this may need immediate help. If someone may be in danger, "
    "please contact local emergency services right away. I can stay with you, "
    "but I cannot provide emergency medical care."
)

_REINTRO_PHRASES = (
    "i'm florence",
    "i am florence",
    "hi! i'm florence",
    "hello! i'm florence",
    "hi, i'm florence",
    "hello, i'm florence",
)

_CALLBACK_PHRASES = (
    "call you back",
    "call back later",
    "reach out to you directly",
    "get in touch with you directly",
    "call you later",
)


def sanitize_assistant_reply(reply: str, state: ConversationState, fallback: str) -> str:
    if state == ConversationState.GREETING:
        return reply
    lowered = reply.lower()
    if any(phrase in lowered for phrase in _REINTRO_PHRASES):
        logger.info("Replacing repeated Florence introduction with scripted fallback")
        return fallback
    if state != ConversationState.COLLECT_CALLER_CONTACT and any(
        phrase in lowered for phrase in _CALLBACK_PHRASES
    ):
        logger.info("Replacing callback-style phrasing with scripted fallback")
        return fallback
    return reply


def generate_assistant_reply(
    *,
    intake: IntakeRecord,
    state: ConversationState,
    history: list[dict[str, str]],
    fallback: str,
    client: LlmClient | None = None,
    scripted_only: bool = False,
) -> str:
    if intake.safety.possible_emergency or intake.safety.immediate_danger:
        return EMERGENCY_REPLY

    if scripted_only:
        return fallback

    settings = get_settings()
    if not settings.enable_ollama:
        return fallback

    llm = client or get_llm_client()
    if not llm.is_available():
        logger.info("LLM unavailable; using scripted fallback reply")
        return fallback

    messages = _reply_messages(intake=intake, state=state, history=history, fallback=fallback)
    try:
        reply = llm.chat(messages).strip()
    except LlmError:
        logger.warning("LLM reply generation failed; using fallback")
        return fallback

    return sanitize_assistant_reply(reply or fallback, state, fallback)


def stream_text_chunks(text: str) -> Iterator[str]:
    words = text.split()
    for index, word in enumerate(words):
        yield word if index == 0 else f" {word}"


def _reply_messages(
    *,
    intake: IntakeRecord,
    state: ConversationState,
    history: list[dict[str, str]],
    fallback: str,
) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": RESPONSE_PROMPT},
        {
            "role": "system",
            "content": state_instruction(state.value, intake),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "current_intake": intake.model_dump(),
                    "conversation": history[-8:],
                    "fallback_reply": fallback,
                }
            ),
        },
    ]


def stream_assistant_reply(
    *,
    intake: IntakeRecord,
    state: ConversationState,
    history: list[dict[str, str]],
    fallback: str,
    client: LlmClient | None = None,
) -> Iterator[str]:
    if intake.safety.possible_emergency or intake.safety.immediate_danger:
        yield from stream_text_chunks(EMERGENCY_REPLY)
        return

    settings = get_settings()
    if not settings.enable_ollama:
        yield from stream_text_chunks(fallback)
        return

    llm = client or get_llm_client()
    if not llm.is_available():
        logger.info("LLM unavailable; streaming scripted fallback reply")
        yield from stream_text_chunks(fallback)
        return

    messages = _reply_messages(intake=intake, state=state, history=history, fallback=fallback)
    try:
        chunks = list(llm.chat_stream(messages))
    except LlmError:
        logger.warning("LLM reply streaming failed; using fallback")
        yield from stream_text_chunks(fallback)
        return

    if not chunks:
        yield from stream_text_chunks(fallback)
        return

    yield from chunks


def finalize_assistant_reply(
    reply: str,
    *,
    state: ConversationState,
    fallback: str,
) -> str:
    return sanitize_assistant_reply(reply, state, fallback)
