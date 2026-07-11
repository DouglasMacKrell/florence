from app.models.intake import IntakeRecord


def test_intake_record_defaults_to_empty_schema() -> None:
    intake = IntakeRecord()
    assert intake.caller.name is None
    assert intake.safety.immediate_danger is False
    assert intake.care_needs.requested_care_types == []


def test_intake_record_parses_partial_update() -> None:
    intake = IntakeRecord.model_validate(
        {
            "caller": {"name": "Jane Doe", "phone": "555-123-4567"},
            "care_recipient": {"age": 82},
            "timing": {"urgency": "within_30_days"},
        }
    )
    assert intake.caller.name == "Jane Doe"
    assert intake.care_recipient.age == 82
    assert intake.timing.urgency == "within_30_days"


def test_intake_missing_required_fields() -> None:
    intake = IntakeRecord()
    missing = intake.missing_required_fields()
    assert "caller.name" in missing
    assert "caller.phone" in missing
    assert "consent.consent_to_contact" in missing


def test_intake_completion_percent_increases_with_fields() -> None:
    empty = IntakeRecord()
    partial = IntakeRecord.model_validate(
        {
            "caller": {
                "name": "Jane Doe",
                "phone": "555-123-4567",
                "relationship_to_care_recipient": "daughter",
            },
            "care_recipient": {"age": 82},
            "location_preferences": {"postal_code": "11101"},
            "care_needs": {"notes": "Needs bathing help"},
            "timing": {"urgency": "within_30_days"},
            "financial": {"monthly_budget_max": 8000},
            "consent": {"consent_to_contact": True},
        }
    )
    assert partial.completion_percent() > empty.completion_percent()
    assert partial.completion_percent() == 100
