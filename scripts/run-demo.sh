#!/usr/bin/env bash
# Run the Florence Queens demo walkthrough in the terminal.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/backend"

if [[ ! -d .venv ]]; then
  echo "Backend venv not found. Run: cd backend && python3 -m venv .venv && pip install -e '.[dev]'"
  exit 1
fi

source .venv/bin/activate

if [[ -f ../.env ]]; then
  ln -sf ../.env .env 2>/dev/null || true
fi

export ENABLE_OLLAMA="${ENABLE_OLLAMA:-false}"
python -m app.demo.cli "$@"
