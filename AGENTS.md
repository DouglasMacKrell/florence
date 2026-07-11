# Agent Instructions — Florence

Florence is an elder-care navigation MVP — web-first intake, care-type recommendation, provider matching, and referral flow.

## Before making changes

1. Read [docs/handoff.md](docs/handoff.md) for product requirements.
2. Follow all rules in `.cursor/rules/`, especially `security-core.mdc` and `test-driven-development.mdc`.
3. Read [SECURITY.md](SECURITY.md) for data-handling constraints.

## Test-driven development (required)

Every feature follows **Red → Green → Refactor**:

1. Write a failing test first.
2. Implement the minimum code to pass.
3. Refactor with tests still green.

```bash
# Run all configured test suites (also runs on pre-commit)
./scripts/run-tests.sh

# Backend only (once scaffolded)
cd backend && pytest

# Frontend only (once scaffolded)
cd frontend && npm test
```

Do not implement production logic without a preceding failing test. Bug fixes require a regression test first.

## Architecture (planned)

- **Milestone 1:** React web app (text + browser voice) + FastAPI + Postgres + Ollama
- **Milestone 2:** Twilio telephony via Pipecat, reusing the same conversation engine

## Security constraints

- Public repo — no secrets or real PII in commits
- Ollama local-only for user intake; no hosted LLM APIs with user data
- Synthetic data in seeds and tests
- Redact sensitive fields in logs when `REDACT_LOGS=true`

## Key modules (to be built)

| Module | Purpose |
|--------|---------|
| Intake state machine | Deterministic conversation stages |
| Care-type recommender | Hospice / home care / nursing home guidance |
| Matching engine | Hard filters + weighted provider scoring |
| Tool layer | `search_providers`, `submit_referral` (mocked) |
| Redaction utility | `backend/app/security/redaction.py` |

## Environment

Copy `.env.example` to `.env`. Never commit `.env`.
