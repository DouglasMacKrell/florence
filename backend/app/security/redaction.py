import copy
import logging
from typing import Any

logger = logging.getLogger(__name__)

SENSITIVE_FIELD_NAMES = frozenset(
    {
        "name",
        "phone",
        "email",
        "caller_phone",
        "structured_json",
        "content",
        "transcript",
        "safety_notes",
        "financial_notes",
        "notes",
    }
)


def redact_value(field_name: str, value: Any) -> Any:
    if value is None:
        return None
    if field_name in SENSITIVE_FIELD_NAMES:
        return "[REDACTED]"
    return value


def redact_intake(intake: dict[str, Any]) -> dict[str, Any]:
    return _redact_object(copy.deepcopy(intake))


def redact_message_content(content: str) -> str:
    return "[REDACTED]" if content else content


def redact_context(context: dict[str, Any]) -> dict[str, Any]:
    return _redact_object(copy.deepcopy(context))


def safe_log(message: str, **context: Any) -> None:
    from app.config import get_settings

    settings = get_settings()
    payload = redact_context(context) if settings.redact_logs else context
    logger.info("%s | %s", message, payload)


def _redact_object(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _redact_field(key, nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [_redact_object(item) for item in value]
    return value


def _redact_field(field_name: str, value: Any) -> Any:
    if field_name in SENSITIVE_FIELD_NAMES:
        return redact_value(field_name, value)
    return _redact_object(value)
