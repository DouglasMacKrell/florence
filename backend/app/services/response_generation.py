import json
import logging

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

    messages = [
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
    try:
        reply = ollama.chat(messages).strip()
    except OllamaError:
        logger.warning("Ollama reply generation failed; using fallback")
        return fallback

    return reply or fallback
