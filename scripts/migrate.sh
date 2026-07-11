#!/usr/bin/env bash
# Apply Alembic migrations against DATABASE_URL from .env
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/backend"

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

echo "==> alembic upgrade head"
.venv/bin/alembic upgrade head
