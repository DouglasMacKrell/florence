from dataclasses import dataclass

from app.models.enums import CareType
from app.models.intake import IntakeRecord


@dataclass(frozen=True)
class CareRecommendation:
    primary: str
    alternatives: list[str]
    rationale: str


def recommend_care_types(intake: IntakeRecord) -> CareRecommendation:
    needs = intake.care_needs
    adl = needs.activities_of_daily_living
    instrumental = needs.instrumental_needs

    hospice_signals = (
        "hospice" in needs.requested_care_types
        or "terminal_illness" in needs.conditions_relevant_to_care
        or (needs.notes and "comfort-focused" in needs.notes.lower())
    )
    if hospice_signals:
        return CareRecommendation(
            primary=CareType.HOSPICE,
            alternatives=[CareType.HOME_CARE],
            rationale="Comfort-focused support and hospice-level services appear to fit best.",
        )

    skilled_signals = (
        "skilled_nursing" in needs.requested_care_types
        or needs.behavioral_support_needed is True
        or len(needs.medical_equipment) >= 2
    )
    if skilled_signals:
        return CareRecommendation(
            primary=CareType.SKILLED_NURSING,
            alternatives=[CareType.ASSISTED_LIVING],
            rationale="Higher medical complexity suggests skilled nursing or similar 24/7 care.",
        )

    memory_signals = needs.memory_concerns is True or needs.wandering_risk is True
    cannot_live_alone = intake.care_recipient.living_situation == "cannot_live_alone_safely"
    if memory_signals and (cannot_live_alone or needs.overnight_support_needed):
        return CareRecommendation(
            primary=CareType.MEMORY_CARE,
            alternatives=[CareType.ASSISTED_LIVING, CareType.HOME_CARE],
            rationale="Memory support with supervision needs points toward memory care options.",
        )

    adl_help = any(
        value is True
        for value in (
            adl.bathing,
            adl.dressing,
            adl.toileting,
            adl.transferring,
            adl.eating,
            adl.mobility,
            instrumental.meal_preparation,
            instrumental.medication_reminders,
        )
    )
    prefers_home = (
        intake.care_recipient.living_situation
        in {
            "lives_alone",
            "lives_with_family",
            "own_home",
        }
        if intake.care_recipient.living_situation
        else True
    )

    if adl_help and prefers_home and not memory_signals:
        return CareRecommendation(
            primary=CareType.HOME_CARE,
            alternatives=[CareType.ASSISTED_LIVING],
            rationale=(
                "Day-to-day support at home may be enough before considering residential care."
            ),
        )

    if cannot_live_alone or needs.overnight_support_needed:
        return CareRecommendation(
            primary=CareType.ASSISTED_LIVING,
            alternatives=[CareType.MEMORY_CARE, CareType.HOME_CARE],
            rationale="Residential support may fit if staying at home safely is difficult.",
        )

    return CareRecommendation(
        primary=CareType.ASSISTED_LIVING,
        alternatives=[CareType.HOME_CARE],
        rationale="Based on what is known so far, assisted living is a reasonable starting option.",
    )
