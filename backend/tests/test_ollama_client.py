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
    client = OllamaClient(base_url="http://localhost:11434", model="llama3.2:3b")
    with pytest.raises(OllamaError):
        client.chat([{"role": "user", "content": "Hello"}])
