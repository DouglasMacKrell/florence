from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.db.tables import CallRecord
from app.models.intake import IntakeRecord
from app.services.conversation import create_session, get_session


def start_inbound_call(
    db: Session,
    *,
    twilio_call_sid: str,
    caller_phone: str | None = None,
) -> CallRecord:
    existing = db.query(CallRecord).filter_by(twilio_call_sid=twilio_call_sid).one_or_none()
    if existing is not None:
        return existing

    session = create_session(db)
    if caller_phone and session.intake is not None:
        intake = IntakeRecord.model_validate(session.intake.structured_json)
        intake.caller.phone = caller_phone
        session.intake.structured_json = intake.model_dump()
    call = CallRecord(
        session_id=session.id,
        twilio_call_sid=twilio_call_sid,
        caller_phone=caller_phone,
        status="in_progress",
        started_at=datetime.now(UTC),
    )
    db.add(call)
    db.flush()
    return call


def update_call_status(
    db: Session,
    *,
    twilio_call_sid: str,
    status: str,
) -> CallRecord | None:
    call = db.query(CallRecord).filter_by(twilio_call_sid=twilio_call_sid).one_or_none()
    if call is None:
        return None
    call.status = status
    if status in {"completed", "busy", "failed", "no-answer", "canceled"}:
        call.ended_at = datetime.now(UTC)
    db.flush()
    return call


def get_call_by_twilio_sid(db: Session, twilio_call_sid: str) -> CallRecord | None:
    return db.query(CallRecord).filter_by(twilio_call_sid=twilio_call_sid).one_or_none()


def get_session_greeting(db: Session, session_id: str) -> str:
    session = get_session(db, session_id)
    if session is None:
        return "Hello, I'm Florence, a care navigation assistant."
    for message in sorted(session.messages, key=lambda item: item.created_at):
        if message.role == "assistant" and message.content.strip():
            return message.content
    return "Hello, I'm Florence, a care navigation assistant."
