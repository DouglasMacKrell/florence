import asyncio
import json
from collections.abc import Callable

from fastapi import WebSocket
from loguru import logger
from sqlalchemy.orm import Session

from app.config import Settings
from app.services.call_sessions import update_call_status
from app.services.twilio_stream import parse_twilio_stream_start_message
from app.voice.florence_processor import build_florence_processor, telephony_pipeline_available


def _telephony_vad_analyzer():
    from pipecat.audio.vad.silero import SileroVADAnalyzer
    from pipecat.audio.vad.vad_analyzer import VADParams

    # Phone audio is noisier; longer stop window reduces chopped utterances.
    return SileroVADAnalyzer(
        params=VADParams(
            confidence=0.6,
            start_secs=0.25,
            stop_secs=1.0,
            min_volume=0.45,
        )
    )


async def read_twilio_stream_start(websocket: WebSocket):
    while True:
        message = await websocket.receive_text()
        payload = json.loads(message)
        if payload.get("event") == "start":
            return parse_twilio_stream_start_message(payload)


async def run_twilio_call_pipeline(
    websocket: WebSocket,
    *,
    stream_sid: str,
    call_sid: str,
    session_id: str,
    session_factory: Callable[[], Session],
    settings: Settings,
) -> None:
    if not telephony_pipeline_available():
        raise RuntimeError("Telephony pipeline dependencies are not installed")

    from pipecat.frames.frames import EndFrame, TTSSpeakFrame
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.worker import PipelineParams, PipelineTask
    from pipecat.processors.audio.vad_processor import VADProcessor
    from pipecat.serializers.twilio import TwilioFrameSerializer
    from pipecat.services.piper.tts import PiperTTSService
    from pipecat.services.whisper.stt import WhisperSTTService
    from pipecat.transports.websocket.fastapi import (
        FastAPIWebsocketParams,
        FastAPIWebsocketTransport,
    )
    from pipecat.workers.runner import WorkerRunner

    serializer = TwilioFrameSerializer(
        stream_sid=stream_sid,
        call_sid=call_sid,
        account_sid=settings.twilio_account_sid or None,
        auth_token=settings.twilio_auth_token or None,
    )
    transport = FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            serializer=serializer,
        ),
    )
    vad = VADProcessor(vad_analyzer=_telephony_vad_analyzer(), audio_idle_timeout=2.5)
    stt = WhisperSTTService(model=settings.whisper_model)
    florence = build_florence_processor(
        session_id,
        session_factory,
        scripted_replies=settings.telephony_scripted_replies,
    )
    tts = PiperTTSService(voice_id=settings.piper_voice_id)
    pipeline = Pipeline(
        [
            transport.input(),
            vad,
            stt,
            florence,
            tts,
            transport.output(),
        ]
    )
    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            audio_in_sample_rate=16000,
            audio_out_sample_rate=8000,
            allow_interruptions=False,
        ),
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, _websocket) -> None:
        greeting = await asyncio.to_thread(florence.fetch_greeting)
        await task.queue_frame(TTSSpeakFrame(text=greeting))

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, _websocket) -> None:
        await task.queue_frame(EndFrame())
        db = session_factory()
        try:
            update_call_status(db, twilio_call_sid=call_sid, status="completed")
            db.commit()
        finally:
            db.close()

    runner = WorkerRunner()
    await runner.add_workers(task)
    await runner.run()


async def handle_twilio_media_stream(
    websocket: WebSocket,
    *,
    session_factory: Callable[[], Session],
    settings: Settings,
) -> None:
    await websocket.accept()
    try:
        start = await read_twilio_stream_start(websocket)
    except Exception as exc:
        logger.warning("Failed to parse Twilio media stream start: {}", exc)
        await websocket.close(code=1003, reason="Invalid Twilio media stream")
        return

    if not start.session_id:
        await websocket.close(code=1008, reason="Missing session_id")
        return

    try:
        await run_twilio_call_pipeline(
            websocket,
            stream_sid=start.stream_sid,
            call_sid=start.call_sid,
            session_id=start.session_id,
            session_factory=session_factory,
            settings=settings,
        )
    except Exception as exc:
        logger.exception("Telephony pipeline failed: {}", exc)
        if websocket.client_state.name != "DISCONNECTED":
            await websocket.close(code=1011, reason="Telephony pipeline error")
