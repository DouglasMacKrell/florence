from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.intake import IntakeRecord
from app.services.conversation import AssistantTurn, create_session, process_user_message
from app.services.provider_loader import load_providers_from_seed

DEFAULT_SCRIPT_PATH = Path(__file__).resolve().parents[3] / "data" / "demo_script.json"


@dataclass
class WalkthroughResult:
    session_id: str
    final_state: str
    intake: IntakeRecord
    matches: list[dict]
    care_recommendation: dict | None
    turns: list[AssistantTurn]


def load_demo_script(script_path: Path | None = None) -> dict:
    path = script_path or DEFAULT_SCRIPT_PATH
    return json.loads(path.read_text())


def run_demo_walkthrough(
    db: Session,
    *,
    script_path: Path | None = None,
) -> WalkthroughResult:
    load_providers_from_seed(db)
    session = create_session(db)
    script = load_demo_script(script_path)
    turns: list[AssistantTurn] = []

    for message in script["user_messages"]:
        turns.append(process_user_message(db, session.id, message))

    final_turn = turns[-1]
    matches = final_turn.matches or []
    return WalkthroughResult(
        session_id=session.id,
        final_state=final_turn.state,
        intake=final_turn.intake,
        matches=matches,
        care_recommendation=final_turn.care_recommendation,
        turns=turns,
    )
