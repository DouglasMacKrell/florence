from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, WebSocket
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.database import get_db_session, get_session_factory
from app.services.call_sessions import start_inbound_call, update_call_status
from app.services.twilio_security import validate_twilio_request
from app.services.twilio_twiml import build_error_twiml, build_stream_twiml
from app.voice.florence_processor import telephony_pipeline_available
from app.voice.pipeline import handle_twilio_media_stream

router = APIRouter(prefix="/twilio", tags=["twilio"])
DbSession = Annotated[Session, Depends(get_db_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.post("/voice")
async def twilio_voice_webhook(
    request: Request,
    db: DbSession,
    settings: SettingsDep,
) -> Response:
    if not settings.telephony_configured:
        raise HTTPException(status_code=503, detail="Telephony is not enabled")
    if not settings.public_websocket_url:
        return Response(
            content=build_error_twiml("Florence telephony is not configured yet."),
            media_type="application/xml",
        )

    payload = await validate_twilio_request(request, settings)
    call_sid = payload.get("CallSid")
    if not call_sid:
        raise HTTPException(status_code=400, detail="Missing CallSid")

    call = start_inbound_call(
        db,
        twilio_call_sid=call_sid,
        caller_phone=payload.get("From"),
    )
    twiml = build_stream_twiml(
        stream_url=settings.public_websocket_url,
        parameters={
            "session_id": call.session_id,
            "call_id": call.id,
        },
    )
    return Response(content=twiml, media_type="application/xml")


@router.post("/status")
async def twilio_status_callback(
    request: Request,
    db: DbSession,
    settings: SettingsDep,
) -> dict[str, str]:
    if not settings.telephony_configured:
        raise HTTPException(status_code=503, detail="Telephony is not enabled")

    payload = await validate_twilio_request(request, settings)
    call_sid = payload.get("CallSid")
    status = payload.get("CallStatus")
    if call_sid and status:
        update_call_status(db, twilio_call_sid=call_sid, status=status)
    return {"status": "ok"}


@router.websocket("/media")
async def twilio_media_stream(
    websocket: WebSocket,
    settings: SettingsDep,
) -> None:
    if not settings.telephony_configured:
        await websocket.close(code=1008, reason="Telephony is not enabled")
        return
    if not telephony_pipeline_available():
        await websocket.accept()
        await websocket.close(
            code=1011,
            reason="Install telephony extras: pip install '.[telephony]'",
        )
        return

    await handle_twilio_media_stream(
        websocket,
        session_factory=get_session_factory(),
        settings=settings,
    )
