import json
import logging
from collections.abc import Iterator

from app.agent.prompts import RESPONSE_PROMPT, SYSTEM_PROMPT, state_instruction
from app.config import get_settings
from app.models.enums import ConversationState
from app.models.intake import IntakeRecord
from app.services.ollama import OllamaClient, OllamaError

logger = logging.getLogger(__name__)

EMERGENCY_REPLY = (
    "It sounds like this may need immediate help. If someone may be in danger, "
    "please contact local emergency services right away. I can stay with you, "
    "but I cannot provide emergency medical care."
)


def generate_assistant_reply(
    *,
    intake: IntakeRecord,
    state: ConversationState,
    history: list[dict[str, str]],
    fallback: str,
    client: OllamaClient | None = None,
) -> str:
    if intake.safety.possible_emergency or intake.safety.immediate_danger:
        return EMERGENCY_REPLY

    settings = get_settings()
    if not settings.enable_ollama:
        return fallback

    ollama = client or OllamaClient()
    if not ollama.is_available():
        logger.info("Ollama unavailable; using scripted fallback reply")
        return fallback

    messages = _reply_messages(intake=intake, state=state, history=history, fallback=fallback)
    try:
        reply = ollama.chat(messages).strip()
    except OllamaError:
        logger.warning("Ollama reply generation failed; using fallback")
        return fallback

    return reply or fallback


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
            "content": state_instruction(state.value, intake.missing_required_fields()),
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
    client: OllamaClient | None = None,
) -> Iterator[str]:
    if intake.safety.possible_emergency or intake.safety.immediate_danger:
        yield from stream_text_chunks(EMERGENCY_REPLY)
        return

    settings = get_settings()
    if not settings.enable_ollama:
        yield from stream_text_chunks(fallback)
        return

    ollama = client or OllamaClient()
    if not ollama.is_available():
        logger.info("Ollama unavailable; streaming scripted fallback reply")
        yield from stream_text_chunks(fallback)
        return

    messages = _reply_messages(intake=intake, state=state, history=history, fallback=fallback)
    try:
        chunks = list(ollama.chat_stream(messages))
    except OllamaError:
        logger.warning("Ollama reply streaming failed; using fallback")
        yield from stream_text_chunks(fallback)
        return

    if not chunks:
        yield from stream_text_chunks(fallback)
        return

    yield from chunks
