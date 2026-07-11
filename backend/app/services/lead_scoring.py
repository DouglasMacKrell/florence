from dataclasses import dataclass

from app.models.intake import IntakeRecord


@dataclass(frozen=True)
class LeadScoreResult:
    score: int
    category: str
    breakdown: dict[str, int]


def _lead_category(score: int) -> str:
    if score >= 80:
        return "highly_qualified"
    if score >= 60:
        return "qualified"
    if score >= 40:
        return "needs_follow_up"
    return "incomplete_or_exploratory"


def compute_lead_score(intake: IntakeRecord) -> LeadScoreResult:
    breakdown: dict[str, int] = {}

    if intake.caller.name and intake.caller.phone:
        breakdown["identity_and_contact"] = 10

    if intake.care_recipient.age is not None:
        breakdown["care_recipient_identified"] = 10

    if intake._has_care_needs():
        breakdown["care_needs_captured"] = 20

    if intake._has_location():
        breakdown["location_captured"] = 10

    if intake._has_financial_constraints():
        breakdown["financial_captured"] = 15

    if intake.timing.urgency:
        breakdown["timing_captured"] = 10

    if intake.caller.relationship_to_care_recipient or intake.decision_process.decision_makers:
        breakdown["decision_maker_identified"] = 10

    if intake.consent.consent_to_contact is True:
        breakdown["consent_to_follow_up"] = 10

    if intake.consent.consent_to_share_with_matched_providers is True:
        breakdown["consent_to_share"] = 5

    score = sum(breakdown.values())
    return LeadScoreResult(score=score, category=_lead_category(score), breakdown=breakdown)
