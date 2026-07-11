from pathlib import Path

from alembic.config import Config

from alembic import command


def alembic_config() -> Config:
    backend_root = Path(__file__).resolve().parents[2]
    return Config(str(backend_root / "alembic.ini"))


def upgrade_database(revision: str = "head") -> None:
    command.upgrade(alembic_config(), revision)


def stamp_database(revision: str = "head") -> None:
    command.stamp(alembic_config(), revision)
