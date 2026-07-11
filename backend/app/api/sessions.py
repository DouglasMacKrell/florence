import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.schemas import (
    CreateSessionResponse,
    SelectProviderRequest,
    SendMessageRequest,
    SendMessageResponse,
    SessionDetailResponse,
)
from app.db.database import get_db_session
from app.db.tables import (
    CareRecommendationRecordORM,
    MatchRecordORM,
    MessageRecord,
    ReferralRecordORM,
)
from app.models.intake import IntakeRecord
from app.services.conversation import (
    complete_user_message_turn,
    confirm_referral,
    create_session,
    get_session,
    prepare_user_message_turn,
    process_user_message,
    select_provider,
    stream_user_message_tokens,
)
from app.services.provider_loader import load_providers_from_seed
from app.services.response_generation import finalize_assistant_reply

router = APIRouter(prefix="/sessions", tags=["sessions"])
DbSession = Annotated[Session, Depends(get_db_session)]


@router.post("", response_model=CreateSessionResponse)
def start_session(db: DbSession) -> CreateSessionResponse:
    load_providers_from_seed(db)
    session = create_session(db)
    greeting = db.query(MessageRecord).filter_by(session_id=session.id, role="assistant").first()
    return CreateSessionResponse(
        session_id=session.id,
        state=session.current_state,
        greeting=greeting.content if greeting else "",
    )


@router.get("/{session_id}", response_model=SessionDetailResponse)
def read_session(session_id: str, db: DbSession) -> SessionDetailResponse:
    session = get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    intake = IntakeRecord.model_validate(session.intake.structured_json if session.intake else {})
    messages = [
        {
            "role": message.role,
            "content": message.content,
            "created_at": message.created_at.isoformat(),
        }
        for message in sorted(session.messages, key=lambda item: item.created_at)
    ]
    matches = [
        row.explanation_json
        for row in db.query(MatchRecordORM)
        .filter_by(session_id=session_id)
        .order_by(MatchRecordORM.rank)
    ]
    recommendation = (
        db.query(CareRecommendationRecordORM).filter_by(session_id=session_id).one_or_none()
    )
    referral = db.query(ReferralRecordORM).filter_by(session_id=session_id).one_or_none()

    return SessionDetailResponse(
        session_id=session.id,
        state=session.current_state,
        status=session.status,
        intake=intake,
        completion_percent=intake.completion_percent(),
        missing_fields=intake.missing_required_fields(),
        messages=messages,
        matches=matches,
        care_recommendation=(
            {
                "primary": recommendation.primary_care_type,
                "alternatives": recommendation.alternatives_json,
                "rationale": recommendation.rationale,
            }
            if recommendation
            else None
        ),
        referral=(
            {"provider_id": referral.provider_id, "status": referral.status} if referral else None
        ),
    )


@router.post("/{session_id}/messages", response_model=SendMessageResponse)
def send_message(
    session_id: str,
    payload: SendMessageRequest,
    db: DbSession,
) -> SendMessageResponse:
    try:
        turn = process_user_message(db, session_id, payload.content)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return SendMessageResponse(
        content=turn.content,
        state=turn.state,
        intake=turn.intake,
        matches=turn.matches,
        care_recommendation=turn.care_recommendation,
    )


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


@router.post("/{session_id}/messages/stream")
def stream_message(
    session_id: str,
    payload: SendMessageRequest,
    db: DbSession,
) -> StreamingResponse:
    try:
        prepared = prepare_user_message_turn(db, session_id, payload.content)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    def event_stream():
        chunks: list[str] = []
        try:
            for token in stream_user_message_tokens(prepared):
                chunks.append(token)
                yield _sse_event("token", {"text": token})
            reply = finalize_assistant_reply(
                "".join(chunks),
                state=prepared.conversation_state,
                fallback=prepared.fallback,
            )
            turn = complete_user_message_turn(db, prepared, reply)
            yield _sse_event(
                "done",
                {
                    "content": turn.content,
                    "state": turn.state,
                    "intake": turn.intake.model_dump(),
                    "matches": turn.matches,
                    "care_recommendation": turn.care_recommendation,
                },
            )
        except Exception as exc:
            yield _sse_event("error", {"detail": str(exc)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/{session_id}/select-provider")
def choose_provider(
    session_id: str,
    payload: SelectProviderRequest,
    db: DbSession,
) -> dict:
    try:
        return select_provider(db, session_id, payload.provider_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{session_id}/confirm-referral")
def submit_referral(session_id: str, db: DbSession) -> dict:
    try:
        return confirm_referral(db, session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
