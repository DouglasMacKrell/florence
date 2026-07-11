# Florence

Florence is a humanistic elder-care navigation agent that guides families through intake, recommends care types, matches providers, and submits referrals.

**Hackathon MVP for [Arya Health](docs/portfolio.md)** — Jul 2026.

## Status

| Milestone | Status |
|-----------|--------|
| Step Zero — security foundation | Complete |
| M1 — Web app (text + browser voice) + backend core | Functional ([details](docs/roadmap.md)) |
| M2 — Twilio telephony | Not started |

## Documentation

**Start here:** [docs/README.md](docs/README.md)

| Doc | Description |
|-----|-------------|
| [Portfolio overview](docs/portfolio.md) | Problem, solution, demo story, tech highlights |
| [Getting started](docs/getting-started.md) | Install and run locally |
| [Quick start](docs/quick-start.md) | User + developer local run guide |
| [Architecture](docs/architecture.md) | System design and data flow |
| [API reference](docs/api.md) | REST endpoints |
| [Roadmap](docs/roadmap.md) | What's done and what's next |
| [Product handoff (full spec)](docs/handoff.md) | Original requirements |
| [Security policy](SECURITY.md) | Data handling and hooks |

## Quick Start

Run Florence locally:

| Audience | Guide |
|----------|-------|
| **Try the demo** | [docs/quick-start.md](docs/quick-start.md#user-quick-start-5-minutes) |
| **Developers** | [docs/quick-start.md](docs/quick-start.md#developer-quick-start-15-minutes) |

```bash
./scripts/dev-up.sh          # Postgres + env checks
./scripts/run-demo.sh        # terminal demo walkthrough (optional)
# then start backend + frontend (see quick-start guide)
```

Open http://127.0.0.1:5173

Full details: [docs/quick-start.md](docs/quick-start.md) · [docs/getting-started.md](docs/getting-started.md)

## Stack

- **Frontend:** React, Vite, TypeScript, Web Speech API
- **Backend:** FastAPI, Pydantic v2, SQLAlchemy 2
- **Database:** Postgres 16 (Docker)
- **LLM:** Ollama (`llama3.2:3b`) — local only
- **Testing:** pytest, ruff, oxlint, gitleaks

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
