from app.agent.state_machine import (
    ConversationState,
    advance_state,
    advance_through_satisfied_states,
    can_transition,
)
from app.models.intake import IntakeRecord


def test_greeting_advances_to_disclosure() -> None:
    assert can_transition(ConversationState.GREETING, ConversationState.DISCLOSURE_AND_CONSENT)
    next_state = advance_state(ConversationState.GREETING, IntakeRecord())
    assert next_state == ConversationState.DISCLOSURE_AND_CONSENT


def test_disclosure_requires_consent_before_advancing() -> None:
    intake = IntakeRecord()
    assert (
        advance_state(ConversationState.DISCLOSURE_AND_CONSENT, intake)
        == ConversationState.DISCLOSURE_AND_CONSENT
    )
    intake.consent.consent_to_store_information = True
    assert (
        advance_state(ConversationState.DISCLOSURE_AND_CONSENT, intake)
        == ConversationState.UNDERSTAND_REASON_FOR_CALL
    )


def test_advance_through_satisfied_states_stops_at_first_missing_stage() -> None:
    intake = IntakeRecord()
    intake.consent.consent_to_store_information = True

    state = advance_through_satisfied_states(ConversationState.DISCLOSURE_AND_CONSENT, intake)
    assert state == ConversationState.UNDERSTAND_REASON_FOR_CALL


def test_match_providers_requires_required_fields() -> None:
    intake = IntakeRecord()
    assert (
        advance_state(ConversationState.CONFIRM_SUMMARY, intake)
        == ConversationState.CONFIRM_SUMMARY
    )
    intake = IntakeRecord.model_validate(
        {
            "caller": {
                "name": "Jane",
                "phone": "555-123-4567",
                "relationship_to_care_recipient": "daughter",
            },
            "care_recipient": {"age": 82},
            "location_preferences": {"postal_code": "11101"},
            "care_needs": {"notes": "Memory and bathing support"},
            "timing": {"urgency": "within_30_days"},
            "financial": {"monthly_budget_max": 8000},
            "consent": {"consent_to_contact": True},
        }
    )
    assert (
        advance_state(ConversationState.CONFIRM_SUMMARY, intake)
        == ConversationState.MATCH_PROVIDERS
    )
