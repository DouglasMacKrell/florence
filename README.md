# Florence

Florence is a humanistic elder-care navigation agent that guides families through intake, recommends care types, matches providers, and submits referrals.

Hackathon MVP for Arya Health.

## Status

- **Step Zero:** Security foundation — complete
- **Milestone 1:** Web app (text + browser voice) — not yet started
- **Milestone 2:** Twilio telephony — not yet started

## Documentation

- [Product handoff spec](docs/handoff.md)
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

## Testing (TDD required)

This project uses **test-driven development**. Write failing tests before implementation.

```bash
./scripts/run-tests.sh   # runs backend pytest and/or frontend vitest when configured
```

Pre-commit hooks run the test gate on every commit once test suites exist. See [AGENTS.md](AGENTS.md) and `.cursor/rules/test-driven-development.mdc`.

## Security

This is a **public** repository. See [SECURITY.md](SECURITY.md) for data-handling rules, pre-commit hooks, and vulnerability reporting.
