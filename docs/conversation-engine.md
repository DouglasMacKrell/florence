# Conversation Engine

Florence separates **what to ask next** (deterministic) from **how to say it** (LLM-assisted).

## State machine

Stages follow the product spec in [handoff.md §11](handoff.md#11-conversation-state-machine):

```text
GREETING → DISCLOSURE_AND_CONSENT → UNDERSTAND_REASON_FOR_CALL
  → IDENTIFY_CARE_RECIPIENT → ASSESS_CARE_NEEDS → ASSESS_URGENCY_AND_SAFETY
  → COLLECT_LOCATION_REQUIREMENTS → COLLECT_FINANCIAL_REQUIREMENTS
  → COLLECT_PREFERENCES → UNDERSTAND_DECISION_PROCESS → CONFIRM_SUMMARY
  → MATCH_PROVIDERS → EXPLAIN_RECOMMENDATIONS → CAPTURE_FOLLOWUP_CONSENT
  → END_OR_HUMAN_HANDOFF
```

Implementation: `backend/app/agent/state_machine.py`

Each state advances when its **completion condition** is met (e.g. consent captured, age provided, budget entered). The LLM cannot skip states.

## Required fields for qualification

A lead is qualified when all required fields are captured. Tracked by `IntakeRecord.missing_required_fields()`:

- Caller name, phone, relationship
- Care recipient age
- Location (ZIP or city/state)
- Care needs (types, ADL flags, or notes)
- Timing / urgency
- Budget or payment constraints
- Consent to follow up

See [data-models.md](data-models.md).

## Ollama integration

| Component | File | Role |
|-----------|------|------|
| Client | `services/ollama.py` | HTTP chat + JSON mode against local Ollama |
| Prompts | `agent/prompts.py` | System, extraction, and response instructions |
| Extraction | `services/intake_extraction.py` | Merge Ollama JSON patch + rule fallback |
| Responses | `services/response_generation.py` | Natural replies with scripted fallback |

### Configuration

```text
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
ENABLE_OLLAMA=true
```

**No API keys** — Ollama runs as a local HTTP server.

### Extraction flow

1. Build prompt with current state, intake JSON, recent messages, latest user text.
2. Request JSON from Ollama (`format: json`).
3. Apply patch to `IntakeRecord` via `apply_extraction_patch()`.
4. Always run rule-based extraction as supplement/fallback.
5. Run safety phrase detection on user text.

### Response flow

1. If safety flag → return emergency escalation message (no matching).
2. If `ENABLE_OLLAMA=false` or Ollama unavailable → use scripted `STATE_PROMPTS`.
3. Otherwise → Ollama generates brief reply aligned to current state and missing fields.

## Safety

`backend/app/agent/safety.py` scans user messages for:

- **Emergency language** — chest pain, difficulty breathing, immediate danger
- **Abuse/neglect concerns** — exploitation, withholding care

When triggered:

- `intake.safety.human_followup_required = true`
- Normal provider matching is suppressed
- Assistant returns escalation guidance (not medical advice)

## Frontend voice (M1)

Browser **Web Speech API** handles STT/TTS client-side. Transcribed text is sent to the same REST endpoint as typed messages — no separate voice pipeline in M1.

## Module map

| File | Purpose |
|------|---------|
| `services/conversation.py` | Orchestrates turns, persistence, matching trigger |
| `agent/state_machine.py` | `advance_state()`, transition rules |
| `services/intake_extraction.py` | Field extraction |
| `services/response_generation.py` | Reply generation |
| `services/ollama.py` | Ollama HTTP client |

## Testing

- `tests/test_state_machine.py` — transitions and gating
- `tests/test_intake_extraction.py` — rule extraction
- `tests/test_ollama_client.py` — mocked HTTP client
- `tests/test_safety.py` — phrase detection
- `tests/test_sessions_api.py` — end-to-end session API (Ollama disabled)
