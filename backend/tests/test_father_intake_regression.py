import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import clear_settings_cache
from app.db.database import Base
from app.services.conversation import create_session, process_user_message
from app.services.intake_summary import build_intake_confirmation_message

OPENER = (
    "My dad took a fall a few weeks back and now he's having problems "
    "getting around the house. I think he may need someone to come "
    "around every so often to lend a hand."
)

CARE_NEEDS = (
    "His mind is fine thankfully, but he's having mobility issues since "
    "the fall. So making meals, cleanup, day-to-day stuff is getting harder"
)


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
    finally:
        session.close()
        clear_settings_cache()


def test_father_scenario_intake_and_summary(db_session) -> None:
    session = create_session(db_session)
    db_session.flush()
    session_id = session.id

    steps = [
        OPENER,
        "I agree",
        CARE_NEEDS,
        "87",
        "Soon. Within the week if we can schedule it.",
        "11111",
        "My brother Max",
        "of course",
        "Crash Sexcastle",
        "555 555 5555",
    ]
    last = None
    for content in steps:
        last = process_user_message(db_session, session_id, content)

    assert last is not None
    intake = last.intake
    assert intake.care_recipient.relationship_descriptor == "father"
    assert intake.care_recipient.age == 87
    assert intake.location_preferences.postal_code == "11111"
    assert intake.financial.monthly_budget_max is None
    assert intake.financial.monthly_budget_min is None
    assert intake.caller.name == "Crash Sexcastle"
    assert intake.care_recipient.name != "Max"
    assert intake.caller.relationship_to_care_recipient != "brother"
    assert any("Max" in entry for entry in intake.decision_process.decision_makers)
    assert intake.care_needs.activities_of_daily_living.mobility is True
    assert intake.care_needs.instrumental_needs.meal_preparation is True
    assert intake.care_needs.instrumental_needs.housekeeping is True
    assert intake.care_needs.memory_concerns is False

    summary = build_intake_confirmation_message(intake)
    assert "$11,111" not in summary
    assert "his mind is fine thankfully" not in summary.lower()
    assert "needs help with his mind" not in summary.lower()
    assert "Crash Sexcastle" in summary
    assert "mobility" in summary.lower()
    assert "meal preparation" in summary.lower()
    assert "11111" in summary
