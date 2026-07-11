#!/usr/bin/env bash
# Full quality gate before push — tests, lint, secrets scan.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Florence pre-push quality gate"
"$ROOT/scripts/run-tests.sh"
"$ROOT/scripts/lint.sh"

if command -v gitleaks >/dev/null 2>&1; then
  echo "==> gitleaks (full repo scan)"
  gitleaks detect --source "$ROOT" --config "$ROOT/.gitleaks.toml" --no-banner
else
  echo "WARNING: gitleaks not installed — skipping full scan"
fi
