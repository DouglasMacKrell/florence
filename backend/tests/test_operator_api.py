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


def test_operator_session_view_includes_lead_score_and_referral_value(client: TestClient) -> None:
    session_id = client.post("/sessions").json()["session_id"]

    from app.demo.walkthrough import load_demo_script

    for message in load_demo_script()["user_messages"]:
        client.post(f"/sessions/{session_id}/messages", json={"content": message})

    response = client.get(f"/operator/sessions/{session_id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["lead_score"] >= 80
    assert payload["lead_category"] == "highly_qualified"
    assert len(payload["transcript"]) >= 10
    assert len(payload["matches"]) >= 1
    assert payload["matches"][0]["estimated_referral_value"] > 0
