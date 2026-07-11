# Roadmap & Status

Last updated: Jul 2026 (Arya Health hackathon)

## Milestone summary

| Phase | Scope | Status |
|-------|-------|--------|
| **Step Zero** | Security, hooks, gitignore, docs skeleton | ✅ Complete |
| **M1 — Web MVP** | React UI, FastAPI, Postgres, Ollama, matching, mock referral | 🟡 Functional, polish remaining |
| **M2 — Telephony** | Twilio + Pipecat, reuse conversation engine | ⬜ Not started |

## Step Zero ✅

- Public-repo security discipline (gitleaks, `.env.example`, redaction design)
- Pre-commit + pre-push quality gates
- `develop` / `main` branch workflow
- [SECURITY.md](../SECURITY.md)

## M1 — Web app 🟡

### Done

- [x] Docker Compose Postgres 16
- [x] FastAPI backend with `/health` and session API
- [x] Pydantic intake schema + completion tracking
- [x] Conversation state machine
- [x] Care-type recommender
- [x] Deterministic matching engine (hard filters + weighted scoring)
- [x] 18-provider synthetic seed (`data/providers.json`)
- [x] Ollama client + extraction + response generation (with fallbacks)
- [x] Safety phrase detection
- [x] React chat UI (text + Web Speech voice hooks)
- [x] Provider cards + mock referral confirmation
- [x] 35 backend tests, frontend build/lint
- [x] First local run verified

### Remaining / polish

- [ ] SSE streaming for assistant replies
- [ ] Richer Ollama extraction (smaller model tuning, retry logic)
- [ ] Intake progress sidebar (partial — completion % only)
- [ ] Operator dashboard (lead score, referral economics, transcript view)
- [ ] Demo script automation / seeded walkthrough
- [ ] Alembic migrations (currently `create_all` on startup)
- [ ] README runbook consolidation (partially moved to docs/)

## M2 — Telephony ⬜

From [handoff.md Phase 3](handoff.md#phase-3-twilio-integration):

- [ ] `POST /twilio/voice` webhook
- [ ] `WS /twilio/media` bidirectional stream
- [ ] Pipecat pipeline (VAD, STT, TTS)
- [ ] Link `call_sid` to existing session/intake records
- [ ] Public WebSocket tunnel (ngrok / Cloudflare)
- [ ] Graceful disconnect → partial intake saved

**Design constraint:** Reuse `services/conversation.py` — do not fork intake logic for phone.

## Definition of done (hackathon)

From [handoff.md §27](handoff.md#27-definition-of-done-for-the-hackathon):

| Criterion | Status |
|-----------|--------|
| User converses by text or voice in browser | ✅ |
| Intake accumulates in Postgres | ✅ |
| Care-type recommendation | ✅ |
| 1–3 provider cards with explanations | ✅ |
| User selects provider + mock referral | ✅ |
| Safety scenario routes correctly | ✅ (phrase detection; UI surfacing basic) |
| Callable Twilio number | ⬜ M2 |
| Operator dashboard | ⬜ Partial |

## Promotion criteria (main branch)

Merge `develop` → `main` when:

- `./scripts/pre-push-gate.sh` passes
- Milestone is demo-stable
- Documentation reflects current behavior

## Related docs

- [Portfolio overview](portfolio.md)
- [Architecture](architecture.md)
- [Getting started](getting-started.md)
