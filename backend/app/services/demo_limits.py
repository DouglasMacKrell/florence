from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.tables import MessageRecord


def enforce_demo_session_message_cap(
    db: Session,
    session_id: str,
    settings: Settings,
) -> None:
    if not settings.public_demo_mode:
        return

    user_message_count = (
        db.query(MessageRecord).filter_by(session_id=session_id, role="user").count()
    )
    if user_message_count >= settings.demo_max_messages_per_session:
        raise HTTPException(
            status_code=429,
            detail=(
                "This demo session has reached its message limit. "
                "Refresh the page to start a new demonstration session."
            ),
        )
