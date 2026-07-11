# Florence Frontend

React + Vite + TypeScript chat UI for the Florence elder-care navigation agent.

## Documentation

Full project docs live in the repo root:

- [docs/README.md](../docs/README.md) — documentation index
- [docs/getting-started.md](../docs/getting-started.md) — run locally
- [docs/api.md](../docs/api.md) — backend API

## Local development

```bash
cp .env.example .env
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Set `VITE_API_BASE_URL` to your backend (default in `.env.example` uses port 8001 when 8000 is occupied).

## Features

- Text chat with Florence
- Web Speech API voice input and TTS listen button
- Live intake completion progress
- Care recommendation panel
- Provider match cards with select + mock referral

## Scripts

| Command | Purpose |
|---------|---------|
| `npm run dev` | Dev server |
| `npm run build` | Production build |
| `npm run lint` | oxlint |
