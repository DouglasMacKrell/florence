import json
import time
from collections.abc import Iterator
from typing import Any, Protocol

import httpx

from app.config import get_settings
from app.services.ollama import OllamaClient, OllamaError


class LlmError(RuntimeError):
    pass


class LlmClient(Protocol):
    def chat(self, messages: list[dict[str, str]], *, json_mode: bool = False) -> str: ...

    def chat_stream(self, messages: list[dict[str, str]]) -> Iterator[str]: ...

    def chat_json(self, messages: list[dict[str, str]]) -> dict[str, Any]: ...

    def is_available(self) -> bool: ...


class OllamaLlmClient:
    def __init__(self, *, client: OllamaClient | None = None) -> None:
        self._client = client or OllamaClient()

    def chat(self, messages: list[dict[str, str]], *, json_mode: bool = False) -> str:
        try:
            return self._client.chat(messages, json_mode=json_mode)
        except OllamaError as exc:
            raise LlmError(str(exc)) from exc

    def chat_stream(self, messages: list[dict[str, str]]) -> Iterator[str]:
        try:
            yield from self._client.chat_stream(messages)
        except OllamaError as exc:
            raise LlmError(str(exc)) from exc

    def chat_json(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        try:
            return self._client.chat_json(messages)
        except OllamaError as exc:
            raise LlmError(str(exc)) from exc

    def is_available(self) -> bool:
        return self._client.is_available()


class GroqLlmClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 60.0,
        max_retries: int | None = None,
    ) -> None:
        settings = get_settings()
        self.api_key = api_key if api_key is not None else settings.groq_api_key
        self.base_url = (base_url or settings.groq_base_url).rstrip("/")
        self.model = model or settings.groq_model
        self.timeout_seconds = timeout_seconds
        self.max_retries = settings.llm_max_retries if max_retries is None else max_retries

    def is_available(self) -> bool:
        return bool(self.api_key.strip())

    def chat(self, messages: list[dict[str, str]], *, json_mode: bool = False) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        last_error: LlmError | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return self._chat_once(payload)
            except LlmError as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(0.2 * (attempt + 1))
        assert last_error is not None
        raise last_error

    def _chat_once(self, payload: dict[str, Any]) -> str:
        if not self.is_available():
            raise LlmError("Groq API key is not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LlmError(str(exc)) from exc

        data = response.json()
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LlmError("Groq response missing choices")
        message = choices[0].get("message", {})
        content = message.get("content")
        if not isinstance(content, str):
            raise LlmError("Groq response missing assistant content")
        return content

    def chat_stream(self, messages: list[dict[str, str]]) -> Iterator[str]:
        if not self.is_available():
            raise LlmError("Groq API key is not configured")

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            with (
                httpx.Client(timeout=self.timeout_seconds) as client,
                client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                ) as response,
            ):
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line.removeprefix("data:").strip()
                    if data_str == "[DONE]":
                        break
                    chunk = json.loads(data_str)
                    choices = chunk.get("choices")
                    if not isinstance(choices, list) or not choices:
                        continue
                    delta = choices[0].get("delta", {})
                    content = delta.get("content")
                    if isinstance(content, str) and content:
                        yield content
        except httpx.HTTPError as exc:
            raise LlmError(str(exc)) from exc

    def chat_json(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        content = self.chat(messages, json_mode=True)
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            repair_messages = [
                *messages,
                {
                    "role": "user",
                    "content": "Your previous response was not valid JSON. Reply with JSON only.",
                },
            ]
            content = self.chat(repair_messages, json_mode=True)
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError as exc:
                raise LlmError("Groq returned invalid JSON") from exc
        if not isinstance(parsed, dict):
            raise LlmError("Groq JSON payload must be an object")
        return parsed


def get_llm_client(*, client: LlmClient | None = None) -> LlmClient:
    if client is not None:
        return client
    settings = get_settings()
    if settings.inference_provider == "groq":
        return GroqLlmClient()
    return OllamaLlmClient()
