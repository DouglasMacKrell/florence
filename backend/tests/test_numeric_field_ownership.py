from app.models.enums import ConversationState
from app.models.intake import IntakeRecord
from app.services.intake_extraction import extract_state_owned_rules


def test_zip_only_at_location_does_not_set_budget() -> None:
    intake = IntakeRecord()
    extract_state_owned_rules(intake, "11111", ConversationState.COLLECT_LOCATION_REQUIREMENTS)
    assert intake.location_preferences.postal_code == "11111"
    assert intake.financial.monthly_budget_min is None
    assert intake.financial.monthly_budget_max is None
