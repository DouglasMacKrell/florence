# Florence

Florence is a humanistic elder-care navigation agent that guides families through intake, recommends care types, matches providers, and submits referrals — by **web chat** or **phone**.

**Hackathon MVP for [Arya Health](docs/portfolio.md)** — Jul 2026.

## Status

| Milestone | Status |
|-----------|--------|
| Step Zero — security foundation | ✅ Complete |
| M1 — Web app (text + browser voice) + backend core | ✅ Demo-ready |
| M2 — Twilio telephony | 🟡 Functional locally ([setup](docs/telephony.md)) |

Full detail: [docs/roadmap.md](docs/roadmap.md)

## Documentation

**Start here:** [docs/README.md](docs/README.md)

| Doc | Description |
|-----|-------------|
| [Portfolio overview](docs/portfolio.md) | Problem, solution, demo story, architecture |
| [Quick start](docs/quick-start.md) | User + developer local run guide |
| [Telephony setup](docs/telephony.md) | Twilio + ngrok phone demo |
| [Architecture](docs/architecture.md) | System design and data flow |
| [API reference](docs/api.md) | REST + Twilio endpoints |
| [Roadmap](docs/roadmap.md) | What's done and what's next |
| [Product handoff (full spec)](docs/handoff.md) | Original requirements |
| [Security policy](SECURITY.md) | Data handling and hooks |

## Quick Start

| Audience | Guide |
|----------|-------|
| **Try the web demo** | [docs/quick-start.md](docs/quick-start.md#user-quick-start-5-minutes) |
| **Try the phone demo** | [docs/telephony.md](docs/telephony.md) |
| **Developers** | [docs/quick-start.md](docs/quick-start.md#developer-quick-start-15-minutes) |

```bash
./scripts/dev-up.sh          # Postgres + env checks
./scripts/run-demo.sh        # terminal demo walkthrough (optional)
# then start backend + frontend (see quick-start guide)
```

Open http://127.0.0.1:5173

## Stack

- **Frontend:** React 19, Vite, TypeScript, Web Speech API
- **Backend:** FastAPI, Pydantic v2, SQLAlchemy 2
- **Database:** Postgres 16 (Docker)
- **LLM:** Ollama (`llama3.2:3b`) — local only
- **Telephony:** Twilio, Pipecat, Whisper STT, Piper TTS
- **Testing:** 71 pytest tests, ruff, oxlint, gitleaks

## Git workflow

Work on **`develop`**, merge to **`main`** at stable milestones. No PRs.

```bash
git checkout develop
git push origin develop

# Stable milestone:
git checkout main && git merge develop && git push origin main && git checkout develop
```

See [docs/development.md](docs/development.md).

## Security

Public repository — no secrets or real PII in commits. User intake processed by **local Ollama only**.

See [SECURITY.md](SECURITY.md).
