# Elder Care Voice Agent — Cursor Handoff

## 1. Project Summary

Build a humanistic, phone-based voice agent that acts as a first point of contact for families and individuals seeking elder care.

The agent should gently guide callers through a structured onboarding conversation, collect the information required to understand their care needs, and produce a ranked list of matching elder-care providers.

The long-term business goal is to convert qualified care seekers into successful provider referrals and capture the associated referral bounty, potentially worth up to $20,000 per completed placement.

This is not a medical diagnosis tool. It is a care-navigation, intake, qualification, and matching system.

---

## 2. Product Vision

Finding elder care is emotionally difficult, operationally complex, and often urgent. Families may not know:

- What kind of care is appropriate
- What care terminology means
- What questions to ask
- What services cost
- Whether insurance or public benefits may apply
- Which providers are available nearby
- Whether a provider can handle a specific condition or level of care
- What the next step should be

The product should make this process feel more understandable and humane.

The voice agent should behave like a calm, empathetic care coordinator who:

1. Listens without rushing
2. Explains unfamiliar terms in plain language
3. Collects care, location, timing, financial, and preference requirements
4. Identifies urgent or high-risk situations
5. Confirms the caller’s answers
6. Scores available providers
7. Recommends the strongest matches
8. Creates a qualified referral record
9. Hands off to a human when appropriate

---

## 3. Primary User

The initial user is a care seeker, usually:

- An adult child seeking care for a parent
- A spouse seeking help for a partner
- A relative or family friend assisting an older adult
- An older adult seeking care for themselves

The caller may be stressed, unfamiliar with elder-care terminology, or unsure what level of care is needed.

The system must not assume that the caller is the person receiving care.

---

## 4. Initial Use Case

The MVP should focus on inbound telephone calls.

Example:

> A daughter calls because her father can no longer safely live alone. She is unsure whether he needs home care, assisted living, memory care, or skilled nursing. The agent asks gentle questions, clarifies needs, captures budget and geography, and produces a ranked shortlist of providers.

The first version should support care navigation and lead qualification, not fully autonomous placement.

---

## 5. Core Product Principles

### Humanistic

The agent should sound patient, warm, respectful, and emotionally aware.

It should acknowledge the difficulty of the situation without becoming overly sentimental.

Example:

> “I’m sorry your family is having to navigate this. I’ll take this one step at a time with you.”

### Structured

The conversation should feel natural, but the underlying workflow must be deterministic.

The LLM should not freely decide what information is important. The application should maintain a required intake schema and track which fields are complete.

### Transparent

The agent should explain:

- Why it is asking sensitive questions
- That it is not a medical professional
- That recommendations are based on the information provided
- Whether providers may compensate the service for referrals

### Safe

The system must not diagnose, prescribe treatment, recommend medication changes, or falsely represent itself as a clinician or licensed care manager.

### Actionable

Every completed call should end with a clear next step:

- Provider shortlist
- Human follow-up
- Scheduled consultation
- Additional information request
- Emergency or professional-care guidance

---

## 6. MVP Scope

### Included

- Inbound phone calls through Twilio
- Bidirectional audio streaming
- Local speech-to-text
- Local LLM inference
- Local text-to-speech
- Structured elder-care intake
- Basic provider database
- Rule-based and weighted provider matching
- Ranked provider results
- Call transcript
- Structured lead record
- Human handoff flag
- Simple internal results page or JSON endpoint

### Excluded from MVP

- Medical diagnosis
- Medication guidance
- Insurance eligibility determinations
- Real-time provider inventory guarantees
- Automated contract signing
- Payments
- Fully automated outbound calling
- Production HIPAA claims
- Live CRM integrations
- Live provider marketplace integrations
- Automated booking without human review

---

## 7. Recommended Technical Architecture

```text
Caller
  |
  v
Twilio Phone Number
  |
  v
Twilio Bidirectional Media Stream
  |
  v
Public WebSocket Tunnel
  |
  v
Pipecat Orchestration Layer
  |
  +--> Voice Activity Detection
  |
  +--> Local Speech-to-Text
  |
  +--> Conversation State Machine
  |
  +--> Local Ollama LLM
  |
  +--> Intake Extraction and Validation
  |
  +--> Provider Matching Engine
  |
  +--> Local Text-to-Speech
  |
  v
Twilio Audio Response
```

### Suggested Components

| Layer | Suggested Tool |
|---|---|
| Telephony | Twilio Voice |
| Audio streaming | Twilio Media Streams |
| Orchestration | Pipecat |
| Voice activity detection | Silero VAD |
| Speech-to-text | MLX Whisper or faster-whisper |
| LLM | Ollama |
| Text-to-speech | Kokoro or Piper |
| API server | FastAPI |
| Database | SQLite for MVP |
| Data models | Pydantic |
| ORM | SQLAlchemy |
| Public tunnel | Cloudflare Tunnel or ngrok |
| Internal UI | Simple React page or FastAPI templates |

For a hackathon, optimize for reliability and demonstrability rather than production scalability.

---

## 8. Suggested Repository Structure

```text
elder-care-agent/
├── README.md
├── .env.example
├── pyproject.toml
├── requirements.txt
├── app/
│   ├── main.py
│   ├── config.py
│   ├── api/
│   │   ├── twilio.py
│   │   ├── calls.py
│   │   ├── leads.py
│   │   └── providers.py
│   ├── voice/
│   │   ├── pipeline.py
│   │   ├── transport.py
│   │   ├── stt.py
│   │   ├── tts.py
│   │   └── vad.py
│   ├── agent/
│   │   ├── system_prompt.py
│   │   ├── state_machine.py
│   │   ├── conversation.py
│   │   ├── extraction.py
│   │   ├── validation.py
│   │   └── safety.py
│   ├── matching/
│   │   ├── engine.py
│   │   ├── scoring.py
│   │   ├── filters.py
│   │   └── explanations.py
│   ├── models/
│   │   ├── call.py
│   │   ├── intake.py
│   │   ├── lead.py
│   │   ├── provider.py
│   │   └── match.py
│   ├── services/
│   │   ├── provider_service.py
│   │   ├── lead_service.py
│   │   ├── transcript_service.py
│   │   └── handoff_service.py
│   ├── db/
│   │   ├── database.py
│   │   ├── seed.py
│   │   └── migrations/
│   └── web/
│       ├── templates/
│       └── static/
├── data/
│   ├── providers.json
│   ├── sample_calls/
│   └── synthetic_leads/
├── scripts/
│   ├── seed_database.py
│   ├── run_local.py
│   └── test_call_flow.py
└── tests/
    ├── test_intake.py
    ├── test_matching.py
    ├── test_safety.py
    └── test_state_machine.py
```

---

## 9. Intake Data Model

The intake should be stored as structured data throughout the conversation.

```json
{
  "caller": {
    "name": null,
    "phone": null,
    "email": null,
    "relationship_to_care_recipient": null,
    "preferred_contact_method": null
  },
  "care_recipient": {
    "name": null,
    "age": null,
    "current_location": {
      "city": null,
      "state": null,
      "postal_code": null
    },
    "living_situation": null,
    "is_participating_in_decision": null
  },
  "care_needs": {
    "requested_care_types": [],
    "activities_of_daily_living": {
      "bathing": null,
      "dressing": null,
      "toileting": null,
      "transferring": null,
      "eating": null,
      "mobility": null
    },
    "instrumental_needs": {
      "meal_preparation": null,
      "medication_reminders": null,
      "transportation": null,
      "housekeeping": null,
      "shopping": null
    },
    "memory_concerns": null,
    "wandering_risk": null,
    "fall_risk": null,
    "behavioral_support_needed": null,
    "overnight_support_needed": null,
    "medical_equipment": [],
    "conditions_relevant_to_care": [],
    "notes": null
  },
  "timing": {
    "urgency": null,
    "desired_start_date": null,
    "temporary_or_long_term": null
  },
  "location_preferences": {
    "preferred_city": null,
    "preferred_state": null,
    "postal_code": null,
    "maximum_distance_miles": null,
    "must_remain_near_family": null
  },
  "financial": {
    "monthly_budget_min": null,
    "monthly_budget_max": null,
    "payment_sources": [],
    "long_term_care_insurance": null,
    "medicaid": null,
    "medicare": null,
    "veterans_benefits": null,
    "home_sale_expected": null,
    "financial_notes": null
  },
  "preferences": {
    "private_room_required": null,
    "pet_friendly": null,
    "language_preferences": [],
    "cultural_preferences": [],
    "religious_preferences": [],
    "gender_preferences_for_caregiver": null,
    "transportation_available": null,
    "amenities": [],
    "deal_breakers": []
  },
  "decision_process": {
    "decision_makers": [],
    "other_family_involved": null,
    "has_toured_providers": null,
    "providers_already_considered": [],
    "main_obstacle": null
  },
  "consent": {
    "consent_to_store_information": null,
    "consent_to_contact": null,
    "consent_to_share_with_matched_providers": null,
    "referral_disclosure_acknowledged": null
  },
  "safety": {
    "immediate_danger": false,
    "possible_emergency": false,
    "abuse_or_neglect_concern": false,
    "unsafe_living_situation": false,
    "human_followup_required": false,
    "safety_notes": null
  }
}
```

Not every field must be collected on every call. The state machine should prioritize required fields and ask optional questions only when relevant.

---

## 10. Required MVP Intake Fields

A lead should not be considered qualified until the following are captured:

- Caller name
- Caller phone number
- Relationship to care recipient
- Care recipient age or approximate age
- Current or desired location
- General type or severity of care needed
- Timing or urgency
- Budget range or payment constraints
- Consent to follow up
- At least one clear next step

Recommended additional fields:

- Memory-care needs
- Mobility limitations
- Help with activities of daily living
- Overnight supervision needs
- Preferred distance from family
- Existing insurance or public-benefit information
- Primary decision-maker
- Biggest concern

---

## 11. Conversation State Machine

The conversation should follow explicit stages.

```text
GREETING
  |
  v
DISCLOSURE_AND_CONSENT
  |
  v
UNDERSTAND_REASON_FOR_CALL
  |
  v
IDENTIFY_CARE_RECIPIENT
  |
  v
ASSESS_CARE_NEEDS
  |
  v
ASSESS_URGENCY_AND_SAFETY
  |
  v
COLLECT_LOCATION_REQUIREMENTS
  |
  v
COLLECT_FINANCIAL_REQUIREMENTS
  |
  v
COLLECT_PREFERENCES
  |
  v
UNDERSTAND_DECISION_PROCESS
  |
  v
CONFIRM_SUMMARY
  |
  v
MATCH_PROVIDERS
  |
  v
EXPLAIN_RECOMMENDATIONS
  |
  v
CAPTURE_FOLLOWUP_CONSENT
  |
  v
END_OR_HUMAN_HANDOFF
```

Each state should define:

- Required fields
- Optional fields
- Completion condition
- Allowed transitions
- Safety checks
- Suggested agent wording
- Maximum number of retries
- Human-handoff conditions

The LLM should generate natural phrasing, but the application should control state transitions.

---

## 12. Example Conversation Style

### Opening

> “Thank you for calling. I’m here to help you make sense of elder-care options and understand what might fit your family’s needs. I know this process can feel overwhelming, so we can take it one step at a time.”

### Disclosure

> “Before we begin, I want to let you know that I’m an automated care-navigation assistant, not a doctor or licensed medical professional. I can help organize your needs and identify possible care providers. With your permission, I’ll save the information you share so a care specialist can follow up.”

### First Question

> “Could you tell me a little about what has been happening and what led you to look for care now?”

### Clarifying Care Needs

> “When you say your mother needs help during the day, what kinds of things have become difficult for her?”

### Budget

> “Care costs can vary a lot, and it is completely understandable if you are not sure what is realistic yet. Do you have a monthly range in mind, or would it be more helpful to talk through possible payment sources?”

### Confirmation

> “Let me make sure I have this right. Your father is 82, lives in Queens, and is having increasing trouble with bathing, meals, and remembering medication. You would prefer care within about ten miles, and your family is hoping to stay below approximately $7,000 per month. Is that accurate?”

### Closing

> “Based on what you shared, I found three providers that appear to fit your location, care, and budget needs. I can explain why each one may be a match, and with your permission, a care specialist can follow up with you.”

---

## 13. Agent System Prompt

Use the following as a starting point.

```text
You are a warm, patient elder-care navigation assistant.

Your job is to help callers describe their situation, understand their care requirements, and identify potentially suitable elder-care providers.

You are not a doctor, nurse, lawyer, financial adviser, social worker, or licensed care manager. Do not diagnose conditions, prescribe treatment, interpret medical tests, recommend medication changes, promise eligibility, or guarantee provider availability.

Speak in short, clear sentences suitable for a telephone conversation.

Ask one main question at a time.

Use compassionate acknowledgements when the caller expresses fear, guilt, grief, confusion, or frustration, but do not overstate emotion or claim personal experience.

Do not pressure the caller to choose a provider.

Explain unfamiliar elder-care terms in plain language.

Confirm important facts, especially names, locations, timing, budget, memory-care needs, mobility needs, and consent.

Never invent missing information. Mark uncertain information as unknown and ask for clarification when necessary.

Follow the application-provided conversation state and field requirements. Do not skip required stages.

If the caller describes immediate danger, severe breathing difficulty, chest pain, active self-harm, a serious fall with injury, a missing vulnerable adult, suspected abuse, or another possible emergency, stop the normal intake flow and follow the configured safety escalation.

When discussing provider matches, explain the concrete reasons for each match and identify any uncertainties.

Disclose that the service may receive compensation from providers for successful referrals before sharing caller information with a provider.

Respect the caller’s right to decline, pause, correct information, or request a human.
```

---

## 14. Provider Data Model

For the hackathon, use a curated synthetic or public-data-backed provider dataset.

```json
{
  "id": "provider_001",
  "name": "Harbor View Senior Living",
  "provider_type": "assisted_living",
  "address": {
    "street": "123 Example Street",
    "city": "Queens",
    "state": "NY",
    "postal_code": "11101",
    "latitude": 40.744,
    "longitude": -73.949
  },
  "service_area_miles": 15,
  "care_levels": [
    "assisted_living",
    "memory_care"
  ],
  "supports": {
    "bathing": true,
    "dressing": true,
    "toileting": true,
    "mobility": true,
    "medication_management": true,
    "memory_support": true,
    "two_person_transfer": false,
    "overnight_supervision": true
  },
  "pricing": {
    "monthly_min": 5500,
    "monthly_max": 9000,
    "entrance_fee": 0
  },
  "payment_options": [
    "private_pay",
    "long_term_care_insurance"
  ],
  "languages": [
    "English",
    "Spanish"
  ],
  "amenities": [
    "transportation",
    "private_rooms",
    "pet_friendly"
  ],
  "availability": {
    "status": "unknown",
    "last_verified_at": null
  },
  "referral": {
    "eligible": true,
    "estimated_bounty": 12000,
    "requirements": "Qualified move-in and attribution"
  },
  "quality": {
    "rating": 4.4,
    "review_count": 83,
    "license_status": "unverified_for_demo"
  },
  "notes": null
}
```

Do not represent synthetic, stale, or unverified provider data as live availability.

---

## 15. Matching Strategy

Use a two-stage matching system.

### Stage 1: Hard Filters

Exclude providers that fail essential requirements.

Examples:

- Outside the maximum geographic radius
- Does not provide the required care type
- Cannot support a non-negotiable care need
- Minimum price is above the caller’s hard maximum budget
- Does not accept the required payment source
- Violates a stated deal-breaker
- Not eligible for referral, if referral eligibility is required for the business flow

### Stage 2: Weighted Scoring

Score remaining providers from 0 to 100.

Suggested weights:

| Category | Weight |
|---|---:|
| Care capability fit | 35 |
| Budget fit | 20 |
| Location fit | 15 |
| Urgency or availability fit | 10 |
| Personal preferences | 10 |
| Quality signals | 5 |
| Referral viability | 5 |

Example:

```text
total_score =
    care_fit * 0.35
  + budget_fit * 0.20
  + location_fit * 0.15
  + availability_fit * 0.10
  + preference_fit * 0.10
  + quality_fit * 0.05
  + referral_fit * 0.05
```

Referral economics should not override safety, care suitability, or explicit caller requirements.

The system should never rank a worse clinical or practical fit above a stronger fit solely because the referral bounty is larger.

---

## 16. Match Explanation Model

Every recommendation should include an explanation.

```json
{
  "provider_id": "provider_001",
  "score": 88,
  "rank": 1,
  "strengths": [
    "Provides both assisted living and memory support",
    "Located 4.2 miles from the preferred ZIP code",
    "Estimated price overlaps the stated monthly budget",
    "Offers overnight supervision",
    "Supports Spanish-speaking families"
  ],
  "concerns": [
    "Current room availability has not been verified",
    "Two-person transfers are not supported"
  ],
  "disqualifiers": [],
  "referral_eligible": true,
  "estimated_referral_value": 12000
}
```

The caller-facing explanation should omit internal scoring mechanics and bounty amounts.

Internal staff may see referral economics, but the caller should receive a transparent compensation disclosure rather than sales-pressure language.

---

## 17. Lead Scoring

Separate provider-match scoring from lead-quality scoring.

Suggested lead score:

| Signal | Points |
|---|---:|
| Caller identity and contact captured | 10 |
| Care recipient identified | 10 |
| Specific care needs captured | 20 |
| Location captured | 10 |
| Budget or payment constraints captured | 15 |
| Timing captured | 10 |
| Decision-maker identified | 10 |
| Consent to follow up | 10 |
| Consent to share with providers | 5 |

Lead categories:

- 80–100: Highly qualified
- 60–79: Qualified
- 40–59: Needs follow-up
- Below 40: Incomplete or exploratory

Do not lower the quality of care recommendations based on lead score.

---

## 18. Safety and Escalation

The system must detect situations that require a different response.

### Possible Emergency

Examples:

- Chest pain
- Severe difficulty breathing
- Unresponsiveness
- Serious injury after a fall
- Active suicidal intent
- Missing vulnerable adult
- Immediate danger
- Fire or unsafe environment

Behavior:

1. Stop normal intake
2. State that the situation may require immediate help
3. Encourage contacting emergency services or an appropriate local emergency resource
4. Do not continue provider matching as though the situation were routine
5. Flag the call for immediate human review

### Abuse, Neglect, or Exploitation

Examples:

- Physical abuse
- Caregiver neglect
- Financial exploitation
- Unsafe confinement
- Withholding food or medication

Behavior:

1. Respond calmly
2. Avoid interrogating the caller
3. Do not accuse anyone
4. Flag for trained human review
5. Present the appropriate configured escalation language
6. Preserve only the minimum necessary information

### Non-Emergency Human Handoff

Trigger a human handoff when:

- The caller requests a person
- The caller is highly distressed
- The agent repeatedly fails to understand
- The care situation is unusually complex
- Legal, benefits, medical, or financial advice is requested
- Consent is unclear
- No reasonable provider matches exist
- The caller disputes the summary
- The agent detects contradictory critical information

---

## 19. Privacy and Consent

For the hackathon:

- Use synthetic patient and provider data
- Avoid collecting unnecessary medical details
- Do not claim HIPAA compliance
- Store transcripts locally
- Make transcript retention configurable
- Redact obvious sensitive fields from logs
- Do not send private data to hosted model APIs
- Require explicit consent before sharing a lead with a provider
- Include a clear referral-compensation disclosure
- Provide a way to delete a test lead

Suggested disclosure:

> “Our service may receive compensation from a care provider if you choose that provider. That does not change the information you can share or your ability to consider other options.”

This language should be reviewed before production use.

---

## 20. API Endpoints

Suggested FastAPI endpoints:

```text
POST   /twilio/voice
WS     /twilio/media
GET    /health

POST   /calls
GET    /calls/{call_id}
GET    /calls/{call_id}/transcript

POST   /intakes
GET    /intakes/{intake_id}
PATCH  /intakes/{intake_id}

GET    /providers
GET    /providers/{provider_id}
POST   /providers/search

POST   /matches
GET    /matches/{intake_id}

GET    /leads
GET    /leads/{lead_id}
POST   /leads/{lead_id}/handoff
POST   /leads/{lead_id}/share
DELETE /leads/{lead_id}
```

---

## 21. Database Tables

### calls

- id
- twilio_call_sid
- started_at
- ended_at
- caller_phone
- status
- transcript_path
- handoff_required
- safety_flag

### intakes

- id
- call_id
- structured_json
- completion_percent
- current_state
- created_at
- updated_at

### providers

- id
- name
- provider_type
- address_json
- capabilities_json
- pricing_json
- payment_options_json
- preferences_json
- referral_json
- quality_json
- updated_at

### matches

- id
- intake_id
- provider_id
- score
- rank
- explanation_json
- created_at

### leads

- id
- intake_id
- lead_score
- lead_status
- consent_to_contact
- consent_to_share
- assigned_to
- created_at
- updated_at

### audit_events

- id
- call_id
- event_type
- event_payload
- created_at

---

## 22. Implementation Phases

### Phase 1: Local Text Prototype

Goal: Prove the intake and matching logic without voice.

Build:

- Pydantic intake model
- Provider model
- Synthetic provider dataset
- State machine
- Text chat loop
- Field extraction
- Required-field tracker
- Matching engine
- Match explanations
- Unit tests

Success criteria:

- A complete synthetic intake produces a valid structured record
- Matching results are deterministic
- Disqualifying requirements work
- Missing fields are correctly identified
- Safety phrases trigger escalation

### Phase 2: Local Voice Prototype

Goal: Add microphone input and spoken output.

Build:

- Local STT
- Local TTS
- Pipecat pipeline
- Voice activity detection
- Interruptions
- Short conversational responses
- Transcript persistence

Success criteria:

- Agent can complete the full intake by voice
- Caller can interrupt
- Latency is acceptable for a demo
- Structured data matches the spoken conversation

### Phase 3: Twilio Integration

Goal: Make the agent callable by telephone.

Build:

- Twilio webhook
- Bidirectional Media Stream
- Public WebSocket tunnel
- Twilio serializer
- Call lifecycle records
- Graceful disconnect behavior

Success criteria:

- Caller dials a Twilio number
- Two-way audio works
- Completed calls create lead and match records
- Partial calls are saved safely

### Phase 4: Internal Demo Dashboard

Goal: Make the value visible to judges and operators.

Display:

- Caller summary
- Care-recipient summary
- Intake completion
- Safety flags
- Lead score
- Ranked providers
- Match reasoning
- Referral eligibility
- Estimated internal referral value
- Transcript
- Human follow-up action

### Phase 5: Demo Polish

Add:

- Better voice
- Faster model
- Scripted sample callers
- Seeded provider data
- Clear consent language
- Human handoff simulation
- One strong end-to-end demo scenario
- One edge-case scenario
- One safety-escalation scenario

---

## 23. First Demo Scenario

### Caller

Adult daughter seeking care for her 82-year-old father.

### Situation

- Lives alone in Queens
- Increasing memory problems
- Misses medication
- Recently fell without serious injury
- Needs help with bathing and meals
- Family wants him within ten miles
- Budget is $6,000–$8,000 per month
- Care is needed within 30 days
- Daughter is primary decision-maker
- Open to assisted living or memory care
- Prefers a private room
- Wants transportation available

### Expected Result

The agent:

1. Responds empathetically
2. Captures the structured needs
3. Clarifies that the fall is not an active emergency
4. Explains assisted living versus memory care
5. Confirms budget and location
6. Produces three ranked providers
7. Explains strengths and uncertainties
8. Captures permission for follow-up
9. Creates a highly qualified lead
10. Displays estimated internal referral value on the staff dashboard

---

## 24. Testing Strategy

### Unit Tests

- Intake field validation
- State transitions
- Hard provider filters
- Weighted scoring
- Distance calculations
- Budget overlap
- Lead scoring
- Safety phrase detection
- Consent requirements

### Conversation Tests

Use scripted transcripts:

- Straightforward assisted-living request
- Memory-care request
- Home-care request
- Caller with no known budget
- Caller unsure of care type
- Contradictory information
- Caller refuses consent
- No provider matches
- Emergency language
- Abuse or neglect concern
- Caller requests human

### Voice Tests

Measure:

- Time to first spoken response
- Turn latency
- STT accuracy
- Proper interruption handling
- Medication and place-name transcription
- Whether the agent asks more than one question at once
- Whether the agent repeats questions unnecessarily

---

## 25. Non-Functional Requirements

- Keep spoken responses brief
- Never block the audio loop with long database work
- Stream LLM and TTS output where possible
- Store structured state after each completed turn
- Make every call recoverable after disconnection
- Log state transitions
- Keep model and voice settings configurable
- Use environment variables for credentials
- Never commit Twilio secrets
- Keep provider scoring deterministic
- Make business-weight changes auditable
- Separate internal referral economics from caller-facing recommendations

---

## 26. Environment Variables

```text
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=
PUBLIC_BASE_URL=
PUBLIC_WEBSOCKET_URL=

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=

STT_MODEL=
TTS_MODEL=
TTS_VOICE=

DATABASE_URL=sqlite:///./elder_care.db
TRANSCRIPT_RETENTION_DAYS=7
ENABLE_AUDIO_RECORDING=false
ENABLE_REFERRAL_SCORING=true
```

Do not store credentials in source control.

---

## 27. Definition of Done for the Hackathon

The project is successful when a judge can:

1. Call a Twilio phone number
2. Speak naturally with the agent
3. Describe an elder-care situation
4. Hear empathetic, relevant follow-up questions
5. Complete a structured intake
6. Receive understandable provider recommendations
7. See a dashboard containing:
   - Structured care requirements
   - Lead qualification score
   - Ranked providers
   - Match explanations
   - Consent status
   - Referral eligibility
   - Estimated internal referral value
8. See the system correctly route a safety-sensitive scenario

---

## 28. Immediate Cursor Tasks

Start in this order.

### Task 1

Create the Python project skeleton, configuration system, FastAPI app, and health endpoint.

### Task 2

Implement the Pydantic models for:

- Caller
- Care recipient
- Care needs
- Timing
- Location preferences
- Financial requirements
- Personal preferences
- Consent
- Safety
- Provider
- Match result
- Lead

### Task 3

Create a synthetic provider dataset with 15–25 providers representing:

- Home care
- Assisted living
- Memory care
- Skilled nursing
- Respite care

Include differences in:

- Geography
- Price
- Care capability
- Language
- Amenities
- Payment options
- Referral eligibility

### Task 4

Implement hard filters and deterministic weighted provider scoring.

### Task 5

Implement the intake state machine and missing-field tracker.

### Task 6

Build a terminal-based text conversation simulator before integrating voice.

### Task 7

Add local Ollama extraction and response generation.

### Task 8

Add tests for intake, matching, consent, and safety.

### Task 9

Integrate Pipecat, local STT, and local TTS.

### Task 10

Integrate Twilio Media Streams and the public WebSocket endpoint.

### Task 11

Build a minimal internal dashboard for the completed lead and provider matches.

---

## 29. First Cursor Prompt

Paste this into Cursor after creating the repository:

```text
We are building a hackathon MVP for a humanistic elder-care voice agent.

Read the project handoff document in full before making changes.

Begin with Phase 1 only. Do not add Twilio or voice integration yet.

Create:

1. A FastAPI project structure
2. Pydantic v2 data models for the complete intake schema
3. A provider data model
4. A match-result data model
5. A lead data model
6. A SQLite database configuration using SQLAlchemy
7. A synthetic provider seed file
8. A deterministic provider matching engine with:
   - hard filters
   - weighted scoring
   - human-readable match explanations
9. An explicit intake state machine
10. Unit tests for matching and state transitions
11. A terminal-based scripted demo that walks through one complete intake and prints the top three provider matches

Constraints:

- Python 3.12
- Type hints everywhere
- Pydantic v2
- FastAPI
- SQLAlchemy 2
- pytest
- ruff
- No hosted APIs
- No medical diagnosis
- No hidden scoring logic
- Keep referral value separate from care-fit scoring
- Use synthetic data only
- Favor simple, readable modules over abstraction-heavy architecture

Before coding, produce a concise implementation plan and identify any assumptions.
```

---

## 30. Product Risks

### Trust Risk

A voice agent discussing elder care can feel manipulative if the referral business model is hidden.

Mitigation:

- Disclose referral compensation
- Explain recommendations
- Avoid urgency-based sales pressure
- Permit human review

### Safety Risk

The caller may describe a medical or personal emergency.

Mitigation:

- Safety classifier
- Explicit escalation states
- Human handoff
- No diagnosis or treatment advice

### Data Risk

Provider information may be stale or incomplete.

Mitigation:

- Show last-verification timestamps
- State availability as unverified
- Avoid guarantees
- Require human confirmation before placement

### Matching Bias

Higher referral values could distort recommendations.

Mitigation:

- Separate care-fit scoring from referral economics
- Apply referral value only after suitability
- Keep scoring auditable
- Display excluded-provider reasons internally

### Conversation Risk

The agent may sound repetitive, cold, or intrusive.

Mitigation:

- Ask one question at a time
- Explain why sensitive information is needed
- Use brief empathetic acknowledgements
- Allow callers to skip questions
- Confirm summaries rather than repeatedly re-asking

---

## 31. Future Expansion

After the MVP:

- CRM integration
- Provider inventory feeds
- Appointment scheduling
- Human care-adviser console
- SMS follow-up
- Email summaries
- Multilingual support
- Benefits-screening workflows
- Document collection
- Provider outreach automation
- Call-quality analytics
- Referral attribution
- Conversion funnel reporting
- Family collaboration portal
- Care-plan comparison tools
- Provider verification workflows
- Human review of high-value leads
- Fine-grained consent and retention controls

---

## 32. Final Product Positioning

This should be presented as:

> A compassionate elder-care navigation agent that turns a confusing and emotional first phone call into a structured care plan, a qualified referral, and a clear next step.

The strongest hackathon story is not simply that the system talks.

The strongest story is that it combines:

- Human-centered conversation
- Structured intake
- Local private inference
- Explainable matching
- Safety-aware escalation
- A clear referral business model
