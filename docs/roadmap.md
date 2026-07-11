# Roadmap & Status

Last updated: Jul 2026 (Arya Health hackathon)

## Milestone summary

| Phase | Scope | Status |
|-------|-------|--------|
| **Step Zero** | Security, hooks, gitignore, docs skeleton | ✅ Complete |
| **M1 — Web MVP** | React UI, FastAPI, Postgres, Ollama, matching, mock referral | 🟡 Functional, polish remaining |
| **M2 — Telephony** | Twilio + Pipecat, reuse conversation engine | 🟡 Scaffold in progress |

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
- [x] SSE streaming for assistant replies
- [x] Quick-start docs + `dev-up.sh` bootstrap script

### Remaining / polish

- [ ] Richer Ollama extraction (smaller model tuning, retry logic)
- [x] Intake progress sidebar (checklist + completion %)
- [x] Operator dashboard (lead score, referral economics, transcript view)
- [x] Demo script automation / seeded walkthrough
- [ ] Alembic migrations (currently `create_all` on startup)

## M2 — Telephony 🟡

From [handoff.md Phase 3](handoff.md#phase-3-twilio-integration):

- [x] `POST /twilio/voice` webhook
- [x] `WS /twilio/media` bidirectional stream
- [x] Pipecat pipeline (VAD, local Whisper STT, Piper TTS)
- [x] Link `call_sid` to existing session/intake records
- [ ] End-to-end demo on a live Twilio number (requires tunnel + credentials)
- [ ] Graceful disconnect → partial intake saved (basic status callback wired)

**Design constraint:** Reuses `services/conversation.py` — intake logic is not forked for phone.

See [telephony.md](telephony.md).

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
| Callable Twilio number | 🟡 Scaffold ready |
| Operator dashboard | ✅ |

## Promotion criteria (main branch)

Merge `develop` → `main` when:

- `./scripts/pre-push-gate.sh` passes
- Milestone is demo-stable
- Documentation reflects current behavior

## Related docs

- [Portfolio overview](portfolio.md)
- [Architecture](architecture.md)
- [Getting started](getting-started.md)
