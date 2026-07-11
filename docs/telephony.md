# Twilio telephony setup

Florence M2 lets callers dial a Twilio number and talk to the same intake engine as the web app. Audio stays local: Whisper for speech-to-text, Piper for text-to-speech, Ollama for replies when enabled.

## Prerequisites

- Twilio account with a voice-capable phone number
- [ngrok](https://ngrok.com/) or Cloudflare Tunnel (Twilio needs a public HTTPS/WSS URL)
- Ollama running locally (optional but recommended)
- Backend telephony extras installed:

```bash
cd backend
pip install -e '.[telephony]'
```

On Apple Silicon, the telephony extra includes MLX Whisper support required by Pipecat on macOS.

## Configure `.env`

```bash
ENABLE_TELEPHONY=true
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1...
PUBLIC_BASE_URL=https://YOUR-TUNNEL.ngrok-free.app
PUBLIC_WEBSOCKET_URL=wss://YOUR-TUNNEL.ngrok-free.app/twilio/media
```

`PUBLIC_BASE_URL` is used for Twilio signature validation. It must match the URL Twilio calls (your tunnel hostname, not `localhost`).

## Start the stack

```bash
./scripts/dev-up.sh          # Postgres + Ollama if needed
./scripts/telephony-dev.sh   # backend on :8001 with telephony hints
```

In another terminal, expose port 8001:

```bash
ngrok http 8001
```

Copy the ngrok HTTPS hostname into `PUBLIC_BASE_URL` and `PUBLIC_WEBSOCKET_URL`, then restart the backend.

## Twilio console

On your Twilio phone number:

| Setting | Value |
|---------|-------|
| **A call comes in** | Webhook `POST` → `https://YOUR-TUNNEL/twilio/voice` |
| **Call status changes** | Webhook `POST` → `https://YOUR-TUNNEL/twilio/status` |

## What happens on a call

1. Twilio hits `POST /twilio/voice` → Florence creates a session + call record and returns `<Connect><Stream>` TwiML.
2. Twilio opens `WS /twilio/media` → Pipecat pipeline starts.
3. Florence speaks the greeting (Piper TTS).
4. Caller speech → Whisper STT → `process_user_message()` → Piper speaks the reply.
5. Transcript and intake land in Postgres; operator view works the same as web sessions.
6. On hang-up, the call record is marked completed.

Phone calls use **scripted stage prompts** by default (`TELEPHONY_SCRIPTED_REPLIES=true`) for shorter, faster replies. Ollama phrasing is still used on the web UI. Set `TELEPHONY_SCRIPTED_REPLIES=false` in `.env` to experiment with Ollama on phone (slower, more verbose).

## Troubleshooting

| Symptom | Check |
|---------|-------|
| 503 on `/twilio/voice` | `ENABLE_TELEPHONY=true` and `PUBLIC_WEBSOCKET_URL` set |
| WebSocket closes immediately | `pip install -e '.[telephony]'` in backend venv |
| Invalid Twilio signature | `PUBLIC_BASE_URL` matches ngrok URL exactly |
| Slow first response | First Whisper/Piper model download; use smaller models in `.env` |
| No Ollama replies | `ENABLE_OLLAMA=true` and Ollama reachable; fallbacks still work |

## Architecture

Phone calls reuse `backend/app/services/conversation.py` — the Pipecat layer only handles audio transport. See [architecture.md](architecture.md).
