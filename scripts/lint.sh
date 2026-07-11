#!/usr/bin/env bash
# Run linters when configured. Used by pre-push hooks.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ran=0

if [[ -f backend/pyproject.toml ]]; then
  echo "==> backend: ruff check"
  (cd backend && ruff check .)
  echo "==> backend: ruff format --check"
  (cd backend && ruff format --check .)
  ran=1
fi

if [[ -f frontend/package.json ]] && node -e "
  const p = require('./frontend/package.json');
  process.exit(p.scripts && p.scripts.lint ? 0 : 1);
" 2>/dev/null; then
  echo "==> frontend: npm run lint"
  (cd frontend && npm run lint)
  ran=1
fi

if [[ "$ran" -eq 0 ]]; then
  echo "No linters configured yet — skipping."
fi
