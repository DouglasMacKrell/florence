from app.config import Settings, clear_settings_cache


def test_settings_loads_defaults(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("REDACT_LOGS", raising=False)
    clear_settings_cache()
    settings = Settings(_env_file=None)
    assert settings.ollama_base_url == "http://localhost:11434"
    assert settings.redact_logs is True
    assert "http://localhost:5173" in settings.cors_origins_list
