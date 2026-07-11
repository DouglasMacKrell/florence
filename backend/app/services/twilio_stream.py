from dataclasses import dataclass


@dataclass(frozen=True)
class TwilioStreamStart:
    stream_sid: str
    call_sid: str
    session_id: str | None = None
    call_id: str | None = None


def parse_twilio_stream_start_message(payload: dict) -> TwilioStreamStart:
    if payload.get("event") != "start":
        raise ValueError("Expected Twilio media stream start event")
    start = payload.get("start") or {}
    custom = start.get("customParameters") or {}
    stream_sid = start.get("streamSid")
    call_sid = start.get("callSid")
    if not stream_sid or not call_sid:
        raise ValueError("Twilio start event missing streamSid or callSid")
    return TwilioStreamStart(
        stream_sid=stream_sid,
        call_sid=call_sid,
        session_id=custom.get("session_id"),
        call_id=custom.get("call_id"),
    )
