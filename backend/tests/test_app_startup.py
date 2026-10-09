import pytest

from app.config import clear_settings_cache


def test_app_imports_without_telephony_extras(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("PUBLIC_DEMO_MODE", "true")
    monkeypatch.setenv("ENABLE_TELEPHONY", "false")
    clear_settings_cache()

    from app.main import app

    assert app.title == "Florence"
