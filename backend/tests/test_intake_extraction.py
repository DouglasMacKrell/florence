from app.models.enums import ConversationState
from app.models.intake import IntakeRecord
from app.services.intake_extraction import apply_extraction_patch, extract_with_rules


def test_apply_extraction_patch_updates_nested_fields() -> None:
    intake = IntakeRecord()
    apply_extraction_patch(
        intake,
        {
            "caller_name": "Jane Doe",
            "caller_phone": "555-123-4567",
            "relationship": "daughter",
            "care_recipient_age": 82,
            "postal_code": "11101",
            "budget_max": 8000,
            "consent_to_contact": True,
        },
    )
    assert intake.caller.name == "Jane Doe"
    assert intake.caller.phone == "555-123-4567"
    assert intake.care_recipient.age == 82
    assert intake.location_preferences.postal_code == "11101"
    assert intake.financial.monthly_budget_max == 8000
    assert intake.consent.consent_to_contact is True


def test_extract_with_rules_captures_consent() -> None:
    intake = IntakeRecord()
    extract_with_rules(
        intake,
        "Yes, you may store my information.",
        ConversationState.DISCLOSURE_AND_CONSENT,
    )
    assert intake.consent.consent_to_store_information is True


def test_extract_with_rules_captures_demo_intake() -> None:
    intake = IntakeRecord()
    demo_message = (
        "My father is 82 in Queens 11101 and needs memory and bathing help "
        "within 30 days. Budget 6000 to 8000."
    )
    extract_with_rules(
        intake,
        demo_message,
        ConversationState.ASSESS_CARE_NEEDS,
    )
    assert intake.care_recipient.age == 82
    assert intake.location_preferences.postal_code == "11101"
    assert intake.financial.monthly_budget_max == 8000
