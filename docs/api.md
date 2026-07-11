# API Reference

Base URL (local): `http://127.0.0.1:8001`

Interactive docs: `http://127.0.0.1:8001/docs` (FastAPI Swagger UI)

## Health

### `GET /health`

```json
{ "status": "ok", "service": "florence" }
```

## Sessions

### `POST /sessions`

Start a new conversation. Seeds providers into Postgres if empty. Returns initial greeting.

**Response**

```json
{
  "session_id": "uuid",
  "state": "GREETING",
  "greeting": "Thank you for reaching out. I'm Florence..."
}
```

### `GET /sessions/{session_id}`

Full session snapshot for UI refresh.

**Response fields**

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | string | UUID |
| `state` | string | Current conversation state |
| `status` | string | `active` or `completed` |
| `intake` | object | Full structured intake JSON |
| `completion_percent` | int | 0–100 required-field completion |
| `messages` | array | `{ role, content, created_at }` |
| `matches` | array | Provider match explanations |
| `care_recommendation` | object? | Primary care type + rationale |
| `referral` | object? | `{ provider_id, status }` if selected |

### `POST /sessions/{session_id}/messages`

Send a user message; receive assistant reply and updated intake.

**Request**

```json
{ "content": "Yes, you may store my information." }
```

**Response**

```json
{
  "content": "Assistant reply text",
  "state": "UNDERSTAND_REASON_FOR_CALL",
  "intake": { "...": "..." },
  "matches": null,
  "care_recommendation": null
}
```

When intake is complete and state reaches matching, `matches` and `care_recommendation` may be populated.

### `POST /sessions/{session_id}/select-provider`

Record user's provider choice (status `pending`).

**Request**

```json
{ "provider_id": "provider_001" }
```

### `POST /sessions/{session_id}/confirm-referral`

Validate consent and mark referral `mock_complete`. Requires `consent.consent_to_contact === true` and a prior provider selection.

**Response**

```json
{
  "session_id": "uuid",
  "provider_id": "provider_001",
  "status": "mock_complete"
}
```

## Errors

| Code | Meaning |
|------|---------|
| 404 | Session not found |
| 400 | Referral validation failed (missing consent or provider) |

## CORS

Configured via `CORS_ORIGINS` in `.env`. Default includes both `localhost` and `127.0.0.1` on port 5173.

## Not yet implemented

- SSE streaming for assistant replies
- Twilio webhooks (`POST /twilio/voice`, `WS /twilio/media`)
- Operator dashboard endpoints

See [roadmap.md](roadmap.md).
