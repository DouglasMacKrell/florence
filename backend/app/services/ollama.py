import json
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
    ) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model
        self.timeout_seconds = timeout_seconds

    def chat(self, messages: list[dict[str, str]], *, json_mode: bool = False) -> str:
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

    def chat_json(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        content = self.chat(messages, json_mode=True)
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
