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
| `missing_fields` | array | Required intake field keys still empty |
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

### `POST /sessions/{session_id}/messages/stream`

Same request body as `/messages`, but streams the assistant reply via **Server-Sent Events** (`text/event-stream`).

**Events**

| Event | Payload | Description |
|-------|---------|-------------|
| `token` | `{ "text": "..." }` | Incremental reply chunk |
| `done` | Same shape as `/messages` response | Final turn metadata after reply is saved |
| `error` | `{ "detail": "..." }` | Stream failed |

The frontend uses this endpoint by default for progressive reply rendering.

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

## Operator

### `GET /operator/sessions/{session_id}`

Internal operator view: lead score, transcript, match referral economics, and referral status.

| Field | Description |
|-------|-------------|
| `lead_score` | 0–100 lead quality score |
| `lead_category` | `highly_qualified`, `qualified`, `needs_follow_up`, or `incomplete_or_exploratory` |
| `lead_breakdown` | Points by signal (identity, care needs, budget, etc.) |
| `transcript` | Full message history |
| `matches[].estimated_referral_value` | Internal referral bounty (operator-only) |
| `referral.estimated_referral_value` | Bounty for selected provider, if any |

## Demo

### `GET /demo/script`

Returns the seeded Queens daughter walkthrough (`data/demo_script.json`) for UI replay.

Terminal walkthrough (no server required):

```bash
./scripts/run-demo.sh
```

## Not yet implemented

- Twilio webhooks (`POST /twilio/voice`, `WS /twilio/media`)

See [roadmap.md](roadmap.md).
