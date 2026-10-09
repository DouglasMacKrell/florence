import json
import re
from typing import Any

from app.agent.prompts import EXTRACTION_PROMPT
from app.agent.safety import SafetySignals, detect_safety_signals
from app.models.enums import ConversationState
from app.models.intake import IntakeRecord
from app.services.intake_extraction_policy import (
    CARE_NOTES_STATES,
    can_apply_patch_field,
    looks_like_location_phrase,
    looks_like_person_name,
    normalize_caller_relationship,
    reconcile_intake_coherence,
)
from app.services.llm_client import LlmClient, LlmError, get_llm_client

_CARE_RECIPIENT_ROLE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bmy (?:\d{1,3}[- ]year[- ]old )?(mother|mom)\b", re.I), "mother"),
    (re.compile(r"\bmy (?:\d{1,3}[- ]year[- ]old )?(father|dad)\b", re.I), "father"),
    (re.compile(r"\bmy (?:\d{1,3}[- ]year[- ]old )?(husband|wife|spouse)\b", re.I), "spouse"),
    (re.compile(r"\bfor my (mother|mom|father|dad|parent|husband|wife|spouse)\b", re.I), ""),
)

_CALLER_RELATIONSHIP_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bi[' ]?m (?:her|his) daughter\b", re.I), "daughter"),
    (re.compile(r"\bi[' ]?m (?:her|his) son\b", re.I), "son"),
    (re.compile(r"\bi[' ]?m (?:her|his) spouse\b", re.I), "spouse"),
)


def apply_extraction_patch(
    intake: IntakeRecord,
    patch: dict[str, Any],
    *,
    state: ConversationState,
) -> None:
    if patch.get("caller_name") and can_apply_patch_field(
        "caller_name", state=state, intake=intake, new_value=patch["caller_name"]
    ):
        intake.caller.name = str(patch["caller_name"]).strip()
    if patch.get("caller_phone") and can_apply_patch_field(
        "caller_phone", state=state, intake=intake, new_value=patch["caller_phone"]
    ):
        intake.caller.phone = str(patch["caller_phone"]).strip()
    if patch.get("caller_email"):
        intake.caller.email = str(patch["caller_email"]).strip()
    if patch.get("relationship") and can_apply_patch_field(
        "relationship", state=state, intake=intake, new_value=patch["relationship"]
    ):
        intake.caller.relationship_to_care_recipient = normalize_caller_relationship(
            str(patch["relationship"])
        )
    role = patch.get("care_recipient_role")
    if role and can_apply_patch_field(
        "care_recipient_role", state=state, intake=intake, new_value=role
    ):
        intake.care_recipient.relationship_descriptor = str(role).strip().lower()
    if patch.get("care_recipient_name") and can_apply_patch_field(
        "care_recipient_name", state=state, intake=intake, new_value=patch["care_recipient_name"]
    ):
        intake.care_recipient.name = str(patch["care_recipient_name"]).strip()
    if patch.get("care_recipient_age") is not None and can_apply_patch_field(
        "care_recipient_age", state=state, intake=intake, new_value=patch["care_recipient_age"]
    ):
        intake.care_recipient.age = int(patch["care_recipient_age"])
    if patch.get("care_notes") and can_apply_patch_field(
        "care_notes", state=state, intake=intake, new_value=patch["care_notes"]
    ):
        intake.care_needs.notes = str(patch["care_notes"]).strip()
    if patch.get("requested_care_types"):
        values = patch["requested_care_types"]
        if isinstance(values, list):
            intake.care_needs.requested_care_types = [str(item) for item in values]
    if patch.get("urgency") and can_apply_patch_field(
        "urgency", state=state, intake=intake, new_value=patch["urgency"]
    ):
        intake.timing.urgency = _normalize_urgency_text(str(patch["urgency"]))
    if patch.get("postal_code") and can_apply_patch_field(
        "postal_code", state=state, intake=intake, new_value=patch["postal_code"]
    ):
        intake.location_preferences.postal_code = str(patch["postal_code"]).strip()[:5]
    if patch.get("preferred_city") and can_apply_patch_field(
        "preferred_city", state=state, intake=intake, new_value=patch["preferred_city"]
    ):
        intake.location_preferences.preferred_city = str(patch["preferred_city"]).strip()
    if patch.get("preferred_state") and can_apply_patch_field(
        "preferred_state", state=state, intake=intake, new_value=patch["preferred_state"]
    ):
        intake.location_preferences.preferred_state = str(patch["preferred_state"]).strip()
    if patch.get("budget_min") is not None and can_apply_patch_field(
        "budget_min", state=state, intake=intake, new_value=patch["budget_min"]
    ):
        intake.financial.monthly_budget_min = int(patch["budget_min"])
    if patch.get("budget_max") is not None and can_apply_patch_field(
        "budget_max", state=state, intake=intake, new_value=patch["budget_max"]
    ):
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
    reconcile_intake_coherence(intake)


def is_affirmative_reply(content: str) -> bool:
    lowered = content.lower().strip()
    return lowered.startswith("yes") or lowered in {"sure", "ok", "okay", "yep", "yeah"}


def extract_with_rules(
    intake: IntakeRecord, content: str, state: ConversationState
) -> SafetySignals:
    _apply_simple_extraction(intake, content, state)
    signals = detect_safety_signals(content)
    _apply_safety_signals(intake, signals)
    reconcile_intake_coherence(intake)
    return signals


def _normalize_urgency_text(raw: str) -> str:
    cleaned = re.sub(r"\s+", " ", raw.strip())
    lowered = cleaned.lower()
    if "within" in lowered and "30" in lowered:
        return "within_30_days"
    if lowered in {"within_30_days", "within 30 days"}:
        return "within_30_days"
    first_sentence = cleaned.split(".")[0].strip()
    return first_sentence or cleaned


def _apply_relationship_heuristics(intake: IntakeRecord, content: str) -> None:
    for pattern, descriptor in _CARE_RECIPIENT_ROLE_PATTERNS:
        match = pattern.search(content)
        if not match:
            continue
        if descriptor and not intake.care_recipient.relationship_descriptor:
            intake.care_recipient.relationship_descriptor = descriptor
        elif match.group(1):
            role = match.group(1).lower()
            mapping = {
                "mother": "mother",
                "mom": "mother",
                "father": "father",
                "dad": "father",
                "parent": "parent",
                "husband": "spouse",
                "wife": "spouse",
                "spouse": "spouse",
            }
            if not intake.care_recipient.relationship_descriptor:
                intake.care_recipient.relationship_descriptor = mapping.get(role, role)
        if not intake.caller.relationship_to_care_recipient and descriptor in {
            "mother",
            "father",
            "parent",
        }:
            intake.caller.relationship_to_care_recipient = "family member"
        break

    for pattern, relationship in _CALLER_RELATIONSHIP_PATTERNS:
        if pattern.search(content) and not intake.caller.relationship_to_care_recipient:
            intake.caller.relationship_to_care_recipient = relationship
            break


def _apply_simple_extraction(intake: IntakeRecord, content: str, state: ConversationState) -> None:
    lowered = content.lower().strip()
    if is_affirmative_reply(content):
        if state == ConversationState.DISCLOSURE_AND_CONSENT:
            intake.consent.consent_to_store_information = True
        elif state == ConversationState.COLLECT_CALLER_CONTACT:
            if intake.consent.consent_to_store_information is True:
                intake.consent.consent_to_contact = True
        elif state == ConversationState.CAPTURE_FOLLOWUP_CONSENT:
            intake.consent.consent_to_share_with_matched_providers = True
            intake.consent.consent_to_contact = True

    _apply_relationship_heuristics(intake, content)

    if "@" in content and not intake.caller.email:
        intake.caller.email = content.strip()

    phone_match = re.search(
        r"(?:\+1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}",
        content,
    )
    digits = "".join(ch for ch in content if ch.isdigit())
    if phone_match and can_apply_patch_field(
        "caller_phone", state=state, intake=intake, new_value=phone_match.group(0)
    ):
        intake.caller.phone = phone_match.group(0).strip()
    elif (
        len(digits) in {10, 11}
        and len(content.strip()) <= 20
        and can_apply_patch_field("caller_phone", state=state, intake=intake, new_value=content)
    ):
        intake.caller.phone = content.strip()

    name_match = re.search(r"\bmy name is ([^.,!\n]+)", content, re.IGNORECASE)
    if name_match and can_apply_patch_field(
        "caller_name", state=state, intake=intake, new_value=name_match.group(1)
    ):
        intake.caller.name = name_match.group(1).strip()

    name_allowed_at_contact = state == ConversationState.COLLECT_CALLER_CONTACT and not digits
    if (
        state != ConversationState.DISCLOSURE_AND_CONSENT
        and not intake.caller.name
        and looks_like_person_name(content)
        and not looks_like_location_phrase(content)
        and not is_affirmative_reply(content)
        and not digits
        and (state != ConversationState.COLLECT_CALLER_CONTACT or name_allowed_at_contact)
    ):
        intake.caller.name = content.strip()

    if intake.caller.phone and intake.consent.consent_to_store_information is True:
        intake.consent.consent_to_contact = True

    care_sentence = re.search(r"\b(?:she|he|they)[' ]?s[^.!?]+[.!?]?", content, re.IGNORECASE)
    if care_sentence and can_apply_patch_field(
        "care_notes", state=state, intake=intake, new_value=care_sentence.group(0)
    ):
        intake.care_needs.notes = care_sentence.group(0).strip()
    elif (
        state == ConversationState.UNDERSTAND_REASON_FOR_CALL
        and len(content) > 10
        and can_apply_patch_field("care_notes", state=state, intake=intake, new_value=content)
    ):
        intake.care_needs.notes = content.strip()

    if intake.care_recipient.age is None:
        age_match = re.search(
            r"\b(\d{1,3})\s*(?:[- ]year[- ]old|years old)\b",
            content,
            re.IGNORECASE,
        )
        if age_match:
            intake.care_recipient.age = int(age_match.group(1))
        else:
            for token in content.replace(",", "").split():
                if token.isdigit() and 50 <= int(token) <= 120:
                    intake.care_recipient.age = int(token)
                    break

    if state == ConversationState.ASSESS_URGENCY_AND_SAFETY and can_apply_patch_field(
        "urgency", state=state, intake=intake, new_value=content
    ):
        intake.timing.urgency = _normalize_urgency_text(content)

    if state == ConversationState.COLLECT_LOCATION_REQUIREMENTS:
        zip_digits = "".join(ch for ch in content if ch.isdigit())
        if len(zip_digits) >= 5 and can_apply_patch_field(
            "postal_code", state=state, intake=intake, new_value=zip_digits[:5]
        ):
            intake.location_preferences.postal_code = zip_digits[:5]
        if (
            not intake.location_preferences.preferred_city
            and looks_like_location_phrase(content)
            and can_apply_patch_field(
                "preferred_city",
                state=state,
                intake=intake,
                new_value=content,
            )
        ):
            intake.location_preferences.preferred_city = content.strip()
        if "new york" in lowered:
            intake.location_preferences.preferred_city = "New York City"
            intake.location_preferences.preferred_state = "NY"

    if state == ConversationState.COLLECT_FINANCIAL_REQUIREMENTS:
        numbers = [int(token) for token in content.replace(",", "").split() if token.isdigit()]
        if numbers and can_apply_patch_field(
            "budget_max", state=state, intake=intake, new_value=max(numbers)
        ):
            intake.financial.monthly_budget_max = max(numbers)
            if len(numbers) > 1:
                intake.financial.monthly_budget_min = min(numbers)

    if (
        content.strip().isdigit()
        and 500 <= int(content.strip()) <= 50000
        and can_apply_patch_field(
            "budget_max", state=state, intake=intake, new_value=int(content.strip())
        )
    ):
        intake.financial.monthly_budget_max = int(content.strip())

    if "memory" in lowered:
        intake.care_needs.memory_concerns = True
    if (
        state in CARE_NOTES_STATES
        and ("bathing" in lowered or "meal" in lowered or "mobility" in lowered)
        and can_apply_patch_field("care_notes", state=state, intake=intake, new_value=content)
    ):
        intake.care_needs.notes = content.strip()

    zip_match = re.search(r"\b(\d{5})\b", content)
    if (
        zip_match
        and not intake.location_preferences.postal_code
        and can_apply_patch_field(
            "postal_code",
            state=state,
            intake=intake,
            new_value=zip_match.group(1),
        )
    ):
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
        if budget_numbers and can_apply_patch_field(
            "budget_max", state=state, intake=intake, new_value=max(budget_numbers)
        ):
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
    client: LlmClient | None = None,
) -> SafetySignals | None:
    llm = client or get_llm_client()
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
        patch = llm.chat_json(messages)
    except LlmError:
        return None

    apply_extraction_patch(intake, patch, state=state)
    signals = detect_safety_signals(content)
    _apply_safety_signals(intake, signals)
    reconcile_intake_coherence(intake)
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
