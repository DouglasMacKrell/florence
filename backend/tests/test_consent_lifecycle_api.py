import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agent.consent_boundary import (
    FOLLOW_UP_CONTACT_CLARIFICATION,
    FOLLOW_UP_CONTACT_QUESTION,
    STORE_INFORMATION_CLARIFICATION,
    STORE_INFORMATION_QUESTION,
)
from app.config import clear_settings_cache
from app.db.database import Base, get_db_session
from app.main import app
from app.services.intake_summary import SUMMARY_CONFIRMATION_QUESTION
from app.services.provider_loader import load_providers_from_seed

OPENING = (
    "I'm looking for care for my 82-year-old mother in ZIP code 11375. "
    "She's starting to need help around the house."
)


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
    bootstrap = testing_session_factory()
    load_providers_from_seed(bootstrap)
    bootstrap.commit()
    bootstrap.close()

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


def _post_turn(client: TestClient, session_id: str, content: str, *, stream: bool) -> dict:
    if not stream:
        response = client.post(
            f"/sessions/{session_id}/messages",
            json={"content": content},
        )
        assert response.status_code == 200
        return response.json()

    with client.stream(
        "POST",
        f"/sessions/{session_id}/messages/stream",
        json={"content": content},
    ) as response:
        assert response.status_code == 200
        body = response.read().decode()
    events = _parse_sse_events(body)
    done_payload = next(payload for name, payload in events if name == "done")
    token_text = "".join(payload["text"] for name, payload in events if name == "token")
    assert token_text == done_payload["content"]
    return done_payload


@pytest.mark.parametrize("stream", [False, True])
def test_storage_consent_opener_and_typo_clarification(client: TestClient, stream: bool) -> None:
    session = client.post("/sessions").json()
    session_id = session["session_id"]

    first = _post_turn(client, session_id, OPENING, stream=stream)
    assert first["state"] == "DISCLOSURE_AND_CONSENT"
    assert STORE_INFORMATION_QUESTION in first["content"]
    assert STORE_INFORMATION_CLARIFICATION not in first["content"]
    assert "I need a clear yes or no" not in first["content"]
    assert first["intake"]["consent"]["consent_to_store_information"] is not True
    assert first["intake"]["location_preferences"]["postal_code"] == "11375"
    assert first["intake"]["care_recipient"]["age"] == 82

    second = _post_turn(client, session_id, "tes", stream=stream)
    assert second["state"] == "DISCLOSURE_AND_CONSENT"
    assert second["content"] == STORE_INFORMATION_CLARIFICATION
    assert second["intake"]["consent"]["consent_to_store_information"] is not True

    third = _post_turn(client, session_id, "yes", stream=stream)
    assert third["intake"]["consent"]["consent_to_store_information"] is True
    assert third["state"] != "DISCLOSURE_AND_CONSENT"
    assert STORE_INFORMATION_QUESTION not in third["content"]


def _fill_intake_to_follow_up(client: TestClient, session_id: str) -> dict:
    """After storage consent, send turns until follow-up contact consent is asked."""
    last = _post_turn(client, session_id, "within the next month", stream=False)
    if last["state"] == "COLLECT_LOCATION_REQUIREMENTS":
        last = _post_turn(client, session_id, "11375 works for us.", stream=False)
    last = _post_turn(
        client,
        session_id,
        "Our budget is about 7000 dollars per month.",
        stream=False,
    )
    if last["state"] == "COLLECT_PREFERENCES":
        last = _post_turn(client, session_id, "No special preferences.", stream=False)
    if last["state"] == "UNDERSTAND_DECISION_PROCESS":
        last = _post_turn(
            client,
            session_id,
            "I make the decisions with my siblings.",
            stream=False,
        )
    assert last["state"] == "COLLECT_FOLLOWUP_CONSENT"
    assert FOLLOW_UP_CONTACT_QUESTION in last["content"]
    return last


def test_follow_up_consent_decline_does_not_mark_contact(client: TestClient) -> None:
    session = client.post("/sessions").json()
    session_id = session["session_id"]
    _post_turn(client, session_id, OPENING, stream=False)
    _post_turn(client, session_id, "yes", stream=False)
    _fill_intake_to_follow_up(client, session_id)

    decline = _post_turn(client, session_id, "no", stream=False)
    assert decline["intake"]["consent"]["consent_to_contact"] is False
    assert decline["intake"]["consent"]["consent_to_contact"] is not True


@pytest.mark.parametrize("stream", [False, True])
def test_follow_up_tes_does_not_persist_caller_name(client: TestClient, stream: bool) -> None:
    session = client.post("/sessions").json()
    session_id = session["session_id"]
    _post_turn(client, session_id, OPENING, stream=False)
    _post_turn(client, session_id, "yes", stream=False)
    before = _fill_intake_to_follow_up(client, session_id)
    intake_before = before["intake"]

    typo = _post_turn(client, session_id, "tes", stream=stream)
    assert typo["state"] == "COLLECT_FOLLOWUP_CONSENT"
    assert typo["content"] == FOLLOW_UP_CONTACT_CLARIFICATION
    assert typo["intake"]["consent"]["consent_to_contact"] is None
    assert typo["intake"].get("caller", {}).get("name") in {None, ""}
    assert typo["intake"]["care_recipient"] == intake_before["care_recipient"]
    assert typo["intake"]["location_preferences"] == intake_before["location_preferences"]
    assert typo["intake"]["timing"] == intake_before["timing"]
    assert typo["intake"]["financial"] == intake_before["financial"]

    affirm = _post_turn(client, session_id, "yes", stream=False)
    assert affirm["intake"]["consent"]["consent_to_contact"] is True
    assert affirm["state"] == "COLLECT_CALLER_CONTACT"

    named = _post_turn(client, session_id, "Douglas MacKrell", stream=False)
    assert named["intake"]["caller"]["name"] == "Douglas MacKrell"

    phone = _post_turn(client, session_id, "347-495-1109", stream=False)
    assert phone["state"] == "CONFIRM_SUMMARY"
    assert phone["intake"]["caller"]["name"] == "Douglas MacKrell"
    assert "tes —" not in phone["content"]
    assert "Douglas MacKrell" in phone["content"]
    assert "347-495-1109" in phone["content"] or "347" in phone["content"]


def test_follow_up_consent_affirmative_after_clarification(client: TestClient) -> None:
    session = client.post("/sessions").json()
    session_id = session["session_id"]
    _post_turn(client, session_id, OPENING, stream=False)
    _post_turn(client, session_id, "yes", stream=False)
    _fill_intake_to_follow_up(client, session_id)

    typo = _post_turn(client, session_id, "tes", stream=False)
    assert typo["content"] == FOLLOW_UP_CONTACT_CLARIFICATION
    assert typo["intake"]["consent"]["consent_to_contact"] is None

    affirm = _post_turn(client, session_id, "yes", stream=False)
    assert affirm["intake"]["consent"]["consent_to_contact"] is True


@pytest.mark.parametrize("stream", [False, True])
def test_full_lifecycle_reaches_matching(client: TestClient, stream: bool) -> None:
    session = client.post("/sessions").json()
    session_id = session["session_id"]

    _post_turn(client, session_id, OPENING, stream=stream)
    _post_turn(client, session_id, "tes", stream=stream)
    _post_turn(client, session_id, "yes", stream=stream)

    _fill_intake_to_follow_up(client, session_id)
    _post_turn(client, session_id, "yes", stream=False)
    _post_turn(client, session_id, "Douglas MacKrell", stream=False)

    contact = _post_turn(client, session_id, "555-123-4567", stream=False)
    assert contact["state"] == "CONFIRM_SUMMARY"
    assert SUMMARY_CONFIRMATION_QUESTION in contact["content"]
    assert "11375" in contact["content"]

    confirmed = _post_turn(
        client,
        session_id,
        "Yes, that sounds accurate.",
        stream=False,
    )
    assert confirmed["state"] == "MATCH_PROVIDERS"
    assert confirmed.get("matches") is not None
    assert len(confirmed["matches"]) > 0
