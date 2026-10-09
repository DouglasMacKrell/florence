# Florence — Public Demo Deployment Plan

**Status:** Phase 3 deployment configs added (`render.yaml`, `netlify.toml`, `docs/deploy-public-demo.md`). Live deploy requires Neon/Render/Netlify dashboard setup (see doc).

**Architecture policy:** Local-first **Ollama** remains Florence’s default documented development path. **Groq** is documented only as the **public portfolio demo deployment** inference configuration—not a replacement for local architecture.

---

## A. Current Architecture

Florence is a single-repo elder-care navigation MVP: React 19 + Vite 8, FastAPI, SQLAlchemy + Postgres, optional local Ollama, optional Twilio (Pipecat) for phone.

| Layer | Key files | Behavior |
|-------|-----------|----------|
| Frontend entry | [`frontend/index.html`](frontend/index.html) → [`frontend/src/main.tsx`](frontend/src/main.tsx) → [`frontend/src/App.tsx`](frontend/src/App.tsx) | Single-page chat, intake sidebar, Run Demo, voice/mic toggles |
| API client | [`frontend/src/api.ts`](frontend/src/api.ts) | `VITE_API_BASE_URL`; SSE `POST /sessions/{id}/messages/stream` |
| Browser voice | [`frontend/src/speech.ts`](frontend/src/speech.ts), [`frontend/src/mic.ts`](frontend/src/mic.ts) | `speechSynthesis` + `SpeechRecognition` only on web |
| Phone link | [`frontend/src/contact.ts`](frontend/src/contact.ts) | `VITE_CONTACT_PHONE`; not Twilio SDK |
| FastAPI | [`backend/app/main.py`](backend/app/main.py) | Sessions, demo, operator, twilio routers |
| Conversation | [`backend/app/services/conversation.py`](backend/app/services/conversation.py) | Persist turn → extract → state machine → optional match → reply |
| LLM (today) | [`backend/app/services/ollama.py`](backend/app/services/ollama.py) | Used by [`response_generation.py`](backend/app/services/response_generation.py) and [`intake_extraction.py`](backend/app/services/intake_extraction.py) |
| Safety | [`backend/app/agent/safety.py`](backend/app/agent/safety.py) | Phrase detection; emergency reply before LLM in response generation |
| Config | [`backend/app/config.py`](backend/app/config.py) | `ENABLE_OLLAMA`, telephony flags, CORS |
| Tests | [`backend/tests/`](backend/tests/) | 71 tests; API fixtures use SQLite + `ENABLE_OLLAMA=false` |

Referrals are **mock DB updates only** (`confirm_referral` → `mock_complete`). No SMS/email. Twilio returns 503 when not configured.

---

## B. Reusable Components (unchanged)

- State machine, care recommender, matching engine, prompts, safety detection, consent gating, reply sanitization.
- Session API + SSE contract.
- React chat, Run Demo script ([`data/demo_script.json`](data/demo_script.json)), mic/TTS.
- Twilio code (disabled via env in public demo).
- Local dev flow: Docker Postgres + Ollama on host.

---

## C. Required Changes (by phase)

### Phase 1 — Inference (approved to implement)

| File | Change |
|------|--------|
| **New** [`backend/app/services/llm_client.py`](backend/app/services/llm_client.py) | `LlmClient` protocol; `OllamaLlmClient` (wraps `OllamaClient`); `GroqLlmClient` (httpx → OpenAI-compatible `/chat/completions`); `get_llm_client()` |
| [`backend/app/config.py`](backend/app/config.py) | `inference_provider`, `groq_api_key`, `groq_base_url`, `groq_model`, `llm_max_retries` |
| [`.env.example`](.env.example) | Document `INFERENCE_PROVIDER`, Groq vars; keep Ollama local-first comments |
| [`backend/app/services/response_generation.py`](backend/app/services/response_generation.py) | Use `get_llm_client()` + `LlmError` instead of direct `OllamaClient` |
| [`backend/app/services/intake_extraction.py`](backend/app/services/intake_extraction.py) | Same for `extract_with_ollama` (LLM path unchanged in name for minimal churn) |
| **New** [`backend/tests/test_llm_client.py`](backend/tests/test_llm_client.py) | Groq chat, JSON, stream, retries; default Ollama provider |
| **New/extend** [`backend/tests/test_llm_inference_integration.py`](backend/tests/test_llm_inference_integration.py) | Emergency skips LLM; Groq failure → fallback; SSE with mocked Groq stream |

### Phase 2 — Public demo mode (after stop + approval)

| File | Change |
|------|--------|
| `config.py` | `public_demo_mode`, `demo_max_messages_per_session` |
| `frontend` | `VITE_PUBLIC_DEMO`: banner, hide tel CTA, hide operator panel, simulated referral copy |
| `conversation.py` / `sessions.py` | Enforce per-session message cap |
| `main.py` | Ensure telephony not enabled when `public_demo_mode` |

### Phase 3 — Deployment (after approval)

| Asset | Purpose |
|-------|---------|
| Netlify + `netlify.toml` | Static frontend build |
| Render web service | `uvicorn app.main:app` |
| Neon | `DATABASE_URL` |
| Env | `INFERENCE_PROVIDER=groq`, `GROQ_*`, `CORS_ORIGINS`, `VITE_API_BASE_URL` |

**Not in initial scope:** IP rate limits, TTL/cron, Redis, retention jobs, Groq SDK.

---

## D. Inference Provider Recommendation

- **Public demo:** Groq via `https://api.groq.com/openai/v1/chat/completions`.
- **Default model in `.env.example` only:** `llama-3.1-8b-instant` (override with `GROQ_MODEL`).
- **Local default:** `INFERENCE_PROVIDER=ollama` (unchanged Ollama URLs/models).
- **Master switch:** `ENABLE_OLLAMA=false` still disables all LLM assist (tests, scripted paths).
- **Order preserved:** Emergency check → `enable_ollama` gate → `is_available()` → LLM → sanitize/fallback.

---

## E. Hosting Recommendation

Netlify (frontend) + Render (backend) + Neon (Postgres) + Groq (inference). Browser Speech APIs for voice. No Ollama/Twilio/Piper/Whisper on public stack.

---

## F. Security and Safety (public demo)

- UI disclaimers (Phase 2): demonstration only, not medical advice, no real PHI, simulated referrals.
- Groq API key server-side only.
- Deterministic safety and emergency handling unchanged.
- Existing Postgres persistence for sessions (no new retention subsystem in v1).
- Per-session turn cap (Phase 2) only—no distributed rate limiting in v1.

---

## G. Implementation Phases

### Phase 1 — Inference abstraction + Groq (complete)

**Delivered:** [`backend/app/services/llm_client.py`](backend/app/services/llm_client.py); config + `.env.example`; wired reply + extraction; tests in `test_llm_client.py`, `test_llm_inference_integration.py`.

### Phase 2 — Public demo mode (complete)

**Delivered:** `PUBLIC_DEMO_MODE`, `DEMO_MAX_MESSAGES_PER_SESSION`, `demo_limits.py`, session API cap, `telephony_configured` override; frontend `VITE_PUBLIC_DEMO`, disclaimer, hidden phone/operator, simulated referral copy; tests in `test_public_demo_mode.py`.

**Do not proceed to Phase 3 without explicit approval.**

### Phase 3 — Deployment

Netlify / Render / Neon; manual acceptance checklist:

1. Demo disclaimer visible; no phone CTA; no operator economics panel.
2. Run Demo and free-form chat work; SSE streaming after cold start.
3. Emergency phrase returns deterministic emergency copy.
4. Referral flow labeled simulated; status `mock_complete`.
5. Voice/mic work where browser supports Web Speech.
6. No API keys in frontend bundle.
7. Local Ollama dev unchanged.

---

## H. Estimated Effort

**~2–3 days** across three phases (portfolio deployment, not a large infra project).

---

## I. Open Questions

None blocking Phase 1.

---

## Approved product decisions (summary)

1. Single repo. 2. Run Demo + free-form. 3. Hide phone CTA in demo mode. 4. Hide operator panel in demo mode. 5. Twilio in repo, off in demo. 6. Local Ollama default. 7. Public Groq. 8. Configurable Groq model (example: `llama-3.1-8b-instant`). 9. Groq for reply + extraction. 10. Deterministic safety order unchanged. 11. Neon for public DB. 12. Browser voice only.

---

## Phase 1 — Implementation reference (applied)

### Config additions (`backend/app/config.py`)

```python
inference_provider: str = "ollama"
groq_api_key: str = ""
groq_base_url: str = "https://api.groq.com/openai/v1"
groq_model: str = "llama-3.1-8b-instant"
llm_max_retries: int = 2  # shared retry budget for Groq; Ollama keeps ollama_max_retries
```

Environment names (Pydantic): `INFERENCE_PROVIDER`, `GROQ_API_KEY`, `GROQ_BASE_URL`, `GROQ_MODEL`, `LLM_MAX_RETRIES`.

### `get_llm_client()` behavior

- `inference_provider == "groq"` → `GroqLlmClient`
- else → `OllamaLlmClient` delegating to existing `OllamaClient`
- Optional injected client for tests

### Groq streaming → Florence SSE

Groq OpenAI SSE lines (`data: {...}` / `data: [DONE]`) map to token strings; `stream_assistant_reply` unchanged in contract (word-chunk fallback only when LLM disabled).

### `.env.example` addition (local-first preserved)

```bash
# Inference — local default: Ollama on localhost (see OLLAMA_* below)
INFERENCE_PROVIDER=ollama

# Public portfolio demo only (server-side; never in frontend)
# INFERENCE_PROVIDER=groq
# GROQ_API_KEY=
# GROQ_MODEL=llama-3.1-8b-instant
# GROQ_BASE_URL=https://api.groq.com/openai/v1
```

### Test matrix (Phase 1)

| Test | Assert |
|------|--------|
| `get_llm_client` default | Ollama adapter |
| Groq `chat` mocked | Parses `choices[0].message.content` |
| Groq `chat_json` | `response_format` json_object + repair retry |
| Groq `chat_stream` | Delta chunks yielded in order |
| Groq HTTP error | `LlmError`; reply path returns fallback |
| `generate_assistant_reply` emergency intake | `EMERGENCY_REPLY`; mock LLM not called |
| SSE endpoint with Groq mocked | `token` events + `done` (optional integration) |
