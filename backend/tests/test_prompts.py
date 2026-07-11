from app.agent.prompts import missing_fields_for_reply
from app.models.enums import ConversationState
from app.models.intake import IntakeRecord


def test_missing_fields_for_reply_hides_phone_until_contact_stage() -> None:
    intake = IntakeRecord.model_validate({"caller": {"name": "Jane Doe"}})
    early = missing_fields_for_reply(
        ConversationState.UNDERSTAND_REASON_FOR_CALL.value,
        intake,
    )
    assert "caller.phone" not in early
    assert "caller.name" not in early

    contact = missing_fields_for_reply(
        ConversationState.COLLECT_CALLER_CONTACT.value,
        intake,
    )
    assert "caller.phone" in contact
