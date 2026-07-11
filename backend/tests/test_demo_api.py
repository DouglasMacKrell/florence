from fastapi.testclient import TestClient

from app.main import app


def test_get_demo_script_returns_messages() -> None:
    with TestClient(app) as client:
        response = client.get("/demo/script")
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "queens_daughter_memory_care"
    assert len(payload["user_messages"]) >= 8
