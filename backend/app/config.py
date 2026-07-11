from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql://florence:florence@localhost:5432/florence"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    cors_origins: str = "http://localhost:5173"
    redact_logs: bool = True
    enable_transcript_persistence: bool = True
    transcript_retention_days: int = 7
    enable_ollama: bool = True
    enable_telephony: bool = False
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    public_base_url: str = ""
    public_websocket_url: str = ""
    piper_voice_id: str = "en_US-lessac-medium"
    whisper_model: str = "Systran/faster-distil-whisper-medium.en"
    telephony_scripted_replies: bool = True

    @property
    def telephony_configured(self) -> bool:
        return bool(self.enable_telephony and self.public_websocket_url)

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
