import json
from pathlib import Path

from app.matching.engine import match_providers
from app.models.intake import IntakeRecord
from app.models.provider import ProviderRecord


def _load_providers() -> list[ProviderRecord]:
    seed_path = Path(__file__).resolve().parents[2] / "data" / "providers.json"
    return [ProviderRecord.model_validate(p) for p in json.loads(seed_path.read_text())]


def _queens_demo_intake() -> IntakeRecord:
    return IntakeRecord.model_validate(
        {
            "caller": {
                "name": "Jane Doe",
                "phone": "555-123-4567",
                "relationship_to_care_recipient": "daughter",
            },
            "care_recipient": {
                "age": 82,
                "current_location": {"city": "Queens", "state": "NY", "postal_code": "11101"},
            },
            "care_needs": {
                "requested_care_types": ["assisted_living", "memory_care"],
                "activities_of_daily_living": {"bathing": True, "eating": True},
                "memory_concerns": True,
                "overnight_support_needed": True,
            },
            "timing": {"urgency": "within_30_days"},
            "location_preferences": {
                "preferred_city": "Queens",
                "preferred_state": "NY",
                "postal_code": "11101",
                "maximum_distance_miles": 10,
            },
            "financial": {"monthly_budget_min": 6000, "monthly_budget_max": 8000},
            "preferences": {"private_room_required": True, "language_preferences": ["English"]},
            "consent": {"consent_to_contact": True},
        }
    )


def test_match_providers_returns_top_three_ranked() -> None:
    results = match_providers(_queens_demo_intake(), _load_providers(), limit=3)
    assert 1 <= len(results) <= 3
    ranks = [r.rank for r in results]
    assert ranks == sorted(ranks)
    assert results[0].score >= results[-1].score


def test_match_providers_excludes_over_budget() -> None:
    intake = _queens_demo_intake()
    intake.financial.monthly_budget_max = 1000
    results = match_providers(intake, _load_providers(), limit=3)
    assert results == []


def test_match_explanations_include_strengths() -> None:
    results = match_providers(_queens_demo_intake(), _load_providers(), limit=1)
    assert results
    assert results[0].strengths
