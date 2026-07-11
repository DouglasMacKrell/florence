from dataclasses import dataclass


@dataclass(frozen=True)
class SafetySignals:
    immediate_danger: bool = False
    possible_emergency: bool = False
    abuse_or_neglect_concern: bool = False
    unsafe_living_situation: bool = False
    human_followup_required: bool = False


EMERGENCY_PHRASES = (
    "chest pain",
    "can't breathe",
    "cannot breathe",
    "difficulty breathing",
    "unresponsive",
    "suicidal",
    "self-harm",
    "serious injury",
    "missing person",
    "call 911",
    "immediate danger",
)

ABUSE_PHRASES = (
    "abuse",
    "neglect",
    "exploitation",
    "withholding medication",
    "unsafe caregiver",
)


def detect_safety_signals(content: str) -> SafetySignals:
    lowered = content.lower()
    possible_emergency = any(phrase in lowered for phrase in EMERGENCY_PHRASES)
    if "serious injury" in lowered and any(
        negation in lowered
        for negation in (
            "without serious injury",
            "no serious injury",
            "not a serious injury",
            "without a serious injury",
        )
    ):
        possible_emergency = False
    abuse_or_neglect_concern = any(phrase in lowered for phrase in ABUSE_PHRASES)
    human_followup_required = possible_emergency or abuse_or_neglect_concern
    return SafetySignals(
        possible_emergency=possible_emergency,
        abuse_or_neglect_concern=abuse_or_neglect_concern,
        human_followup_required=human_followup_required,
    )
