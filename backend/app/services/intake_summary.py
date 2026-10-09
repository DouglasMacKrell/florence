from app.models.intake import IntakeRecord

SUMMARY_CONFIRMATION_QUESTION = "Does that summary sound accurate?"


def _format_currency(amount: int) -> str:
    return f"${amount:,}"


def _format_urgency(urgency: str) -> str:
    normalized = urgency.replace("_", " ").strip()
    if normalized == "within 30 days":
        return "within about 30 days"
    return normalized


def _location_phrase(intake: IntakeRecord) -> str | None:
    postal = intake.location_preferences.postal_code
    city = intake.location_preferences.preferred_city
    state = intake.location_preferences.preferred_state
    if city and state:
        place = f"{city}, {state}"
    elif city:
        place = city
    elif state:
        place = state
    else:
        place = None
    if postal and place:
        return f"near {place} (ZIP {postal})"
    if postal:
        return f"near ZIP code {postal}"
    if place:
        return f"near {place}"
    return None


def _care_needs_phrase(intake: IntakeRecord) -> str | None:
    if intake.care_needs.notes:
        return intake.care_needs.notes.strip()
    if intake.care_needs.requested_care_types:
        types = [value.replace("_", " ") for value in intake.care_needs.requested_care_types]
        return ", ".join(types)
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
        return ", ".join(flags)
    return None


def _budget_phrase(intake: IntakeRecord) -> str | None:
    minimum = intake.financial.monthly_budget_min
    maximum = intake.financial.monthly_budget_max
    if minimum is not None and maximum is not None and minimum != maximum:
        return (
            f"a monthly budget of about {_format_currency(minimum)} to {_format_currency(maximum)}"
        )
    if maximum is not None:
        return f"a monthly budget around {_format_currency(maximum)}"
    if minimum is not None:
        return f"a monthly budget of at least {_format_currency(minimum)}"
    return None


def _care_recipient_phrase(intake: IntakeRecord) -> str | None:
    age = intake.care_recipient.age
    name = intake.care_recipient.name
    relationship = intake.caller.relationship_to_care_recipient
    if name and age is not None:
        return f"{name} is {age} years old"
    if name:
        return name
    if age is not None and relationship:
        return f"Your {relationship} is about {age} years old"
    if age is not None:
        return f"the care recipient is about {age} years old"
    return None


def build_intake_summary_sentences(intake: IntakeRecord) -> list[str]:
    sentences: list[str] = []

    recipient = _care_recipient_phrase(intake)
    location = _location_phrase(intake)
    if recipient and location:
        sentences.append(f"{recipient}, and care should be {location}.")
    elif recipient:
        sentences.append(f"{recipient}.")
    elif location:
        sentences.append(f"Care should be {location}.")

    care_needs = _care_needs_phrase(intake)
    if care_needs:
        sentences.append(f"Help is needed with {care_needs}.")

    urgency = intake.timing.urgency
    if urgency:
        sentences.append(f"You are hoping care can start {_format_urgency(urgency)}.")

    budget = _budget_phrase(intake)
    if budget:
        sentences.append(f"You mentioned {budget}.")

    if intake.caller.name:
        sentences.append(f"I have your name as {intake.caller.name}.")
    if intake.caller.phone:
        sentences.append(f"The best number to reach you is {intake.caller.phone}.")
    if intake.caller.relationship_to_care_recipient:
        sentences.append(
            "You described your relationship as "
            f"{intake.caller.relationship_to_care_recipient} of the person needing care."
        )

    if intake.consent.consent_to_contact is True:
        sentences.append("You agreed I may contact you for care-navigation updates and referrals.")

    return sentences


def build_intake_confirmation_message(intake: IntakeRecord) -> str:
    sentences = build_intake_summary_sentences(intake)
    if not sentences:
        summary_body = "I captured the details you shared so far."
    else:
        summary_body = " ".join(sentences)
    return (
        f"Let me make sure I have this right.\n\n{summary_body}\n\n{SUMMARY_CONFIRMATION_QUESTION}"
    )
