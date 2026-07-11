# Development Guide

First-time local setup: [quick-start.md](quick-start.md#developer-quick-start-15-minutes).

## Branch workflow

No pull requests — work on **`develop`**, promote to **`main`** at stable milestones.

```bash
git checkout develop
# ... work, commit, push ...
git push origin develop

# Stable milestone only:
git checkout main && git merge develop && ./scripts/pre-push-gate.sh && git push origin main
git checkout develop
```

## Test-driven development (required)

Every feature: **Red → Green → Refactor**

1. Write a failing test
2. Implement minimum code to pass
3. Refactor with tests green

```bash
./scripts/run-tests.sh      # backend pytest (+ frontend when configured)
./scripts/lint.sh           # ruff + oxlint
./scripts/pre-push-gate.sh  # full gate before push
```

Bug fixes require a regression test first.

## Hooks

| Hook | Trigger | Checks |
|------|---------|--------|
| pre-commit | `git commit` | gitleaks (staged), whitespace, YAML, private keys |
| pre-push | `git push` | tests, lint, full-repo gitleaks |

Install once:

```bash
pre-commit install
pre-commit install --hook-type pre-push
```

## Backend

```bash
cd backend
source .venv/bin/activate
pytest -v                    # all tests
pytest tests/test_matching_engine.py -v   # single file
ruff check .
ruff format .
```

### Test notes

- Session API tests use in-memory SQLite with `ENABLE_OLLAMA=false`
- Ollama client tests mock `httpx` — no live model required in CI
- Provider tests read `data/providers.json` from repo root

## Frontend

```bash
cd frontend
npm run dev
npm run lint
npm run build
```

Use `import type` for TypeScript types — runtime imports of `export type` cause white-screen crashes under Vite.

## Environment

Copy `.env.example` → `.env` (never commit).

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Postgres connection (auto-converts to psycopg v3 driver) |
| `OLLAMA_BASE_URL` | Local Ollama server |
| `OLLAMA_MODEL` | Model tag (default `llama3.2:3b`) |
| `ENABLE_OLLAMA` | Toggle LLM layer |
| `REDACT_LOGS` | Mask PII in log output |
| `CORS_ORIGINS` | Allowed frontend origins |

Frontend: `frontend/.env` → `VITE_API_BASE_URL`

## Agent / Cursor instructions

See [AGENTS.md](../AGENTS.md). Local Cursor rules live in `.cursor/` (gitignored).

Before coding:

1. Read [handoff.md](handoff.md)
2. Read [SECURITY.md](../SECURITY.md)
3. Follow TDD

## Key modules (implemented)

| Module | Path |
|--------|------|
| State machine | `backend/app/agent/state_machine.py` |
| Care recommender | `backend/app/agent/care_recommender.py` |
| Matching engine | `backend/app/matching/engine.py` |
| Conversation orchestration | `backend/app/services/conversation.py` |
| Ollama client | `backend/app/services/ollama.py` |
| Redaction | `backend/app/security/redaction.py` |
| Session API | `backend/app/api/sessions.py` |

## Adding a feature (checklist)

1. Update or read relevant doc in `/docs`
2. Write failing test
3. Implement
4. Run `./scripts/pre-push-gate.sh`
5. Update [roadmap.md](roadmap.md) if milestone status changes
6. Commit to `develop`
