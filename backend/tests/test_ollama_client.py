import json

import httpx
import pytest

from app.services.ollama import OllamaClient, OllamaError


def _mock_response(status_code: int, payload: dict) -> httpx.Response:
    request = httpx.Request("POST", "http://localhost:11434/api/chat")
    return httpx.Response(status_code, json=payload, request=request)


def test_chat_returns_assistant_message(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_post(self, url: str, **kwargs) -> httpx.Response:
        assert url.endswith("/api/chat")
        return _mock_response(
            200,
            {"message": {"role": "assistant", "content": "How can I help you today?"}},
        )

    monkeypatch.setattr(httpx.Client, "post", mock_post)
    client = OllamaClient(base_url="http://localhost:11434", model="llama3.2:3b")
    content = client.chat([{"role": "user", "content": "Hello"}])
    assert content == "How can I help you today?"


def test_chat_json_parses_structured_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"caller_name": "Jane Doe", "care_recipient_age": 82}

    def mock_post(self, url: str, **kwargs) -> httpx.Response:
        return _mock_response(
            200,
            {"message": {"role": "assistant", "content": json.dumps(payload)}},
        )

    monkeypatch.setattr(httpx.Client, "post", mock_post)
    client = OllamaClient(base_url="http://localhost:11434", model="llama3.2:3b")
    result = client.chat_json([{"role": "user", "content": "Extract fields"}])
    assert result == payload


def test_chat_raises_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_post(self, url: str, **kwargs) -> httpx.Response:
        return _mock_response(503, {"error": "model unavailable"})

    monkeypatch.setattr(httpx.Client, "post", mock_post)
    client = OllamaClient(base_url="http://localhost:11434", model="llama3.2:3b", max_retries=0)
    with pytest.raises(OllamaError):
        client.chat([{"role": "user", "content": "Hello"}])


def test_chat_retries_transient_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"count": 0}

    def mock_post(self, url: str, **kwargs) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return _mock_response(503, {"error": "model unavailable"})
        return _mock_response(
            200,
            {"message": {"role": "assistant", "content": "Recovered"}},
        )

    monkeypatch.setattr(httpx.Client, "post", mock_post)
    monkeypatch.setattr("app.services.ollama.time.sleep", lambda _seconds: None)
    client = OllamaClient(base_url="http://localhost:11434", model="llama3.2:3b", max_retries=1)
    content = client.chat([{"role": "user", "content": "Hello"}])
    assert content == "Recovered"
    assert calls["count"] == 2


def test_chat_json_retries_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    payloads = [
        {"message": {"role": "assistant", "content": "not-json"}},
        {"message": {"role": "assistant", "content": json.dumps({"caller_name": "Doug"})}},
    ]

    def mock_post(self, url: str, **kwargs) -> httpx.Response:
        return _mock_response(200, payloads.pop(0))

    monkeypatch.setattr(httpx.Client, "post", mock_post)
    client = OllamaClient(base_url="http://localhost:11434", model="llama3.2:3b", max_retries=0)
    result = client.chat_json([{"role": "user", "content": "Extract fields"}])
    assert result == {"caller_name": "Doug"}
