import re

from app.models.intake import IntakeRecord
from app.services.intake_extraction_policy import format_phone_display

SUMMARY_CONFIRMATION_QUESTION = "Does that summary sound accurate?"


def _format_currency(amount: int) -> str:
    return f"${amount:,}"


def _format_urgency_phrase(urgency: str) -> str | None:
    normalized = urgency.replace("_", " ").strip()
    lowered = normalized.lower()
    if lowered in {"within 30 days", "within_30_days"}:
        return "within the next month"
    first = normalized.split(".")[0].strip()
    if not first:
        return None
    if first.lower().startswith("by "):
        return first[0].lower() + first[1:]
    if first.lower().startswith("within "):
        return first[0].lower() + first[1:]
    return first[0].lower() + first[1:] if first else None


def _care_recipient_label(intake: IntakeRecord) -> str | None:
    descriptor = intake.care_recipient.relationship_descriptor
    if descriptor:
        return descriptor.lower()
    name = intake.care_recipient.name
    if name:
        return name
    return None


def _opening_care_line(intake: IntakeRecord) -> str | None:
    age = intake.care_recipient.age
    label = _care_recipient_label(intake)
    postal = intake.location_preferences.postal_code

    if label and age is not None and postal:
        return f"You're looking for care for your {age}-year-old {label} near ZIP code {postal}."
    if label and age is not None:
        return f"You're looking for care for your {age}-year-old {label}."
    if age is not None and postal:
        return f"You're looking for care for someone who is {age} near ZIP code {postal}."
    if label and postal:
        return f"You're looking for care for your {label} near ZIP code {postal}."
    if postal:
        return f"You're looking for care near ZIP code {postal}."
    if label and age is not None:
        return f"You're looking for care for your {age}-year-old {label}."
    return None


def _subject_pronoun(intake: IntakeRecord) -> str:
    descriptor = (intake.care_recipient.relationship_descriptor or "").lower()
    if descriptor in {"mother", "wife", "grandmother"}:
        return "She"
    if descriptor in {"father", "husband", "grandfather"}:
        return "He"
    return "They"


def _sentence_case(fragment: str) -> str:
    if not fragment:
        return fragment
    return fragment[0].lower() + fragment[1:]


def _normalize_care_needs_clause(notes: str) -> str:
    """Map persisted care_needs.notes (raw user language) to text after the subject."""
    text = notes.strip().rstrip(".")
    if not text:
        return ""
    lowered = text.lower()

    if lowered.startswith("needs help with ") or lowered.startswith("needs help "):
        clause = _sentence_case(text)
    elif lowered.startswith("need help with "):
        clause = "needs help with " + text[len("need help with ") :]
    elif lowered.startswith("need help "):
        clause = "needs help " + text[len("need help ") :]
    elif lowered.startswith("help with "):
        clause = "needs " + lowered
    elif lowered.startswith("help "):
        clause = "needs help " + text[len("help ") :]
    else:
        clause = f"needs help with {_sentence_case(text)}"

    clause = re.sub(
        r"^needs help with help\b",
        "needs help",
        clause,
        count=1,
        flags=re.IGNORECASE,
    )
    clause = re.sub(
        r"^needs help with needs\b",
        "needs help",
        clause,
        count=1,
        flags=re.IGNORECASE,
    )
    return clause


def _format_care_needs_paragraph(intake: IntakeRecord) -> str | None:
    subject = _subject_pronoun(intake)
    notes = (intake.care_needs.notes or "").strip().rstrip(".")
    if notes:
        if re.match(r"^(she|he|they)\b", notes, re.IGNORECASE):
            text = notes[0].upper() + notes[1:]
            if not text.endswith("."):
                text += "."
            return text
        clause = _normalize_care_needs_clause(notes)
        if not clause:
            return None
        return f"{subject} {clause}."
    if intake.care_needs.requested_care_types:
        types = [value.replace("_", " ") for value in intake.care_needs.requested_care_types]
        return f"{subject} needs help with {', '.join(types)}."
    flags: list[str] = []
    adl = intake.care_needs.activities_of_daily_living
    for label, value in (
        ("bathing", adl.bathing),
        ("dressing", adl.dressing),
        ("meals", adl.eating),
        ("mobility", adl.mobility),
    ):
        if value is True:
            flags.append(label)
    if intake.care_needs.memory_concerns is True:
        flags.append("memory support")
    if flags:
        return f"{subject} needs help with {', '.join(flags)}."
    return None


def _needs_and_timing_paragraph(intake: IntakeRecord) -> str | None:
    care = _format_care_needs_paragraph(intake)
    urgency = intake.timing.urgency
    urgency_phrase = _format_urgency_phrase(urgency) if urgency else None

    if care and urgency_phrase:
        care_sentence = care.rstrip(".")
        return f"{care_sentence}, and you're hoping to arrange support {urgency_phrase}."
    if care:
        return care
    if urgency_phrase:
        return f"You're hoping to arrange support {urgency_phrase}."
    return None


def _budget_paragraph(intake: IntakeRecord) -> str | None:
    minimum = intake.financial.monthly_budget_min
    maximum = intake.financial.monthly_budget_max
    if minimum is not None and maximum is not None and minimum != maximum:
        return (
            f"Your budget is about {_format_currency(minimum)} to "
            f"{_format_currency(maximum)} per month."
        )
    if maximum is not None:
        return f"Your budget is around {_format_currency(maximum)} per month."
    if minimum is not None:
        return f"Your budget is at least {_format_currency(minimum)} per month."
    return None


def _contact_block(intake: IntakeRecord) -> str | None:
    name = intake.caller.name
    phone = intake.caller.phone
    if not name and not phone:
        return None
    lines = ["I have your contact information as:"]
    if name and phone:
        lines.append(f"{name} — {format_phone_display(phone)}")
    elif name:
        lines.append(name)
    elif phone:
        lines.append(format_phone_display(phone))
    return "\n".join(lines)


def _consent_paragraph(intake: IntakeRecord) -> str | None:
    if intake.consent.consent_to_contact is True:
        return (
            "You've also agreed that Florence may contact you with care-navigation updates "
            "and provider referrals."
        )
    return None


def build_intake_confirmation_message(intake: IntakeRecord) -> str:
    paragraphs: list[str] = ["Let me make sure I have this right."]

    opening = _opening_care_line(intake)
    if opening:
        paragraphs.append(opening)

    needs_timing = _needs_and_timing_paragraph(intake)
    if needs_timing:
        paragraphs.append(needs_timing)

    budget = _budget_paragraph(intake)
    if budget:
        paragraphs.append(budget)

    contact = _contact_block(intake)
    if contact:
        paragraphs.append(contact)

    consent = _consent_paragraph(intake)
    if consent:
        paragraphs.append(consent)

    if len(paragraphs) == 1:
        paragraphs.append("I captured the details you shared so far.")

    paragraphs.append(SUMMARY_CONFIRMATION_QUESTION)
    return "\n\n".join(paragraphs)
