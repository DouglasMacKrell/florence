import re
from typing import Any

from app.models.enums import ConversationState
from app.models.intake import IntakeRecord

CONSENT_FIELDS = frozenset(
    {
        "consent_to_store",
        "consent_to_contact",
        "consent_to_share",
    }
)

EARLY_INTAKE_STATES = frozenset(
    {
        ConversationState.GREETING,
        ConversationState.DISCLOSURE_AND_CONSENT,
        ConversationState.UNDERSTAND_REASON_FOR_CALL,
        ConversationState.IDENTIFY_CARE_RECIPIENT,
        ConversationState.ASSESS_CARE_NEEDS,
    }
)

LOCATION_STATES = frozenset(
    {
        ConversationState.COLLECT_LOCATION_REQUIREMENTS,
        *EARLY_INTAKE_STATES,
    }
)

NAME_STATES = frozenset(
    {
        ConversationState.UNDERSTAND_DECISION_PROCESS,
        ConversationState.COLLECT_CALLER_CONTACT,
        ConversationState.CONFIRM_SUMMARY,
    }
)

PHONE_STATES = frozenset(
    {
        ConversationState.COLLECT_CALLER_CONTACT,
        ConversationState.CONFIRM_SUMMARY,
    }
)

BUDGET_STATES = frozenset(
    {
        ConversationState.COLLECT_FINANCIAL_REQUIREMENTS,
        *EARLY_INTAKE_STATES,
    }
)

URGENCY_STATES = frozenset(
    {
        ConversationState.ASSESS_URGENCY_AND_SAFETY,
        *EARLY_INTAKE_STATES,
    }
)

CARE_NOTES_STATES = frozenset(
    {
        ConversationState.UNDERSTAND_REASON_FOR_CALL,
        ConversationState.ASSESS_CARE_NEEDS,
        *EARLY_INTAKE_STATES,
    }
)


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list):
        return len(value) == 0
    return False


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def looks_like_person_name(text: str) -> bool:
    cleaned = _normalize_whitespace(text)
    if not cleaned or len(cleaned) > 80:
        return False
    if re.search(r"\d{3,}", cleaned):
        return False
    if re.search(r"\b(zip|street|avenue|city|state)\b", cleaned, re.IGNORECASE):
        return False
    words = cleaned.split()
    if not words or len(words) > 5:
        return False
    return all(word[0].isalpha() for word in words if word)


def looks_like_location_phrase(text: str) -> bool:
    cleaned = _normalize_whitespace(text)
    lowered = cleaned.lower()
    if re.search(r"\b\d{5}\b", cleaned):
        return True
    if re.search(r"\b(new york|queens|brooklyn|manhattan|bronx|staten island)\b", lowered):
        return True
    if "," in cleaned:
        return True
    return bool(re.search(r"\b[A-Z]{2}\b", cleaned))


def format_phone_display(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) == 10:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    return phone.strip()


def normalize_caller_relationship(raw: str) -> str:
    lowered = raw.strip().lower()
    mapping = {
        "daughter": "daughter",
        "son": "son",
        "spouse": "spouse",
        "wife": "spouse",
        "husband": "spouse",
        "child": "child",
        "family member": "family member",
        "caregiver": "caregiver",
    }
    if lowered in mapping:
        return mapping[lowered]
    if lowered in {"mother", "mom", "father", "dad", "parent", "parents"}:
        return "family member"
    return raw.strip()


def can_apply_patch_field(
    field_key: str,
    *,
    state: ConversationState,
    intake: IntakeRecord,
    new_value: Any,
    explicit_self_identification: bool = False,
) -> bool:
    if field_key in CONSENT_FIELDS:
        return True

    if field_key == "caller_name":
        if _is_empty(new_value):
            return False
        if explicit_self_identification:
            return _is_empty(intake.caller.name) or state in NAME_STATES
        if not _is_empty(intake.caller.name) and state not in NAME_STATES:
            return False
        if _is_empty(intake.caller.name):
            return state in NAME_STATES
        return state in NAME_STATES

    if field_key == "caller_phone":
        if _is_empty(new_value):
            return False
        if not _is_empty(intake.caller.phone) and state not in PHONE_STATES:
            return False
        return _is_empty(intake.caller.phone) or state in PHONE_STATES

    if field_key == "preferred_city":
        city = str(new_value).strip()
        if not city or city == intake.caller.name:
            return False
        if looks_like_person_name(city) and not looks_like_location_phrase(city):
            return False
        if (
            not _is_empty(intake.location_preferences.preferred_city)
            and state != ConversationState.COLLECT_LOCATION_REQUIREMENTS
        ):
            return False
        return state in LOCATION_STATES

    if field_key == "preferred_state":
        if (
            not _is_empty(intake.location_preferences.preferred_state)
            and state != ConversationState.COLLECT_LOCATION_REQUIREMENTS
        ):
            return False
        return state in LOCATION_STATES

    if field_key == "postal_code":
        if (
            not _is_empty(intake.location_preferences.postal_code)
            and state != ConversationState.COLLECT_LOCATION_REQUIREMENTS
        ):
            return False
        return state in LOCATION_STATES

    if field_key == "relationship":
        caller_relationship = intake.caller.relationship_to_care_recipient
        if not _is_empty(caller_relationship) and state not in EARLY_INTAKE_STATES:
            return False
        return state in EARLY_INTAKE_STATES or _is_empty(caller_relationship)

    if field_key == "care_recipient_role":
        recipient_role = intake.care_recipient.relationship_descriptor
        if not _is_empty(recipient_role) and state not in EARLY_INTAKE_STATES:
            return False
        return state in EARLY_INTAKE_STATES or _is_empty(recipient_role)

    if field_key in {"care_recipient_age", "care_recipient_name"}:
        current = (
            intake.care_recipient.age
            if field_key == "care_recipient_age"
            else intake.care_recipient.name
        )
        if not _is_empty(current) and state not in EARLY_INTAKE_STATES:
            return False
        return state in EARLY_INTAKE_STATES or _is_empty(current)

    if field_key == "care_notes":
        if not _is_empty(intake.care_needs.notes) and state not in CARE_NOTES_STATES:
            return False
        return state in CARE_NOTES_STATES or _is_empty(intake.care_needs.notes)

    if field_key == "urgency":
        if not _is_empty(intake.timing.urgency) and state not in URGENCY_STATES:
            return False
        return state in URGENCY_STATES or _is_empty(intake.timing.urgency)

    if field_key in {"budget_min", "budget_max"}:
        current = (
            intake.financial.monthly_budget_min
            if field_key == "budget_min"
            else intake.financial.monthly_budget_max
        )
        if not _is_empty(current) and state not in BUDGET_STATES:
            return False
        return state in BUDGET_STATES or _is_empty(current)

    return _is_empty(getattr(intake, field_key, None))


def reconcile_intake_coherence(intake: IntakeRecord) -> None:
    city = intake.location_preferences.preferred_city
    if city and intake.caller.name and city.strip() == intake.caller.name.strip():
        intake.location_preferences.preferred_city = None

    recipient_role = intake.care_recipient.relationship_descriptor
    caller_relationship = intake.caller.relationship_to_care_recipient
    if recipient_role and caller_relationship in {"mother", "father", "mom", "dad"}:
        intake.caller.relationship_to_care_recipient = "family member"
