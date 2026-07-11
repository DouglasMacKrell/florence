#!/usr/bin/env bash
# Run test suites when present. Used by pre-commit and CI.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ran=0

if [[ -f backend/pyproject.toml ]]; then
  echo "==> backend: pytest"
  (cd backend && pytest -q)
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
