import asyncio
import time
from collections.abc import Callable

from loguru import logger
from sqlalchemy.orm import Session

from app.services.call_sessions import get_session_greeting
from app.services.conversation import process_user_message
from app.voice.telephony_turns import shorten_for_phone, should_ignore_transcript


def telephony_pipeline_available() -> bool:
    try:
        import pipecat  # noqa: F401
        import twilio  # noqa: F401
    except ImportError:
        return False
    return True


def build_florence_processor(
    session_id: str,
    session_factory: Callable[[], Session],
    *,
    scripted_replies: bool = True,
):
    from pipecat.frames.frames import (
        BotStartedSpeakingFrame,
        BotStoppedSpeakingFrame,
        Frame,
        TranscriptionFrame,
        TTSSpeakFrame,
    )
    from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

    class FlorenceConversationProcessor(FrameProcessor):
        def __init__(self) -> None:
            super().__init__()
            self._session_id = session_id
            self._session_factory = session_factory
            self._scripted_replies = scripted_replies
            self._bot_speaking = False
            self._turn_lock = asyncio.Lock()
            self._accept_after = 0.0

        def fetch_greeting(self) -> str:
            db = self._session_factory()
            try:
                return shorten_for_phone(get_session_greeting(db, self._session_id))
            finally:
                db.close()

        def _handle_turn(self, text: str) -> str:
            db = self._session_factory()
            try:
                turn = process_user_message(
                    db,
                    self._session_id,
                    text,
                    scripted_reply=self._scripted_replies,
                )
                db.commit()
                return shorten_for_phone(turn.content)
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()

        def _ready_for_caller(self) -> bool:
            if self._bot_speaking:
                return False
            return time.monotonic() >= self._accept_after

        async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
            await super().process_frame(frame, direction)

            if isinstance(frame, BotStartedSpeakingFrame):
                self._bot_speaking = True
                await self.push_frame(frame, direction)
                return

            if isinstance(frame, BotStoppedSpeakingFrame):
                self._bot_speaking = False
                self._accept_after = time.monotonic() + 0.75
                await self.push_frame(frame, direction)
                return

            if isinstance(frame, TranscriptionFrame):
                transcript = frame.text.strip()
                if should_ignore_transcript(transcript):
                    logger.debug("Ignoring telephony filler transcript: {}", transcript)
                    return
                if not self._ready_for_caller():
                    logger.debug("Ignoring transcript while Florence is speaking")
                    return
                if self._turn_lock.locked():
                    logger.debug("Ignoring transcript while prior turn is in progress")
                    return

                async with self._turn_lock:
                    if not self._ready_for_caller():
                        return
                    logger.info("Caller transcript received: {}", transcript[:120])
                    try:
                        reply = await asyncio.to_thread(self._handle_turn, transcript)
                    except Exception as exc:
                        logger.exception("Failed to process telephony turn: {}", exc)
                        reply = "I'm sorry, I had trouble with that. Could you repeat it?"
                    if reply:
                        self._bot_speaking = True
                        await self.push_frame(TTSSpeakFrame(text=reply))
                return

            await self.push_frame(frame, direction)

    return FlorenceConversationProcessor()
