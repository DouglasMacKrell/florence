import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import clear_settings_cache
from app.db.database import Base, get_db_session
from app.db.tables import CallRecord
from app.main import app
from app.services.twilio_stream import parse_twilio_stream_start_message


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("ENABLE_OLLAMA", "false")
    monkeypatch.setenv("ENABLE_TELEPHONY", "true")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://florence.example")
    monkeypatch.setenv("PUBLIC_WEBSOCKET_URL", "wss://florence.example/twilio/media")
    clear_settings_cache()

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        session = testing_session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_db_session] = override_get_db
    with TestClient(app) as test_client:
        yield test_client, testing_session_factory
    app.dependency_overrides.clear()
    clear_settings_cache()


def test_parse_twilio_stream_start_message_extracts_session_id() -> None:
    payload = {
        "event": "start",
        "start": {
            "streamSid": "MZ123",
            "callSid": "CA123",
            "customParameters": {"session_id": "sess-1", "call_id": "call-1"},
        },
    }
    parsed = parse_twilio_stream_start_message(payload)
    assert parsed.stream_sid == "MZ123"
    assert parsed.call_sid == "CA123"
    assert parsed.session_id == "sess-1"
    assert parsed.call_id == "call-1"


def test_twilio_voice_webhook_returns_media_stream_twiml(client) -> None:
    test_client, _ = client
    response = test_client.post(
        "/twilio/voice",
        data={
            "CallSid": "CA999",
            "From": "+15551234567",
            "To": "+15557654321",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    body = response.text
    assert "<Connect>" in body
    assert '<Stream url="wss://florence.example/twilio/media">' in body
    assert 'name="session_id"' in body
    assert 'name="call_id"' in body


def test_twilio_voice_webhook_creates_call_and_session_records(client) -> None:
    test_client, session_factory = client
    response = test_client.post(
        "/twilio/voice",
        data={
            "CallSid": "CA888",
            "From": "+15559876543",
            "To": "+15557654321",
        },
    )
    assert response.status_code == 200
    with session_factory() as db:
        call = db.scalar(select(CallRecord).where(CallRecord.twilio_call_sid == "CA888"))
        assert call is not None
        assert call.caller_phone == "+15559876543"
        assert call.session_id
        assert call.status == "in_progress"


def test_twilio_status_callback_marks_call_completed(client) -> None:
    test_client, session_factory = client
    test_client.post(
        "/twilio/voice",
        data={
            "CallSid": "CA777",
            "From": "+15551112222",
            "To": "+15557654321",
        },
    )
    response = test_client.post(
        "/twilio/status",
        data={"CallSid": "CA777", "CallStatus": "completed"},
    )
    assert response.status_code == 200
    with session_factory() as db:
        call = db.scalar(select(CallRecord).where(CallRecord.twilio_call_sid == "CA777"))
        assert call is not None
        assert call.status == "completed"
        assert call.ended_at is not None


def test_twilio_voice_unavailable_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("ENABLE_OLLAMA", "false")
    monkeypatch.setenv("ENABLE_TELEPHONY", "false")
    clear_settings_cache()

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        session = testing_session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_db_session] = override_get_db
    with TestClient(app) as test_client:
        response = test_client.post("/twilio/voice", data={"CallSid": "CA1"})
        assert response.status_code == 503
    app.dependency_overrides.clear()
    clear_settings_cache()
