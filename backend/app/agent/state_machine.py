from app.models.enums import ConversationState
from app.models.intake import IntakeRecord

ORDERED_STATES: list[ConversationState] = [
    ConversationState.GREETING,
    ConversationState.DISCLOSURE_AND_CONSENT,
    ConversationState.UNDERSTAND_REASON_FOR_CALL,
    ConversationState.IDENTIFY_CARE_RECIPIENT,
    ConversationState.ASSESS_CARE_NEEDS,
    ConversationState.ASSESS_URGENCY_AND_SAFETY,
    ConversationState.COLLECT_LOCATION_REQUIREMENTS,
    ConversationState.COLLECT_FINANCIAL_REQUIREMENTS,
    ConversationState.COLLECT_PREFERENCES,
    ConversationState.UNDERSTAND_DECISION_PROCESS,
    ConversationState.CONFIRM_SUMMARY,
    ConversationState.MATCH_PROVIDERS,
    ConversationState.EXPLAIN_RECOMMENDATIONS,
    ConversationState.CAPTURE_FOLLOWUP_CONSENT,
    ConversationState.END_OR_HUMAN_HANDOFF,
]


def can_transition(current: ConversationState, target: ConversationState) -> bool:
    if current == target:
        return True
    try:
        current_index = ORDERED_STATES.index(current)
        target_index = ORDERED_STATES.index(target)
    except ValueError:
        return False
    return target_index == current_index + 1


def advance_state(current: ConversationState, intake: IntakeRecord) -> ConversationState:
    if current == ConversationState.GREETING:
        return ConversationState.DISCLOSURE_AND_CONSENT

    if current == ConversationState.DISCLOSURE_AND_CONSENT:
        if intake.consent.consent_to_store_information is True:
            return ConversationState.UNDERSTAND_REASON_FOR_CALL
        return current

    if current == ConversationState.UNDERSTAND_REASON_FOR_CALL:
        if intake.care_needs.notes or intake.care_needs.requested_care_types:
            return ConversationState.IDENTIFY_CARE_RECIPIENT
        return current

    if current == ConversationState.IDENTIFY_CARE_RECIPIENT:
        if intake.care_recipient.age is not None:
            return ConversationState.ASSESS_CARE_NEEDS
        return current

    if current == ConversationState.ASSESS_CARE_NEEDS:
        if intake._has_care_needs():
            return ConversationState.ASSESS_URGENCY_AND_SAFETY
        return current

    if current == ConversationState.ASSESS_URGENCY_AND_SAFETY:
        if intake.timing.urgency or intake.safety.possible_emergency:
            return ConversationState.COLLECT_LOCATION_REQUIREMENTS
        return current

    if current == ConversationState.COLLECT_LOCATION_REQUIREMENTS:
        if intake._has_location():
            return ConversationState.COLLECT_FINANCIAL_REQUIREMENTS
        return current

    if current == ConversationState.COLLECT_FINANCIAL_REQUIREMENTS:
        if intake._has_financial_constraints():
            return ConversationState.COLLECT_PREFERENCES
        return current

    if current == ConversationState.COLLECT_PREFERENCES:
        return ConversationState.UNDERSTAND_DECISION_PROCESS

    if current == ConversationState.UNDERSTAND_DECISION_PROCESS:
        return ConversationState.CONFIRM_SUMMARY

    if current == ConversationState.CONFIRM_SUMMARY:
        if intake.is_qualified():
            return ConversationState.MATCH_PROVIDERS
        return current

    if current == ConversationState.MATCH_PROVIDERS:
        return ConversationState.EXPLAIN_RECOMMENDATIONS

    if current == ConversationState.EXPLAIN_RECOMMENDATIONS:
        return ConversationState.CAPTURE_FOLLOWUP_CONSENT

    if current == ConversationState.CAPTURE_FOLLOWUP_CONSENT:
        if intake.consent.consent_to_share_with_matched_providers is True:
            return ConversationState.END_OR_HUMAN_HANDOFF
        return current

    return current
