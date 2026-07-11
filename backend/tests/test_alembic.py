from pathlib import Path


def test_initial_alembic_migration_creates_core_tables() -> None:
    versions = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    migration_files = list(versions.glob("*.py"))
    assert migration_files
    contents = "\n".join(path.read_text() for path in migration_files)
    assert "op.create_table(" in contents
    assert '"sessions"' in contents or "'sessions'" in contents
    assert '"calls"' in contents or "'calls'" in contents
