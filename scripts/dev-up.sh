#!/usr/bin/env bash
# Florence local dev bootstrap — Postgres, env files, prerequisite checks.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Florence dev-up"
echo ""

# Env files
if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi
if [[ ! -f frontend/.env ]]; then
  cp frontend/.env.example frontend/.env
  echo "Created frontend/.env from frontend/.env.example"
fi

# Backend venv hint
if [[ ! -d backend/.venv ]]; then
  echo ""
  echo "NOTE: Backend venv not found. First-time setup:"
  echo "  cd backend && python3 -m venv .venv && source .venv/bin/activate"
  echo "  pip install -e \".[dev]\" && ln -sf ../.env .env"
  echo ""
fi

# Docker / Postgres
if ! command -v docker >/dev/null 2>&1; then
  echo "WARNING: docker not found — install Docker Desktop"
else
  echo "==> Starting Postgres (docker compose up -d)"
  docker compose up -d
  echo "    Waiting for Postgres..."
  for _ in {1..30}; do
    if docker compose exec -T postgres pg_isready -U florence -d florence >/dev/null 2>&1; then
      echo "    Postgres is ready."
      break
    fi
    sleep 1
  done
fi

# Ollama
echo ""
if command -v ollama >/dev/null 2>&1; then
  if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
    if ollama list 2>/dev/null | grep -q "llama3.2:3b"; then
      echo "==> Ollama: running, llama3.2:3b installed"
    else
      echo "==> Ollama: running but llama3.2:3b not found"
      echo "    Run: ollama pull llama3.2:3b"
    fi
  else
    echo "==> Ollama: installed but not responding — run: ollama serve"
  fi
else
  echo "==> Ollama: not installed (optional — set ENABLE_OLLAMA=false for scripted mode)"
fi

echo ""
echo "==> Next: open TWO terminals"
echo ""
echo "  Terminal 1 — backend:"
echo "    cd backend && source .venv/bin/activate"
echo "    uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"
echo ""
echo "  Terminal 2 — frontend:"
echo "    cd frontend && npm install && npm run dev -- --host 127.0.0.1 --port 5173"
echo ""
echo "  Then open: http://127.0.0.1:5173"
echo ""
echo "  Docs: docs/quick-start.md"
