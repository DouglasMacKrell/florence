from app.security.redaction import redact_intake, redact_message_content, redact_value


def test_redact_value_masks_phone() -> None:
    assert redact_value("phone", "555-123-4567") == "[REDACTED]"


def test_redact_value_masks_email() -> None:
    assert redact_value("email", "user@example.com") == "[REDACTED]"


def test_redact_value_leaves_non_sensitive_unchanged() -> None:
    assert redact_value("urgency", "within_30_days") == "within_30_days"


def test_redact_intake_masks_nested_pii() -> None:
    intake = {
        "caller": {"name": "Jane Doe", "phone": "555-123-4567", "email": "j@example.com"},
        "care_recipient": {"name": "John Doe", "age": 82},
        "timing": {"urgency": "within_30_days"},
    }
    redacted = redact_intake(intake)
    assert redacted["caller"]["name"] == "[REDACTED]"
    assert redacted["caller"]["phone"] == "[REDACTED]"
    assert redacted["caller"]["email"] == "[REDACTED]"
    assert redacted["care_recipient"]["name"] == "[REDACTED]"
    assert redacted["care_recipient"]["age"] == 82
    assert redacted["timing"]["urgency"] == "within_30_days"


def test_redact_message_content_masks_user_text() -> None:
    assert redact_message_content("My father John lives at 555-123-4567") == "[REDACTED]"
