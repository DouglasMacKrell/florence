# Agent Instructions — Florence

Florence is an elder-care navigation MVP — web-first intake, care-type recommendation, provider matching, and referral flow.

## Before making changes

1. Read [docs/handoff.md](docs/handoff.md) for product requirements.
2. Follow local rules in `.cursor/rules/` (gitignored — not in the public repo).
3. Read [SECURITY.md](SECURITY.md) for data-handling constraints.

## Git workflow (no PRs)

| Branch | Use |
|--------|-----|
| **`develop`** | Daily work — commit and push frequently |
| **`main`** | Stable, demo-ready milestones only |

- Commit small, frequent changes to **`develop`**.
- Merge `develop` → `main` only when a step is stable and hooks pass.
- Pre-push runs tests, linters, and gitleaks — fix before pushing.

```bash
git checkout develop
# ... work ...
git add -A && git commit -m "feat: ..."
git push origin develop

# Stable milestone only:
git checkout main && git merge develop && git push origin main && git checkout develop
```

## Test-driven development (required)

Every feature follows **Red → Green → Refactor**:

1. Write a failing test first.
2. Implement the minimum code to pass.
3. Refactor with tests still green.

```bash
./scripts/run-tests.sh
./scripts/lint.sh
./scripts/pre-push-gate.sh   # full gate before push
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
- `.cursor/` is local-only and must not be committed

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
