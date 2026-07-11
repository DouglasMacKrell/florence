from app.agent.care_recommender import recommend_care_types
from app.models.intake import IntakeRecord


def test_recommends_home_care_for_adl_support_at_home() -> None:
    intake = IntakeRecord.model_validate(
        {
            "care_recipient": {"living_situation": "lives_alone"},
            "care_needs": {
                "activities_of_daily_living": {"bathing": True, "meal_preparation": True},
                "memory_concerns": False,
            },
        }
    )
    result = recommend_care_types(intake)
    assert result.primary == "home_care"
    assert "home_care" in result.alternatives or "assisted_living" in result.alternatives


def test_recommends_hospice_for_terminal_comfort_focus() -> None:
    intake = IntakeRecord.model_validate(
        {
            "care_needs": {
                "requested_care_types": ["hospice"],
                "conditions_relevant_to_care": ["terminal_illness"],
                "notes": "Comfort-focused care, declining rapidly",
            },
        }
    )
    result = recommend_care_types(intake)
    assert result.primary == "hospice"


def test_recommends_memory_care_when_memory_concerns() -> None:
    intake = IntakeRecord.model_validate(
        {
            "care_needs": {
                "memory_concerns": True,
                "wandering_risk": True,
                "overnight_support_needed": True,
            },
            "care_recipient": {"living_situation": "cannot_live_alone_safely"},
        }
    )
    result = recommend_care_types(intake)
    assert result.primary in {"memory_care", "assisted_living"}
