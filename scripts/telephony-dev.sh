#!/usr/bin/env bash
# Start backend with telephony enabled and print ngrok setup hints.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "Copy .env.example to .env and set Twilio + PUBLIC_* URLs first."
  exit 1
fi

if ! grep -q '^ENABLE_TELEPHONY=true' .env 2>/dev/null; then
  echo "Add ENABLE_TELEPHONY=true to .env"
fi

if ! grep -q '^PUBLIC_WEBSOCKET_URL=wss://' .env 2>/dev/null; then
  echo ""
  echo "Expose the backend with ngrok (or Cloudflare Tunnel), then set:"
  echo "  PUBLIC_BASE_URL=https://YOUR-TUNNEL.example"
  echo "  PUBLIC_WEBSOCKET_URL=wss://YOUR-TUNNEL.example/twilio/media"
  echo ""
  echo "Twilio phone number webhooks:"
  echo "  Voice URL:  https://YOUR-TUNNEL.example/twilio/voice"
  echo "  Status URL: https://YOUR-TUNNEL.example/twilio/status"
  echo ""
fi

echo "Install telephony deps once:"
echo "  cd backend && pip install -e '.[telephony]'"
echo ""
echo "Starting backend on port 8001..."
export ENABLE_TELEPHONY="${ENABLE_TELEPHONY:-true}"
cd backend
exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
