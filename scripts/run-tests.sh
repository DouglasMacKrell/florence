#!/usr/bin/env bash
# Run test suites when present. Used by pre-commit and CI.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ran=0

if [[ -f backend/pyproject.toml ]]; then
  echo "==> backend: pytest"
  PYTEST="pytest"
  if [[ -x "$ROOT/backend/.venv/bin/pytest" ]]; then
    PYTEST="$ROOT/backend/.venv/bin/pytest"
  fi
  # Default in-memory DB when unset so local .env Postgres is not required for the gate.
  (cd backend && DATABASE_URL="${DATABASE_URL:-sqlite+pysqlite:///:memory:}" "$PYTEST" -q)
  ran=1
fi

if [[ -f frontend/package.json ]] && node -e "
  const p = require('./frontend/package.json');
  process.exit(p.scripts && p.scripts.test ? 0 : 1);
" 2>/dev/null; then
  echo "==> frontend: npm test"
  (cd frontend && npm test -- --run)
  ran=1
fi

if [[ "$ran" -eq 0 ]]; then
  echo "No test suites configured yet — skipping."
fi
