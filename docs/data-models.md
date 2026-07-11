# Data Models

Florence stores intake as structured JSON throughout the conversation. Full schema: [handoff.md §9](handoff.md#9-intake-data-model).

## Intake record (Pydantic)

Top-level object: `IntakeRecord` in `backend/app/models/intake.py`

| Section | Key fields |
|---------|------------|
| `caller` | name, phone, email, relationship |
| `care_recipient` | name, age, location, living_situation |
| `care_needs` | ADLs, memory concerns, requested care types, notes |
| `timing` | urgency, desired start date |
| `location_preferences` | city, state, postal_code, max distance |
| `financial` | budget min/max, payment sources |
| `preferences` | private room, language, amenities, deal_breakers |
| `consent` | store, contact, share with providers, disclosure |
| `safety` | emergency flags, human follow-up required |

### Completion tracking

```python
intake.missing_required_fields()  # list of dot-paths still needed
intake.completion_percent()       # 0–100 for UI progress bar
intake.is_qualified()             # True when all required fields captured
```

## Provider record

`ProviderRecord` in `backend/app/models/provider.py` — mirrors seed JSON:

- Identity: id, name, provider_type
- Location: address, service_area_miles
- Capabilities: supports (bathing, memory_support, etc.)
- Pricing: monthly_min, monthly_max
- Referral: eligible, estimated_bounty
- Quality: rating, review_count (synthetic)

## Match result

`MatchResult` in `backend/app/models/match.py`:

```json
{
  "provider_id": "provider_001",
  "score": 88.5,
  "rank": 1,
  "strengths": ["..."],
  "concerns": ["..."],
  "referral_eligible": true,
  "estimated_referral_value": 12000
}
```

## Database ORM

SQLAlchemy models in `backend/app/db/tables.py`:

| ORM class | Table |
|-----------|-------|
| `SessionRecord` | sessions |
| `MessageRecord` | messages |
| `IntakeRecordORM` | intakes |
| `ProviderRecordORM` | providers |
| `CareRecommendationRecordORM` | care_recommendations |
| `MatchRecordORM` | matches |
| `ReferralRecordORM` | referrals |

Intake JSON is stored in `intakes.structured_json` (JSON column).

## Enums

`backend/app/models/enums.py`:

- `ConversationState` — state machine stages
- `CareType` — hospice, home_care, assisted_living, etc.
- `ProviderType` — provider catalog types

## Redaction

When `REDACT_LOGS=true`, `backend/app/security/redaction.py` masks phone, email, name, and transcript content in logs.

Runtime intake in Postgres is **not** redacted — only log output.

## Synthetic data policy

- All providers in `data/providers.json` are fictional
- Tests use synthetic names and phone numbers
- Never commit real PII or `.env` files

See [SECURITY.md](../SECURITY.md).
