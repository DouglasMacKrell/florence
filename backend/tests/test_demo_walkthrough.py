import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import clear_settings_cache
from app.db.database import Base
from app.demo.walkthrough import load_demo_script, run_demo_walkthrough


@pytest.fixture()
def db_session(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("ENABLE_OLLAMA", "false")
    clear_settings_cache()

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    try:
        yield session
        session.commit()
    finally:
        session.close()
        clear_settings_cache()


def test_load_demo_script_has_user_messages() -> None:
    script = load_demo_script()
    assert script["id"] == "queens_daughter_memory_care"
    assert len(script["user_messages"]) >= 8


def test_run_demo_walkthrough_reaches_provider_matches(db_session) -> None:
    result = run_demo_walkthrough(db_session)

    assert result.session_id
    assert result.final_state in {"MATCH_PROVIDERS", "EXPLAIN_RECOMMENDATIONS"}
    assert 1 <= len(result.matches) <= 3
    assert result.intake.completion_percent() == 100
    assert result.care_recommendation is not None
    assert result.care_recommendation["primary"]


def test_demo_script_file_matches_repo_seed() -> None:
    script_path = Path(__file__).resolve().parents[2] / "data" / "demo_script.json"
    script = json.loads(script_path.read_text())
    assert script["user_messages"][0].lower().startswith("yes")
