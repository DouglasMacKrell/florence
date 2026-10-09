import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings, clear_settings_cache
from app.db.database import Base, get_db_session
from app.main import app


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("ENABLE_OLLAMA", "false")
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
        yield test_client
    app.dependency_overrides.clear()
    clear_settings_cache()


def test_public_demo_mode_defaults_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PUBLIC_DEMO_MODE", raising=False)
    clear_settings_cache()
    settings = Settings(_env_file=None)
    assert settings.public_demo_mode is False
    assert settings.demo_max_messages_per_session == 50


def test_telephony_disabled_when_public_demo_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PUBLIC_DEMO_MODE", "true")
    monkeypatch.setenv("ENABLE_TELEPHONY", "true")
    monkeypatch.setenv("PUBLIC_WEBSOCKET_URL", "wss://example.com/twilio/media")
    clear_settings_cache()
    settings = Settings(_env_file=None)
    assert settings.telephony_configured is False


def test_demo_session_message_cap_blocks_stream(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PUBLIC_DEMO_MODE", "true")
    monkeypatch.setenv("DEMO_MAX_MESSAGES_PER_SESSION", "1")
    clear_settings_cache()

    session = client.post("/sessions").json()
    session_id = session["session_id"]

    first = client.post(
        f"/sessions/{session_id}/messages/stream",
        json={"content": "Yes, you may store my information."},
    )
    assert first.status_code == 200

    second = client.post(
        f"/sessions/{session_id}/messages/stream",
        json={"content": "My father needs help at home."},
    )
    assert second.status_code == 429
    assert "message limit" in second.json()["detail"].lower()


def test_demo_cap_not_applied_when_public_demo_off(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PUBLIC_DEMO_MODE", "false")
    monkeypatch.setenv("DEMO_MAX_MESSAGES_PER_SESSION", "1")
    clear_settings_cache()

    session = client.post("/sessions").json()
    session_id = session["session_id"]

    first = client.post(
        f"/sessions/{session_id}/messages/stream",
        json={"content": "Yes, you may store my information."},
    )
    second = client.post(
        f"/sessions/{session_id}/messages/stream",
        json={"content": "My father needs help at home."},
    )
    assert first.status_code == 200
    assert second.status_code == 200
