from app.models.intake import IntakeRecord
from app.services.intake_summary import (
    SUMMARY_CONFIRMATION_QUESTION,
    build_intake_confirmation_message,
    build_intake_summary_sentences,
)


def test_build_intake_summary_sentences_uses_structured_intake() -> None:
    intake = IntakeRecord.model_validate(
        {
            "caller": {
                "name": "Douglas MacKrell",
                "phone": "555-123-4567",
                "relationship_to_care_recipient": "daughter",
            },
            "care_recipient": {"age": 82},
            "location_preferences": {"postal_code": "11375", "preferred_city": "Queens"},
            "care_needs": {"notes": "help around the house"},
            "timing": {"urgency": "within_30_days"},
            "financial": {"monthly_budget_max": 7000},
            "consent": {"consent_to_contact": True},
        }
    )

    sentences = build_intake_summary_sentences(intake)
    joined = " ".join(sentences)

    assert "82" in joined
    assert "11375" in joined
    assert "help around the house" in joined
    assert "within about 30 days" in joined
    assert "$7,000" in joined
    assert "Douglas MacKrell" in joined
    assert "555-123-4567" in joined
    assert "daughter" in joined


def test_build_intake_confirmation_message_includes_summary_and_question() -> None:
    intake = IntakeRecord.model_validate(
        {
            "caller": {"name": "Jane Doe", "phone": "555-000-1111"},
            "care_recipient": {"age": 79},
            "location_preferences": {"postal_code": "11101"},
            "care_needs": {"notes": "bathing and meals"},
            "timing": {"urgency": "within_30_days"},
            "financial": {"monthly_budget_max": 8000},
            "consent": {"consent_to_contact": True},
        }
    )

    message = build_intake_confirmation_message(intake)

    assert message.startswith("Let me make sure I have this right.")
    assert "Jane Doe" in message
    assert "11101" in message
    assert "bathing and meals" in message
    assert message.endswith(SUMMARY_CONFIRMATION_QUESTION)
