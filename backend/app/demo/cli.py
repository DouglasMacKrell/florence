from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.db.database import Base, init_db
from app.demo.walkthrough import load_demo_script, run_demo_walkthrough


def _build_session_factory():
    settings = get_settings()
    engine = create_engine(settings.database_url)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Florence Queens demo walkthrough.")
    parser.add_argument(
        "--script",
        type=Path,
        default=None,
        help="Path to demo_script.json (default: data/demo_script.json)",
    )
    args = parser.parse_args(argv)

    script = load_demo_script(args.script)
    print(f"==> Florence demo: {script['title']}")
    print(f"    {script['description']}")
    print()

    init_db()
    session_factory = _build_session_factory()
    db = session_factory()
    try:
        result = run_demo_walkthrough(db, script_path=args.script)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print(f"Session: {result.session_id}")
    print(f"Final state: {result.final_state}")
    print(f"Intake completion: {result.intake.completion_percent()}%")
    if result.care_recommendation:
        primary = result.care_recommendation["primary"].replace("_", " ")
        print(f"Care recommendation: {primary}")
        print(f"  {result.care_recommendation['rationale']}")
    print()
    print(f"Provider matches ({len(result.matches)}):")
    for match in result.matches:
        print(f"  #{match['rank']} {match['provider_id']} — score {match['score']}")
        for strength in match["strengths"][:2]:
            print(f"     + {strength}")
    print()
    print("Demo walkthrough complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
