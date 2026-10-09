import json

import httpx
import pytest

from app.config import clear_settings_cache
from app.services.llm_client import GroqLlmClient, LlmError, OllamaLlmClient, get_llm_client


def _groq_response(status_code: int, payload: dict) -> httpx.Response:
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    return httpx.Response(status_code, json=payload, request=request)


def test_get_llm_client_uses_ollama_when_provider_is_ollama(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("INFERENCE_PROVIDER", "ollama")
    clear_settings_cache()
    client = get_llm_client()
    assert isinstance(client, OllamaLlmClient)


def test_get_llm_client_uses_groq_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INFERENCE_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    clear_settings_cache()
    client = get_llm_client()
    assert isinstance(client, GroqLlmClient)


def test_groq_chat_returns_assistant_message(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_post(self, url: str, **kwargs) -> httpx.Response:
        assert url.endswith("/chat/completions")
        assert kwargs["headers"]["Authorization"] == "Bearer test-key"
        return _groq_response(
            200,
            {"choices": [{"message": {"role": "assistant", "content": "Hello from Groq"}}]},
        )

    monkeypatch.setattr(httpx.Client, "post", mock_post)
    client = GroqLlmClient(api_key="test-key", model="test-model", max_retries=0)
    content = client.chat([{"role": "user", "content": "Hi"}])
    assert content == "Hello from Groq"


def test_groq_chat_json_uses_json_object_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"caller_name": "Alex"}

    def mock_post(self, url: str, **kwargs) -> httpx.Response:
        body = kwargs["json"]
        assert body["response_format"] == {"type": "json_object"}
        return _groq_response(
            200,
            {"choices": [{"message": {"role": "assistant", "content": json.dumps(payload)}}]},
        )

    monkeypatch.setattr(httpx.Client, "post", mock_post)
    client = GroqLlmClient(api_key="test-key", model="test-model", max_retries=0)
    result = client.chat_json([{"role": "user", "content": "Extract"}])
    assert result == payload


def test_groq_chat_stream_yields_delta_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    stream_lines = [
        'data: {"choices":[{"delta":{"content":"Hel"}}]}',
        'data: {"choices":[{"delta":{"content":"lo"}}]}',
        "data: [DONE]",
    ]

    class MockStream:
        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

        def raise_for_status(self) -> None:
            return None

        def iter_lines(self):
            yield from stream_lines

    class MockClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

        def stream(self, *args, **kwargs):
            return MockStream()

    monkeypatch.setattr(httpx, "Client", MockClient)
    client = GroqLlmClient(api_key="test-key", model="test-model")
    tokens = list(client.chat_stream([{"role": "user", "content": "Hi"}]))
    assert tokens == ["Hel", "lo"]


def test_groq_chat_retries_transient_error(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"count": 0}

    def mock_post(self, url: str, **kwargs) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return _groq_response(503, {"error": "unavailable"})
        return _groq_response(
            200,
            {"choices": [{"message": {"role": "assistant", "content": "OK"}}]},
        )

    monkeypatch.setattr(httpx.Client, "post", mock_post)
    monkeypatch.setattr("app.services.llm_client.time.sleep", lambda _seconds: None)
    client = GroqLlmClient(api_key="test-key", model="test-model", max_retries=1)
    assert client.chat([{"role": "user", "content": "Hi"}]) == "OK"
    assert calls["count"] == 2


def test_groq_unavailable_without_api_key() -> None:
    client = GroqLlmClient(api_key="", model="test-model", max_retries=0)
    assert client.is_available() is False
    with pytest.raises(LlmError):
        client.chat([{"role": "user", "content": "Hi"}])
