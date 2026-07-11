from app.models.intake import IntakeRecord
from app.services.lead_scoring import compute_lead_score


def _qualified_intake() -> IntakeRecord:
    return IntakeRecord.model_validate(
        {
            "caller": {
                "name": "Jane Doe",
                "phone": "555-123-4567",
                "relationship_to_care_recipient": "daughter",
            },
            "care_recipient": {"age": 82},
            "care_needs": {"memory_concerns": True, "notes": "Needs bathing help"},
            "timing": {"urgency": "within_30_days"},
            "location_preferences": {"postal_code": "11101"},
            "financial": {"monthly_budget_max": 8000},
            "consent": {
                "consent_to_contact": True,
                "consent_to_share_with_matched_providers": True,
            },
        }
    )


def test_compute_lead_score_for_qualified_intake() -> None:
    result = compute_lead_score(_qualified_intake())
    assert result.score == 100
    assert result.category == "highly_qualified"


def test_compute_lead_score_for_partial_intake() -> None:
    intake = IntakeRecord()
    result = compute_lead_score(intake)
    assert result.score < 40
    assert result.category == "incomplete_or_exploratory"


def test_compute_lead_score_mid_range() -> None:
    intake = IntakeRecord.model_validate(
        {
            "caller": {"name": "Jane Doe", "phone": "555-123-4567"},
            "care_recipient": {"age": 82},
            "care_needs": {"notes": "Needs help"},
            "location_preferences": {"postal_code": "11101"},
        }
    )
    result = compute_lead_score(intake)
    assert 40 <= result.score <= 79
    assert result.breakdown["identity_and_contact"] == 10
