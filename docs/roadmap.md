# Roadmap & Status

Last updated: Jul 2026

## Hackathon outcome ✅

**Grand Prize** — [AI Healthcare Hack NYC](https://luma.com/arya-health-hack) by Arya Health & Twilio AI Startup Searchlight.

| | |
|---|---|
| **Devpost** | [florence-2026](https://devpost.com/software/florence-2026) |
| **Team** | Morrison Chang, Douglas MacKrell, Andrew Lai |
| **Prize** | $500 Twilio credit + Arya Health engineering interview |

Shipped in a one-day sprint: web intake, Twilio telephony, deterministic matching, operator dashboard, 71 tests.

## Milestone summary

| Phase | Scope | Status |
|-------|-------|--------|
| **Step Zero** | Security, hooks, gitignore, docs skeleton | ✅ Complete |
| **M1 — Web MVP** | React UI, FastAPI, Postgres, Ollama, matching, mock referral | ✅ Demo-ready |
| **M2 — Telephony** | Twilio + Pipecat, reuse conversation engine | ✅ Demo-ready locally |

## Step Zero ✅

- Public-repo security discipline (gitleaks, `.env.example`, redaction design)
- Pre-commit + pre-push quality gates
- `develop` / `main` branch workflow
- [SECURITY.md](../SECURITY.md)

## M1 — Web app ✅

### Done

- Docker Compose Postgres 16
- FastAPI backend with `/health` and session API
- Pydantic intake schema + completion tracking
- Conversation state machine (including contact-collection stage)
- Care-type recommender + deterministic matching engine
- 18-provider synthetic seed (`data/providers.json`)
- Ollama client + extraction + response generation (with fallbacks and retry)
- Safety phrase detection
- React chat UI (text + Web Speech voice hooks)
- SSE streaming for assistant replies
- Provider cards + mock referral confirmation
- Intake progress sidebar + operator dashboard
- Demo script automation (`Run demo` + `./scripts/run-demo.sh`)
- Alembic migrations (opt-in via `USE_ALEMBIC=true`)
- **71 backend tests**, frontend lint/build

## M2 — Telephony ✅

From [handoff.md Phase 3](handoff.md#phase-3-twilio-integration):

- [x] `POST /twilio/voice` webhook + TwiML media stream
- [x] `WS /twilio/media` Pipecat pipeline (VAD, Whisper STT, Piper TTS)
- [x] Link `call_sid` to session/intake records; caller ID pre-fills phone
- [x] Scripted stage prompts (`TELEPHONY_SCRIPTED_REPLIES=true`) for stable demos
- [x] Rules-only extraction on phone (no Ollama latency on live calls)
- [x] Turn locking, echo filtering, transcript filler suppression
- [x] Live demo at hackathon via ngrok + Twilio
- [ ] Production deploy with stable public URL (post-hackathon)
- [ ] Sign-off on graceful disconnect edge cases

**Design constraint:** Reuses `services/conversation.py` — intake logic is not forked for phone.

Setup: [telephony.md](telephony.md)

## Definition of done (hackathon)

| Criterion | Status |
|-----------|--------|
| User converses by text or voice in browser | ✅ |
| Intake accumulates in Postgres | ✅ |
| Care-type recommendation | ✅ |
| 1–3 provider cards with explanations | ✅ |
| User selects provider + mock referral | ✅ |
| Safety scenario routes correctly | ✅ |
| Callable Twilio number (live demo) | ✅ |
| Operator dashboard | ✅ |

**Result:** Grand Prize at AI Healthcare Hack NYC (Jul 2026).

## Promotion criteria (main branch)

Merge `develop` → `main` when:

- `./scripts/pre-push-gate.sh` passes
- Milestone is demo-stable
- Documentation reflects current behavior

## Related docs

- [Portfolio overview](portfolio.md)
- [Architecture](architecture.md)
- [Quick start](quick-start.md)
