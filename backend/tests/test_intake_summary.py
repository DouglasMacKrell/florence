from app.models.intake import IntakeRecord
from app.services.intake_summary import (
    SUMMARY_CONFIRMATION_QUESTION,
    build_intake_confirmation_message,
)


def test_confirmation_summary_uses_structured_intake_with_paragraphs() -> None:
    intake = IntakeRecord.model_validate(
        {
            "caller": {
                "name": "Douglas MacKrell",
                "phone": "5551234567",
                "relationship_to_care_recipient": "family member",
            },
            "care_recipient": {"age": 82, "relationship_descriptor": "mother"},
            "location_preferences": {"postal_code": "11375"},
            "care_needs": {"notes": "cooking, cleaning, and getting around safely"},
            "timing": {"urgency": "within_30_days"},
            "financial": {"monthly_budget_max": 7000},
            "consent": {"consent_to_contact": True},
        }
    )

    message = build_intake_confirmation_message(intake)

    assert message.startswith("Let me make sure I have this right.")
    assert "82-year-old mother" in message
    assert "ZIP code 11375" in message
    assert "555-123-4567" in message
    assert "Douglas MacKrell" in message
    assert "within the next month" in message
    assert message.endswith(SUMMARY_CONFIRMATION_QUESTION)
    assert "Help is needed with" not in message


def test_confirmation_summary_omits_missing_fields_cleanly() -> None:
    intake = IntakeRecord.model_validate(
        {
            "care_recipient": {"age": 79},
            "location_preferences": {"postal_code": "11101"},
        }
    )

    message = build_intake_confirmation_message(intake)

    assert "11101" in message
    assert "budget" not in message.lower()
    assert "contact information" not in message.lower()
