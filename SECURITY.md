# Security Policy

## Hackathon disclaimer

This project is a **hackathon MVP** for elder-care navigation. It is **not** production-ready and **does not** claim HIPAA compliance. Demo scenarios use **synthetic data only**.

## What we do not store in git

- Environment files with real credentials (`.env`)
- API keys, tokens, or private keys
- Real personal or health information (names, phones, emails, medical details)
- Conversation transcripts or intake records from live sessions

Intake and transcript data at runtime belongs in local Postgres only.

## Local-only inference

User conversations are processed by **Ollama running locally**. Intake data and transcripts must not be sent to hosted LLM APIs.

## Developer setup

1. Copy `.env.example` to `.env` and fill in local values.
2. Never commit `.env`.
3. Install pre-commit hooks before your first commit:

   ```bash
   brew install gitleaks pre-commit   # macOS
   pre-commit install
   pre-commit run --all-files
   ```

## Reporting a vulnerability

If you discover a security issue, please **open a [GitHub Security Advisory](https://github.com/security-advisories)** on this repository rather than filing a public issue with sensitive details.

Do not include real user data, credentials, or exploit details in public issues.
