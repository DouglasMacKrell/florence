# Quick Start

**Grand Prize** — [AI Healthcare Hack NYC](https://luma.com/arya-health-hack) · [Devpost](https://devpost.com/software/florence-2026)

Get Florence running locally in two paths depending on who you are.

| I want to… | Go to |
|------------|-------|
| **Try the web demo** (judge, PM, designer) | [User quick start ↓](#user-quick-start-5-minutes) |
| **Try the phone demo** (Twilio) | [Phone demo ↓](#phone-demo-optional) |
| **Develop or contribute** (engineer) | [Developer quick start ↓](#developer-quick-start-15-minutes) |

**URLs when running:** UI → http://127.0.0.1:5173 · API → http://127.0.0.1:8001

---

## User quick start (~5 minutes)

For anyone who wants to **use** Florence locally — no coding required.

### What you need installed

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (runs the database)
- [Ollama](https://ollama.com/) (optional — enables natural AI replies; app works without it)

### Steps

**1. Open a terminal in the project folder** (you already have the repo cloned).

**2. Run the startup helper:**

```bash
./scripts/dev-up.sh
```

This starts Postgres, checks Ollama, and prints what to run next.

**3. Start the backend** (terminal 1):

```bash
cd backend
source .venv/bin/activate   # first time: see Developer setup below to create it
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

**4. Start the frontend** (terminal 2):

```bash
cd frontend
npm install    # first time only
npm run dev -- --host 127.0.0.1 --port 5173
```

**5. Open the app:** http://127.0.0.1:5173

> Use `127.0.0.1`, not `localhost` — avoids CORS issues.

### First conversation (demo script)

**Fastest path:** click **Run demo** in the UI header — it replays the Queens daughter scenario automatically.

Or run the terminal walkthrough:

```bash
./scripts/run-demo.sh
```

Manual script:

1. Read Florence's greeting → reply **Yes** to storage consent.
2. Describe a care situation, for example:

   > My father is 82, lives in Queens 11101. He needs help with bathing and meals, has memory concerns, and recently fell. We need care within 30 days. Budget is about $6,000–$8,000 per month.

3. Answer follow-up questions (location, budget, timing).
4. When provider cards appear → click **Select provider**.
5. Confirm — you'll see a mock referral recorded.

**Voice:** Click **Voice input** (Chrome recommended) or **Listen** on replies.

**Operator view:** Use the header link to inspect lead score, transcript, and referral economics after a session.

### If something goes wrong

| Problem | Try this |
|---------|----------|
| White screen | Hard refresh: **Cmd+Shift+R** |
| "Failed to create session" | Backend not running — check terminal 1 |
| Slow first reply | Normal if Ollama is starting; wait ~10s |
| No provider cards | Include ZIP code + budget in your messages |

More help: [Troubleshooting](#troubleshooting) · [getting-started.md](getting-started.md)

---

## Phone demo (optional)

Call Florence on a Twilio number — same intake engine as the web app, with spoken prompts.

**Requires:** Twilio account, ngrok (or similar tunnel), telephony Python extras.

1. Follow [telephony.md](telephony.md) to configure `.env` and Twilio webhooks.
2. Run `./scripts/telephony-dev.sh` and start ngrok on port 8001.
3. Dial your Twilio number — the web header shows the configured number when telephony is enabled.

Phone calls use **scripted stage prompts** by default for reliable live demos. Web chat still uses Ollama for natural replies.

---

## Developer quick start (~15 minutes)

For engineers cloning the repo for the first time.

### Prerequisites

```bash
brew install git docker ollama pre-commit gitleaks ruff
```

Also need **Python 3.12+** and **Node.js 18+**.

### 1. Clone and configure

```bash
git clone https://github.com/DouglasMacKrell/florence.git
cd florence
git checkout develop

cp .env.example .env
cp frontend/.env.example frontend/.env
```

Default config works for local Docker Postgres. Frontend points at `http://127.0.0.1:8001`.

### 2. Git hooks (required before contributing)

```bash
pre-commit install
pre-commit install --hook-type pre-push
```

### 3. Ollama model

```bash
ollama pull llama3.2:3b
```

Verify: `ollama list` shows `llama3.2:3b`.

### 4. Infrastructure + backend

```bash
./scripts/dev-up.sh

cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
ln -sf ../.env .env

uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

Verify:

```bash
curl http://127.0.0.1:8001/health
# {"status":"ok","service":"florence"}
```

### 5. Frontend (new terminal)

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Open http://127.0.0.1:5173

### 6. Run tests

```bash
./scripts/run-tests.sh
./scripts/pre-push-gate.sh
```

### Daily workflow (already set up)

```bash
# Terminal 1
docker compose up -d
cd backend && source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

# Terminal 2
cd frontend && npm run dev -- --host 127.0.0.1 --port 5173
```

---

## Cheat sheet

```bash
# All services (after first-time setup)
docker compose up -d
cd backend && source .venv/bin/activate && uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
cd frontend && npm run dev -- --host 127.0.0.1 --port 5173

# Health checks
curl http://127.0.0.1:8001/health
curl -X POST http://127.0.0.1:8001/sessions

# Tests
./scripts/pre-push-gate.sh
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| White screen in browser | Cmd+Shift+R; check browser devtools console |
| CORS error in network tab | Open UI at `127.0.0.1:5173`, not `localhost:5173` |
| Port 8000 already in use | We use **8001** — ensure `frontend/.env` has `VITE_API_BASE_URL=http://127.0.0.1:8001` |
| `ModuleNotFoundError: psycopg2` | Pull latest code; `database.py` auto-converts to psycopg v3 |
| Postgres connection refused | `docker compose up -d` and wait for healthy status |
| Ollama errors / timeouts | Run `ollama serve`; or set `ENABLE_OLLAMA=false` in `.env` for scripted fallback |
| No provider matches | Include postal code, budget range, and care needs in conversation |

---

## Next steps

- [getting-started.md](getting-started.md) — detailed setup notes
- [telephony.md](telephony.md) — Twilio + ngrok phone demo
- [development.md](development.md) — TDD, branches, hooks
- [portfolio.md](portfolio.md) — demo narrative for presentations
- [api.md](api.md) — REST + Twilio API reference
