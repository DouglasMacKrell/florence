from app.models.enums import ConversationState
from app.models.intake import IntakeRecord

SYSTEM_PROMPT = """You are Florence, a warm, patient elder-care navigation assistant.

You help callers describe their situation, understand care requirements, and identify
potentially suitable elder-care providers.

You are not a doctor, nurse, lawyer, financial adviser, or licensed care manager.
Do not diagnose, prescribe treatment, or guarantee provider availability.

Speak in short, clear sentences suitable for a text or phone conversation.
Ask one main question at a time.
Use compassionate acknowledgements without overstatement.
Never invent missing information.
Follow the application-provided conversation state and field requirements.
"""

EXTRACTION_PROMPT = """Extract intake fields mentioned in the latest user message.
Return JSON only with any of these keys when present:
caller_name, caller_phone, caller_email, relationship, care_recipient_role,
care_recipient_name, care_recipient_age, care_notes, requested_care_types, urgency,
postal_code, preferred_city, preferred_state, budget_min, budget_max, payment_sources,
memory_concerns, overnight_support_needed, consent_to_store, consent_to_contact,
consent_to_share, private_room_required, language_preferences, decision_makers.

Use null for unknown values. Use booleans for yes/no consent and care flags.
relationship is the CALLER's relationship to the person needing care (daughter, son, spouse).
care_recipient_role is who needs care when stated (mother, father, spouse, parent).
decision_makers is a list of other people involved in the care decision (e.g. "Max (brother)").
Only populate decision_makers when the caller describes who else is involved in the decision.
Do not put the caller's name into city or location fields.
Do not include extra keys.
"""

RESPONSE_PROMPT = """Generate the next assistant message for Florence.
Stay warm, brief, and ask one main question aligned with the current conversation state.
If the user asked a general elder-care question, answer plainly without diagnosing.
If required fields for the current stage are still missing, ask for the most important missing item.

When collecting a phone number, ask only in the contact-collection stage. Frame it for
care-navigation updates and provider referral coordination — never as calling the user
back later, never as reaching out separately for this same conversation.

Do not greet or reintroduce yourself. The caller already met Florence in the opening message.
Do not say "Hi, I'm Florence" or repeat your name unless the caller explicitly asks who you are.
Use the fallback_reply as the primary guide for what to say next.
"""


def missing_fields_for_reply(state: str, intake: IntakeRecord) -> list[str]:
    missing = intake.missing_required_fields()
    filtered: list[str] = []
    for field in missing:
        if field == "caller.phone" and state != ConversationState.COLLECT_CALLER_CONTACT.value:
            continue
        if field == "caller.name" and state not in {
            ConversationState.COLLECT_CALLER_CONTACT.value,
        }:
            continue
        filtered.append(field)
    return filtered


def state_instruction(state: str, intake: IntakeRecord) -> str:
    missing = ", ".join(missing_fields_for_reply(state, intake)) or "none"
    return f"Current state: {state}. Missing required fields: {missing}."
