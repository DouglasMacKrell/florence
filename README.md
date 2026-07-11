# Elder Care Navigation Agent

Hackathon MVP: a humanistic elder-care navigation agent that guides families through intake, recommends care types, matches providers, and submits referrals.

## Status

- **Step Zero:** Security foundation (this repo)
- **Milestone 1:** Web app (text + browser voice) — not yet started
- **Milestone 2:** Twilio telephony — not yet started

## Documentation

- [Product handoff spec](elder-care-voice-agent-cursor-handoff.md)
- [Security policy](SECURITY.md)
- [Agent instructions](AGENTS.md)

## Developer setup

### Prerequisites

- Git
- [gitleaks](https://github.com/gitleaks/gitleaks) and [pre-commit](https://pre-commit.com/)

  ```bash
  brew install gitleaks pre-commit
  ```

### First-time setup

```bash
# Install git hooks (required before committing)
pre-commit install

# Verify hooks pass
pre-commit run --all-files

# Environment (when app code is added)
cp .env.example .env
# Edit .env with local values — never commit .env
```

## Security

This is a **public** repository. See [SECURITY.md](SECURITY.md) for data-handling rules, pre-commit hooks, and vulnerability reporting.
