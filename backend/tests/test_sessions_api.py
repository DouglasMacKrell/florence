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


def test_create_session_returns_greeting(client: TestClient) -> None:
    response = client.post("/sessions")
    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"]
    assert payload["state"] == "GREETING"
    assert "Florence" in payload["greeting"]


def test_send_message_advances_state(client: TestClient) -> None:
    session = client.post("/sessions").json()
    response = client.post(
        f"/sessions/{session['session_id']}/messages",
        json={"content": "Yes, you may store my information."},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["state"] != "GREETING"
    assert payload["intake"]["consent"]["consent_to_store_information"] is True


def test_get_session_returns_messages(client: TestClient) -> None:
    session = client.post("/sessions").json()
    client.post(
        f"/sessions/{session['session_id']}/messages",
        json={"content": "My father needs help at home."},
    )
    response = client.get(f"/sessions/{session['session_id']}")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["messages"]) >= 2
    assert payload["completion_percent"] >= 0
