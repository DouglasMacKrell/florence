# Getting Started

> **New here?** Start with [quick-start.md](quick-start.md) — separate paths for **demo users** and **developers**.

Detailed setup reference below.

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Git | any recent | Clone and hooks |
| Docker | recent | Postgres 16 |
| Python | 3.12+ | FastAPI backend |
| Node.js | 18+ | React frontend |
| Ollama | recent | Local LLM (optional but recommended) |
| gitleaks, pre-commit, ruff | via Homebrew | Hooks and lint |

```bash
brew install gitleaks pre-commit ruff ollama
```

## 1. Clone and configure

```bash
git clone https://github.com/DouglasMacKrell/florence.git
cd florence
git checkout develop

cp .env.example .env
cp frontend/.env.example frontend/.env
```

Edit `.env` if needed. Defaults work for local Docker Postgres.

Edit `frontend/.env`:

```text
VITE_API_BASE_URL=http://127.0.0.1:8001
```

Use port **8001** if something else occupies 8000 (common on dev machines).

## 2. Install hooks

```bash
pre-commit install
pre-commit install --hook-type pre-push
```

## 3. Start Postgres

```bash
docker compose up -d
```

Verify:

```bash
docker compose ps
```

## 4. Ollama model (recommended)

```bash
ollama pull llama3.2:3b
ollama list   # should show llama3.2:3b
```

Set in `.env`:

```text
ENABLE_OLLAMA=true
OLLAMA_MODEL=llama3.2:3b
```

If Ollama is unavailable, Florence falls back to scripted prompts and rule-based extraction.

## 5. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Link env if running from backend/
ln -sf ../.env .env

uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

Health check:

```bash
curl http://127.0.0.1:8001/health
# {"status":"ok","service":"florence"}
```

## 6. Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Open **http://127.0.0.1:5173** (use `127.0.0.1`, not `localhost`, to match CORS settings).

## 7. First conversation

1. You should see Florence's greeting and an intake progress indicator.
2. Reply **Yes** to the storage consent prompt.
3. Describe a care situation (see [demo scenario in handoff.md](handoff.md#23-first-demo-scenario)).
4. Continue until provider cards appear.
5. Select a provider to record a mock referral.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| White screen in browser | Hard refresh (Cmd+Shift+R). Check browser console. |
| CORS errors | Use `127.0.0.1:5173` for UI; ensure `CORS_ORIGINS` in `.env` includes that origin. |
| Backend won't start (`psycopg2`) | Use `postgresql+psycopg://` URL or latest code — `database.py` auto-converts `postgresql://`. |
| Port 8000 in use | Run backend on 8001; update `frontend/.env`. |
| Slow first reply | Ollama cold start on first message; subsequent turns are faster. |
| No provider matches | Ensure budget/location/care type aren't over-constrained. |

## Run tests

```bash
./scripts/run-tests.sh
./scripts/pre-push-gate.sh
```

See [development.md](development.md) for workflow detail.
