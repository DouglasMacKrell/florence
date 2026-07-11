import json
import re
from typing import Any

from app.agent.prompts import EXTRACTION_PROMPT
from app.agent.safety import SafetySignals, detect_safety_signals
from app.models.enums import ConversationState
from app.models.intake import IntakeRecord
from app.services.ollama import OllamaClient, OllamaError


def apply_extraction_patch(intake: IntakeRecord, patch: dict[str, Any]) -> None:
    if patch.get("caller_name"):
        intake.caller.name = str(patch["caller_name"])
    if patch.get("caller_phone"):
        intake.caller.phone = str(patch["caller_phone"])
    if patch.get("caller_email"):
        intake.caller.email = str(patch["caller_email"])
    if patch.get("relationship"):
        intake.caller.relationship_to_care_recipient = str(patch["relationship"])
    if patch.get("care_recipient_name"):
        intake.care_recipient.name = str(patch["care_recipient_name"])
    if patch.get("care_recipient_age") is not None:
        intake.care_recipient.age = int(patch["care_recipient_age"])
    if patch.get("care_notes"):
        intake.care_needs.notes = str(patch["care_notes"])
    if patch.get("requested_care_types"):
        values = patch["requested_care_types"]
        if isinstance(values, list):
            intake.care_needs.requested_care_types = [str(item) for item in values]
    if patch.get("urgency"):
        intake.timing.urgency = str(patch["urgency"])
    if patch.get("postal_code"):
        intake.location_preferences.postal_code = str(patch["postal_code"])
    if patch.get("preferred_city"):
        intake.location_preferences.preferred_city = str(patch["preferred_city"])
    if patch.get("preferred_state"):
        intake.location_preferences.preferred_state = str(patch["preferred_state"])
    if patch.get("budget_min") is not None:
        intake.financial.monthly_budget_min = int(patch["budget_min"])
    if patch.get("budget_max") is not None:
        intake.financial.monthly_budget_max = int(patch["budget_max"])
    if patch.get("payment_sources") and isinstance(patch["payment_sources"], list):
        intake.financial.payment_sources = [str(item) for item in patch["payment_sources"]]
    if patch.get("memory_concerns") is not None:
        intake.care_needs.memory_concerns = bool(patch["memory_concerns"])
    if patch.get("overnight_support_needed") is not None:
        intake.care_needs.overnight_support_needed = bool(patch["overnight_support_needed"])
    if patch.get("consent_to_store") is not None:
        intake.consent.consent_to_store_information = bool(patch["consent_to_store"])
    if patch.get("consent_to_contact") is not None:
        intake.consent.consent_to_contact = bool(patch["consent_to_contact"])
    if patch.get("consent_to_share") is not None:
        intake.consent.consent_to_share_with_matched_providers = bool(patch["consent_to_share"])
    if patch.get("private_room_required") is not None:
        intake.preferences.private_room_required = bool(patch["private_room_required"])
    if patch.get("language_preferences") and isinstance(patch["language_preferences"], list):
        intake.preferences.language_preferences = [
            str(item) for item in patch["language_preferences"]
        ]


def extract_with_rules(
    intake: IntakeRecord, content: str, state: ConversationState
) -> SafetySignals:
    _apply_simple_extraction(intake, content, state)
    signals = detect_safety_signals(content)
    _apply_safety_signals(intake, signals)
    return signals


def _apply_simple_extraction(intake: IntakeRecord, content: str, state: ConversationState) -> None:
    lowered = content.lower().strip()
    if lowered.startswith("yes") or lowered in {"sure", "ok", "okay"}:
        if state == ConversationState.DISCLOSURE_AND_CONSENT:
            intake.consent.consent_to_store_information = True
        elif state == ConversationState.CAPTURE_FOLLOWUP_CONSENT:
            intake.consent.consent_to_share_with_matched_providers = True
            intake.consent.consent_to_contact = True

    if "@" in content and not intake.caller.email:
        intake.caller.email = content.strip()

    digits = "".join(ch for ch in content if ch.isdigit())
    phone_match = re.search(
        r"(?:\+1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}",
        content,
    )
    if phone_match and not intake.caller.phone:
        intake.caller.phone = phone_match.group(0).strip()
    elif len(digits) in {10, 11} and not intake.caller.phone and len(content.strip()) <= 20:
        intake.caller.phone = content.strip()

    name_match = re.search(r"\bmy name is ([^.,!\n]+)", content, re.IGNORECASE)
    if name_match and not intake.caller.name:
        intake.caller.name = name_match.group(1).strip()

    if intake.caller.phone and intake.consent.consent_to_store_information is True:
        intake.consent.consent_to_contact = True

    if state == ConversationState.UNDERSTAND_REASON_FOR_CALL and len(content) > 10:
        intake.care_needs.notes = content.strip()

    if intake.care_recipient.age is None:
        for token in content.replace(",", "").split():
            if token.isdigit() and 50 <= int(token) <= 120:
                intake.care_recipient.age = int(token)
                break

    if state == ConversationState.ASSESS_URGENCY_AND_SAFETY:
        intake.timing.urgency = (
            "within_30_days" if "soon" in lowered or "30" in lowered else content.strip()
        )

    if state == ConversationState.COLLECT_LOCATION_REQUIREMENTS:
        zip_digits = "".join(ch for ch in content if ch.isdigit())
        if len(zip_digits) >= 5:
            intake.location_preferences.postal_code = zip_digits[:5]
        if not intake.location_preferences.preferred_city:
            intake.location_preferences.preferred_city = content.strip()

    if state == ConversationState.COLLECT_FINANCIAL_REQUIREMENTS:
        numbers = [int(token) for token in content.replace(",", "").split() if token.isdigit()]
        if numbers:
            intake.financial.monthly_budget_max = max(numbers)
            if len(numbers) > 1:
                intake.financial.monthly_budget_min = min(numbers)

    if "daughter" in lowered or "son" in lowered:
        intake.caller.relationship_to_care_recipient = (
            "daughter" if "daughter" in lowered else "son"
        )

    if "memory" in lowered:
        intake.care_needs.memory_concerns = True
    if "bathing" in lowered or "meal" in lowered or "mobility" in lowered:
        intake.care_needs.notes = content.strip()

    if state == ConversationState.GREETING and not intake.caller.name and " " in content.strip():
        intake.caller.name = content.strip()

    zip_match = re.search(r"\b(\d{5})\b", content)
    if zip_match and not intake.location_preferences.postal_code:
        intake.location_preferences.postal_code = zip_match.group(1)

    if "budget" in lowered:
        numbers = [
            int("".join(ch for ch in token if ch.isdigit()))
            for token in content.replace(",", "").split()
            if any(ch.isdigit() for ch in token)
        ]
        budget_numbers = [
            number
            for number in numbers
            if 500 <= number <= 50000 and number != intake.care_recipient.age
        ]
        postal = intake.location_preferences.postal_code
        if postal and postal.isdigit():
            budget_numbers = [number for number in budget_numbers if number != int(postal)]
        if budget_numbers:
            intake.financial.monthly_budget_max = max(budget_numbers)
            if len(budget_numbers) > 1:
                intake.financial.monthly_budget_min = min(budget_numbers)

    if "within" in lowered and "30" in lowered and not intake.timing.urgency:
        intake.timing.urgency = "within_30_days"


def extract_with_ollama(
    intake: IntakeRecord,
    content: str,
    state: ConversationState,
    history: list[dict[str, str]],
    client: OllamaClient | None = None,
) -> SafetySignals | None:
    ollama = client or OllamaClient()
    messages = [
        {"role": "system", "content": EXTRACTION_PROMPT},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "current_state": state.value,
                    "current_intake": intake.model_dump(),
                    "conversation": history[-6:],
                    "latest_user_message": content,
                }
            ),
        },
    ]
    try:
        patch = ollama.chat_json(messages)
    except OllamaError:
        return None

    apply_extraction_patch(intake, patch)
    signals = detect_safety_signals(content)
    _apply_safety_signals(intake, signals)
    return signals


def _apply_safety_signals(intake: IntakeRecord, signals: SafetySignals) -> None:
    if signals.possible_emergency:
        intake.safety.possible_emergency = True
        intake.safety.human_followup_required = True
    if signals.abuse_or_neglect_concern:
        intake.safety.abuse_or_neglect_concern = True
        intake.safety.human_followup_required = True
    if signals.immediate_danger:
        intake.safety.immediate_danger = True
        intake.safety.human_followup_required = True
