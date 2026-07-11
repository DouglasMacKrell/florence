import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import clear_settings_cache
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


def _parse_sse_events(body: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    for block in body.split("\n\n"):
        if not block.strip():
            continue
        event_name = "message"
        data_payload: dict = {}
        for line in block.splitlines():
            if line.startswith("event:"):
                event_name = line.removeprefix("event:").strip()
            elif line.startswith("data:"):
                data_payload = json.loads(line.removeprefix("data:").strip())
        events.append((event_name, data_payload))
    return events


def test_stream_message_emits_tokens_and_done(client: TestClient) -> None:
    session = client.post("/sessions").json()
    with client.stream(
        "POST",
        f"/sessions/{session['session_id']}/messages/stream",
        json={"content": "Yes, you may store my information."},
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        body = response.read().decode()

    events = _parse_sse_events(body)
    event_names = [name for name, _ in events]
    assert "token" in event_names
    assert "done" in event_names

    done_payload = next(payload for name, payload in events if name == "done")
    assert done_payload["content"]
    assert done_payload["state"] != "GREETING"
    assert done_payload["intake"]["consent"]["consent_to_store_information"] is True

    token_text = "".join(payload["text"] for name, payload in events if name == "token")
    assert token_text == done_payload["content"]
