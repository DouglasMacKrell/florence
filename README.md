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

## Git workflow

No PRs — work on **`develop`**, merge to **`main`** at stable milestones.

```bash
git checkout develop          # daily work branch
git push origin develop       # frequent pushes

# Stable step only:
git checkout main && git merge develop && git push origin main
```

## Developer setup

### Prerequisites

- Git
- [gitleaks](https://github.com/gitleaks/gitleaks), [pre-commit](https://pre-commit.com/), and [ruff](https://docs.astral.sh/ruff/) (for Python linting once backend exists)

  ```bash
  brew install gitleaks pre-commit ruff
  ```

### First-time setup

```bash
# Install commit + push hooks (required)
pre-commit install
pre-commit install --hook-type pre-push

# Verify hooks
pre-commit run --all-files
./scripts/pre-push-gate.sh

# Environment (when app code is added)
cp .env.example .env
# Edit .env with local values — never commit .env
```

### Hooks

| Hook | Runs | Checks |
|------|------|--------|
| **pre-commit** | Every commit | gitleaks (staged), whitespace, YAML, merge conflicts, private keys |
| **pre-push** | Every push | tests, ruff (backend), frontend lint, full-repo gitleaks |

## Testing (TDD required)

Write failing tests before implementation.

```bash
./scripts/run-tests.sh
./scripts/lint.sh
./scripts/pre-push-gate.sh
```

See [AGENTS.md](AGENTS.md) for full workflow. Cursor rules live locally in `.cursor/rules/` (gitignored).

## Security

This is a **public** repository. See [SECURITY.md](SECURITY.md) for data-handling rules, pre-commit hooks, and vulnerability reporting.
