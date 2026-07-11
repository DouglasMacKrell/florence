# Agent Instructions — Florence

Florence is an elder-care navigation MVP — web-first intake, care-type recommendation, provider matching, and referral flow.

## Before making changes

1. Read [docs/handoff.md](docs/handoff.md) for product requirements.
2. Read [docs/README.md](docs/README.md) for architecture, API, and roadmap.
3. Follow local rules in `.cursor/rules/` (gitignored — not in the public repo).
4. Read [SECURITY.md](SECURITY.md) for data-handling constraints.

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

## Architecture

- **Milestone 1 (current):** React web app (text + browser voice) + FastAPI + Postgres + Ollama — see [docs/architecture.md](docs/architecture.md)
- **Milestone 2:** Twilio telephony via Pipecat, reusing the same conversation engine — see [docs/roadmap.md](docs/roadmap.md)

## Security constraints

- Public repo — no secrets or real PII in commits
- Ollama local-only for user intake; no hosted LLM APIs with user data
- Synthetic data in seeds and tests
- Redact sensitive fields in logs when `REDACT_LOGS=true`
- `.cursor/` is local-only and must not be committed

## Key modules

| Module | Purpose | Location |
|--------|---------|----------|
| Intake state machine | Deterministic conversation stages | `backend/app/agent/state_machine.py` |
| Care-type recommender | Hospice / home care / nursing home guidance | `backend/app/agent/care_recommender.py` |
| Matching engine | Hard filters + weighted provider scoring | `backend/app/matching/engine.py` |
| Conversation service | Turn orchestration, Ollama, persistence | `backend/app/services/conversation.py` |
| Redaction utility | Log PII masking | `backend/app/security/redaction.py` |

See [docs/conversation-engine.md](docs/conversation-engine.md) and [docs/matching-and-referrals.md](docs/matching-and-referrals.md).

## Environment

Copy `.env.example` to `.env`. Never commit `.env`.
