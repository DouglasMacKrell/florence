# Deploy — Florence public portfolio demo

Architecture: **Netlify** (frontend) · **Render** (FastAPI) · **Neon** (Postgres) · **Groq** (`openai/gpt-oss-20b`).

Local development stays **Ollama-first**; this path is for the public demo only.

## Prerequisites

- GitHub repo connected to Render and Netlify
- Groq API key (server-side only on Render)
- Neon project with Postgres

## 1. Neon PostgreSQL

1. Open [https://console.neon.tech](https://console.neon.tech)
2. **New Project** (e.g. `florence-demo`)
3. Copy the **pooled** connection string (`postgresql://…?sslmode=require`)
4. In **Render** → your web service → **Environment** → set `DATABASE_URL` to that string (do not commit or paste into chat)

Florence uses existing `DATABASE_URL` + `init_db()` (`create_all` when `USE_ALEMBIC=false`).

## 2. Render backend

1. Open [https://dashboard.render.com](https://dashboard.render.com)
2. **New** → **Blueprint** → connect `DouglasMacKrell/florence` (branch `develop` or `main`)
3. Apply [`render.yaml`](../render.yaml) at repo root
4. Set secret/missing env vars in the service:
   - `DATABASE_URL` (Neon)
   - `GROQ_API_KEY` (Groq console)
   - `CORS_ORIGINS` — set **after** Netlify URL is known, e.g. `https://your-site.netlify.app` (exact origin, no wildcard)
5. Deploy; confirm **Logs** show startup and `GET /health` → 200

Public URL shape: `https://florence-api.onrender.com` (name may vary).

## 3. Netlify frontend

1. Open [https://app.netlify.com](https://app.netlify.com)
2. **Add new site** → **Import from Git** → same repo
3. Netlify reads [`netlify.toml`](../netlify.toml) (`base = frontend`, publish `dist`)
4. **Site configuration** → **Environment variables** (build time):
   - `VITE_PUBLIC_DEMO` = `true`
   - `VITE_API_BASE_URL` = your Render backend URL (HTTPS, no trailing slash)
5. **Deploy site**; note production URL (`https://….netlify.app`)

## 4. CORS (final)

1. Render → **Environment** → set `CORS_ORIGINS` to your **exact** Netlify production URL
2. **Manual Deploy** or wait for redeploy if env change triggers it
3. Hard-refresh Netlify site and confirm API calls succeed (no CORS errors in browser devtools)

## 5. Production smoke checklist

- Demo banner; no phone CTA; no operator panel
- Run Demo + free-form chat; SSE streaming
- Simulated referral copy
- Emergency phrase → deterministic emergency text
- Message cap (20 user turns) returns 429 when exceeded
- No secrets in Network tab or JS bundle

## 6. Regression (local)

```bash
cd backend && DATABASE_URL=sqlite+pysqlite:///:memory: .venv/bin/pytest -q
cd frontend && npm run lint && npm run build
```
