# Florence Documentation

Florence is a humanistic elder-care navigation agent — a hackathon MVP built for **Arya Health**. It guides families through structured intake, recommends care types, matches providers, and submits mock referrals — by **web chat** or **phone**.

This folder is the **portfolio and engineering reference** for the project.

## Start here

| Doc | Audience | Purpose |
|-----|----------|---------|
| [Portfolio overview](portfolio.md) | Judges, recruiters, collaborators | Problem, solution, demo story, architecture |
| [Quick start](quick-start.md) | Users & developers | Run locally in 5–15 minutes |
| [Roadmap & status](roadmap.md) | Everyone | What's done and what's next |
| [Architecture](architecture.md) | Engineers | System design, data flow, repo layout |

## Demo paths

| Path | Guide |
|------|-------|
| **Web** (text + browser voice) | [Quick start → User path](quick-start.md#user-quick-start-5-minutes) |
| **Phone** (Twilio) | [Telephony setup](telephony.md) |
| **Terminal replay** | `./scripts/run-demo.sh` |

**Local URLs:** UI → http://127.0.0.1:5173 · API → http://127.0.0.1:8001

## Product & domain

| Doc | Purpose |
|-----|---------|
| [Product handoff (full spec)](handoff.md) | Original requirements, intake schema, conversation design |
| [Conversation engine](conversation-engine.md) | State machine, web vs phone behavior, Ollama layer |
| [Matching & referrals](matching-and-referrals.md) | Care-type recommender, provider scoring, referral flow |
| [Data models](data-models.md) | Intake schema, provider catalog, persistence |

## Engineering

| Doc | Purpose |
|-----|---------|
| [API reference](api.md) | REST + Twilio endpoints |
| [Development guide](development.md) | TDD workflow, git branches, hooks, testing |
| [Getting started](getting-started.md) | Detailed install and troubleshooting |
| [Security](../SECURITY.md) | Data handling, local-only LLM, secret scanning |

## Quick status (Jul 2026)

| Milestone | Status |
|-----------|--------|
| Step Zero — security foundation | ✅ Complete |
| M1 — Web app + backend core | ✅ Demo-ready |
| M2 — Twilio telephony | 🟡 Functional locally (tunnel + Twilio creds) |

See [roadmap.md](roadmap.md) for detail.

## Repository

- **GitHub:** https://github.com/DouglasMacKrell/florence
- **Branches:** `develop` (daily work) · `main` (stable milestones)
