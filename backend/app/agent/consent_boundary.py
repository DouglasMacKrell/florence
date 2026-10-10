import re
from dataclasses import dataclass
from enum import StrEnum

from app.models.enums import ConversationState
from app.models.intake import IntakeRecord


class ConsentKind(StrEnum):
    STORE_INFORMATION = "store_information"
    FOLLOW_UP_CONTACT = "follow_up_contact"
    PROVIDER_SHARE = "provider_share"


class ConsentClassification(StrEnum):
    AFFIRMATIVE = "affirmative"
    NEGATIVE = "negative"
    UNCLEAR = "unclear"


STORE_INFORMATION_QUESTION = (
    "Before we continue, is it okay if I save the information you share "
    "so I can help coordinate care options?"
)

STORE_INFORMATION_CLARIFICATION = (
    "Sorry, I didn't quite catch that. Is it okay if I save the information you share?"
)

FOLLOW_UP_CONTACT_QUESTION = (
    "May I have your consent to contact you with updates about care options and provider referrals?"
)

FOLLOW_UP_CONTACT_CLARIFICATION = (
    "Sorry, I didn't quite catch that. May I contact you with updates about care "
    "options and provider referrals?"
)

PROVIDER_SHARE_QUESTION = (
    "May we share your information with the provider you choose so they can follow up?"
)

PROVIDER_SHARE_CLARIFICATION = (
    "I need a clear yes or no. May we share your information with the provider "
    "you choose so they can follow up?"
)

_AFFIRMATIVE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"^yes\b",
        r"^yes[,!.?\s]",
        r"^yeah\b",
        r"^yep\b",
        r"^sure\b",
        r"^ok(?:ay)?\b",
        r"^that[' ]s fine\b",
        r"^i agree\b",
        r"^of course\b",
        r"^i consent\b",
        r"^you have my permission\b",
        r"^you may contact me\b",
        r"^i already consented\b",
        r"^i already said yes\b",
        r"^i already have\b",
        r"^i[' ]?ve already (consented|said yes|given permission)\b",
        r"^you may store\b",
        r"^i give permission\b",
    )
)

_UNCLEAR_CONSENT_ATTEMPT_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"^tes\b",
        r"^maybe\b",
        r"^i don[' ]t know\b",
        r"^not sure\b",
        r"^hmm+\b",
        r"^um+\b",
        r"^uh+\b",
    )
)

_NEGATIVE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"^no\b",
        r"^no[,!.?\s]",
        r"^nope\b",
        r"^no thanks\b",
        r"^i don[' ]t consent\b",
        r"^do not contact me\b",
        r"^don[' ]t contact me\b",
        r"^i do not give permission\b",
        r"^please do not contact\b",
    )
)

CONSENT_COLLECTING_STATES: frozenset[ConversationState] = frozenset(
    {
        ConversationState.DISCLOSURE_AND_CONSENT,
        ConversationState.COLLECT_FOLLOWUP_CONSENT,
        ConversationState.CAPTURE_FOLLOWUP_CONSENT,
    }
)


@dataclass(frozen=True)
class ConsentTurnOutcome:
    classification: ConsentClassification
    consent_changed: bool
    consent_resolved: bool
    scripted_reply: str


def normalize_consent_message(content: str) -> str:
    return re.sub(r"\s+", " ", content.strip())


def _consent_prompt_markers(kind: ConsentKind) -> tuple[str, ...]:
    if kind == ConsentKind.STORE_INFORMATION:
        return (
            "save the information you share",
            "save the information you provide",
            "coordinate care options",
        )
    if kind == ConsentKind.FOLLOW_UP_CONTACT:
        return (
            "contact you with updates about care options",
            "consent to contact you",
        )
    return ("share your information with the provider",)


def consent_prompt_was_issued(history: list[dict[str, str]], kind: ConsentKind) -> bool:
    markers = _consent_prompt_markers(kind)
    for message in reversed(history):
        if message.get("role") != "assistant":
            continue
        lowered = message.get("content", "").lower()
        if any(marker in lowered for marker in markers):
            return True
    return False


def _looks_like_ambiguous_consent_reply(normalized: str) -> bool:
    if not normalized:
        return False
    for pattern in _UNCLEAR_CONSENT_ATTEMPT_PATTERNS:
        if pattern.search(normalized):
            return True
    tokens = normalized.split()
    if len(tokens) == 1:
        return len(normalized) <= 16
    return False


def should_interpret_as_consent_answer(
    content: str,
    kind: ConsentKind,
    history: list[dict[str, str]],
) -> bool:
    classification = classify_consent_response(content)
    if classification in {
        ConsentClassification.AFFIRMATIVE,
        ConsentClassification.NEGATIVE,
    }:
        return True
    normalized = normalize_consent_message(content)
    if len(normalized) > 24:
        return False
    if not consent_prompt_was_issued(history, kind):
        return False
    return _looks_like_ambiguous_consent_reply(normalized)


def classify_consent_response(content: str) -> ConsentClassification:
    normalized = normalize_consent_message(content)
    if not normalized:
        return ConsentClassification.UNCLEAR

    for pattern in _NEGATIVE_PATTERNS:
        if pattern.search(normalized):
            return ConsentClassification.NEGATIVE

    for pattern in _AFFIRMATIVE_PATTERNS:
        if pattern.search(normalized):
            return ConsentClassification.AFFIRMATIVE

    return ConsentClassification.UNCLEAR


def consent_kind_for_state(state: ConversationState) -> ConsentKind | None:
    if state == ConversationState.DISCLOSURE_AND_CONSENT:
        return ConsentKind.STORE_INFORMATION
    if state == ConversationState.COLLECT_FOLLOWUP_CONSENT:
        return ConsentKind.FOLLOW_UP_CONTACT
    if state == ConversationState.CAPTURE_FOLLOWUP_CONSENT:
        return ConsentKind.PROVIDER_SHARE
    return None


def consent_question_for_kind(kind: ConsentKind) -> str:
    if kind == ConsentKind.STORE_INFORMATION:
        return STORE_INFORMATION_QUESTION
    if kind == ConsentKind.FOLLOW_UP_CONTACT:
        return FOLLOW_UP_CONTACT_QUESTION
    return PROVIDER_SHARE_QUESTION


def consent_clarification_for_kind(kind: ConsentKind) -> str:
    if kind == ConsentKind.STORE_INFORMATION:
        return STORE_INFORMATION_CLARIFICATION
    if kind == ConsentKind.FOLLOW_UP_CONTACT:
        return FOLLOW_UP_CONTACT_CLARIFICATION
    return PROVIDER_SHARE_CLARIFICATION


def _consent_value(intake: IntakeRecord, kind: ConsentKind) -> bool | None:
    if kind == ConsentKind.STORE_INFORMATION:
        return intake.consent.consent_to_store_information
    if kind == ConsentKind.FOLLOW_UP_CONTACT:
        return intake.consent.consent_to_contact
    return intake.consent.consent_to_share_with_matched_providers


def _set_consent_value(intake: IntakeRecord, kind: ConsentKind, value: bool) -> None:
    if kind == ConsentKind.STORE_INFORMATION:
        intake.consent.consent_to_store_information = value
    elif kind == ConsentKind.FOLLOW_UP_CONTACT:
        intake.consent.consent_to_contact = value
    else:
        intake.consent.consent_to_share_with_matched_providers = value


def should_gate_follow_up_consent(intake: IntakeRecord, state: ConversationState) -> bool:
    if intake.consent.consent_to_store_information is not True:
        return False
    if intake.consent.consent_to_contact is not None:
        return False
    if state in {
        ConversationState.GREETING,
        ConversationState.DISCLOSURE_AND_CONSENT,
        ConversationState.COLLECT_FOLLOWUP_CONSENT,
    }:
        return False
    return state == ConversationState.COLLECT_CALLER_CONTACT


def ensure_consent_gate_state(state: ConversationState, intake: IntakeRecord) -> ConversationState:
    if should_gate_follow_up_consent(intake, state):
        return ConversationState.COLLECT_FOLLOWUP_CONSENT
    return state


def process_consent_turn(
    intake: IntakeRecord,
    content: str,
    kind: ConsentKind,
) -> ConsentTurnOutcome:
    current_value = _consent_value(intake, kind)
    classification = classify_consent_response(content)

    if current_value is not None and classification == ConsentClassification.AFFIRMATIVE:
        return ConsentTurnOutcome(
            classification=classification,
            consent_changed=False,
            consent_resolved=True,
            scripted_reply="",
        )

    if classification == ConsentClassification.AFFIRMATIVE:
        _set_consent_value(intake, kind, True)
        return ConsentTurnOutcome(
            classification=classification,
            consent_changed=True,
            consent_resolved=True,
            scripted_reply="",
        )

    if classification == ConsentClassification.NEGATIVE:
        _set_consent_value(intake, kind, False)
        return ConsentTurnOutcome(
            classification=classification,
            consent_changed=True,
            consent_resolved=True,
            scripted_reply="",
        )

    return ConsentTurnOutcome(
        classification=classification,
        consent_changed=False,
        consent_resolved=False,
        scripted_reply=consent_clarification_for_kind(kind),
    )


def is_consent_collecting_state(state: ConversationState) -> bool:
    return state in CONSENT_COLLECTING_STATES
