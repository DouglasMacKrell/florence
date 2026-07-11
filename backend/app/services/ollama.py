import json
import time
from collections.abc import Iterator
from typing import Any

import httpx

from app.config import get_settings


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 60.0,
        max_retries: int | None = None,
    ) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model
        self.timeout_seconds = timeout_seconds
        self.max_retries = settings.ollama_max_retries if max_retries is None else max_retries

    def chat(self, messages: list[dict[str, str]], *, json_mode: bool = False) -> str:
        last_error: OllamaError | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return self._chat_once(messages, json_mode=json_mode)
            except OllamaError as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(0.2 * (attempt + 1))
        assert last_error is not None
        raise last_error

    def _chat_once(self, messages: list[dict[str, str]], *, json_mode: bool) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        if json_mode:
            payload["format"] = "json"

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(f"{self.base_url}/api/chat", json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise OllamaError(str(exc)) from exc

        data = response.json()
        message = data.get("message", {})
        content = message.get("content")
        if not isinstance(content, str):
            raise OllamaError("Ollama response missing assistant content")
        return content

    def chat_stream(self, messages: list[dict[str, str]]) -> Iterator[str]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }

        try:
            with (
                httpx.Client(timeout=self.timeout_seconds) as client,
                client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json=payload,
                ) as response,
            ):
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    message = data.get("message", {})
                    content = message.get("content")
                    if isinstance(content, str) and content:
                        yield content
        except httpx.HTTPError as exc:
            raise OllamaError(str(exc)) from exc

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
                raise OllamaError("Ollama returned invalid JSON") from exc
        if not isinstance(parsed, dict):
            raise OllamaError("Ollama JSON payload must be an object")
        return parsed

    def is_available(self) -> bool:
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
            return True
        except httpx.HTTPError:
            return False
