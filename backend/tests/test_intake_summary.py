import pytest

from app.models.intake import IntakeRecord
from app.services.intake_summary import (
    SUMMARY_CONFIRMATION_QUESTION,
    build_intake_confirmation_message,
)


def _mother_intake(*, care_needs: dict | None = None, **overrides: object) -> IntakeRecord:
    base: dict = {
        "care_recipient": {"age": 82, "relationship_descriptor": "mother"},
        "timing": {"urgency": "within_30_days"},
    }
    if care_needs is not None:
        base["care_needs"] = care_needs
    base.update(overrides)
    return IntakeRecord.model_validate(base)


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


_TIMING_TAIL = ", and you're hoping to arrange support within the next month."


@pytest.mark.parametrize(
    ("notes", "expected_care_fragment"),
    [
        ("help around the house", "She needs help around the house"),
        ("needs help around the house", "She needs help around the house"),
        (
            "She's starting to need help around the house",
            "She's starting to need help around the house",
        ),
        (
            "cooking, cleaning, and getting around safely",
            "She needs help with cooking, cleaning, and getting around safely",
        ),
    ],
)
def test_care_needs_notes_render_without_duplicated_help(
    notes: str,
    expected_care_fragment: str,
) -> None:
    intake = _mother_intake(care_needs={"notes": notes})
    message = build_intake_confirmation_message(intake)
    assert expected_care_fragment + _TIMING_TAIL in message
    assert "needs help with help" not in message.lower()
    assert "needs help with needs" not in message.lower()


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
