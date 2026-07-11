# Florence Documentation

Florence is a humanistic elder-care navigation agent — a hackathon MVP built for **Arya Health**. It guides families through structured intake, recommends care types, matches providers, and submits mock referrals.

This folder is the **portfolio and engineering reference** for the project.

## Start here

| Doc | Audience | Purpose |
|-----|----------|---------|
| [Portfolio overview](portfolio.md) | Judges, recruiters, collaborators | Problem, solution, demo story, tech highlights |
| [Quick start](quick-start.md) | Users & developers | Run locally in 5–15 minutes |
| [Getting started](getting-started.md) | Developers | Detailed install and troubleshooting |
| [Architecture](architecture.md) | Engineers | System design, repo layout, data flow |
| [Roadmap & status](roadmap.md) | Everyone | What's done, in progress, and planned |

## Product & domain

| Doc | Purpose |
|-----|---------|
| [Product handoff (full spec)](handoff.md) | Original product requirements, intake schema, conversation design |
| [Conversation engine](conversation-engine.md) | State machine, Ollama layer, extraction, safety |
| [Matching & referrals](matching-and-referrals.md) | Care-type recommender, provider scoring, referral flow |
| [Data models](data-models.md) | Intake schema, provider catalog, persistence |

## Engineering

| Doc | Purpose |
|-----|---------|
| [API reference](api.md) | REST endpoints for sessions and referrals |
| [Development guide](development.md) | TDD workflow, git branches, hooks, testing |
| [Security](../SECURITY.md) | Data handling, local-only LLM, secret scanning |

## Repository links

- **GitHub:** https://github.com/DouglasMacKrell/florence
- **Default branch:** `develop` (daily work); `main` (stable milestones)
- **Live stack (local):** React UI → FastAPI → Postgres + Ollama

## Quick status (Jul 2026)

| Milestone | Status |
|-----------|--------|
| Step Zero — security foundation | Complete |
| M1 — Web app + backend core | Functional (demo-ready with caveats) |
| M2 — Twilio telephony | Not started |

See [roadmap.md](roadmap.md) for detail.
