# Agent Instructions

Elder-care navigation MVP — web-first intake, care-type recommendation, provider matching, and referral flow.

## Before making changes

1. Read [elder-care-voice-agent-cursor-handoff.md](elder-care-voice-agent-cursor-handoff.md) for product requirements.
2. Follow all rules in `.cursor/rules/`, especially `security-core.mdc`.
3. Read [SECURITY.md](SECURITY.md) for data-handling constraints.

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
