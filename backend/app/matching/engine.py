from app.models.intake import IntakeRecord
from app.models.match import MatchResult
from app.models.provider import ProviderRecord

WEIGHTS = {
    "care_fit": 0.35,
    "budget_fit": 0.20,
    "location_fit": 0.15,
    "availability_fit": 0.10,
    "preference_fit": 0.10,
    "quality_fit": 0.05,
    "referral_fit": 0.05,
}


def match_providers(
    intake: IntakeRecord,
    providers: list[ProviderRecord],
    *,
    limit: int = 3,
) -> list[MatchResult]:
    scored: list[MatchResult] = []
    for provider in providers:
        disqualifiers = _hard_disqualifiers(intake, provider)
        if disqualifiers:
            continue
        score, strengths, concerns = _score_provider(intake, provider)
        scored.append(
            MatchResult(
                provider_id=provider.id,
                score=round(score, 2),
                rank=0,
                strengths=strengths,
                concerns=concerns,
                referral_eligible=provider.referral.eligible,
                estimated_referral_value=provider.referral.estimated_bounty,
            )
        )

    scored.sort(key=lambda item: item.score, reverse=True)
    results = scored[:limit]
    for index, result in enumerate(results, start=1):
        result.rank = index
    return results


def _hard_disqualifiers(intake: IntakeRecord, provider: ProviderRecord) -> list[str]:
    reasons: list[str] = []
    budget_max = intake.financial.monthly_budget_max
    if budget_max is not None and provider.pricing.monthly_min > budget_max:
        reasons.append("minimum price above caller budget")

    requested_types = set(intake.care_needs.requested_care_types)
    if requested_types:
        provider_types = {provider.provider_type, *provider.care_levels}
        if requested_types.isdisjoint(provider_types):
            reasons.append("does not provide requested care type")

    for deal_breaker in intake.preferences.deal_breakers:
        if deal_breaker in provider.amenities or deal_breaker == provider.provider_type:
            reasons.append(f"deal breaker: {deal_breaker}")

    postal_code = intake.preferred_postal_code()
    max_distance = intake.location_preferences.maximum_distance_miles
    if postal_code and max_distance is not None:
        distance = _approx_distance_miles(postal_code, provider.address.postal_code)
        if distance > max(max_distance, provider.service_area_miles):
            reasons.append("outside geographic radius")

    if intake.preferences.language_preferences and not set(
        intake.preferences.language_preferences
    ).intersection(provider.languages):
        reasons.append("language preference not supported")

    return reasons


def _score_provider(
    intake: IntakeRecord,
    provider: ProviderRecord,
) -> tuple[float, list[str], list[str]]:
    strengths: list[str] = []
    concerns: list[str] = []

    care_fit = _care_fit(intake, provider, strengths, concerns)
    budget_fit = _budget_fit(intake, provider, strengths, concerns)
    location_fit = _location_fit(intake, provider, strengths, concerns)
    availability_fit = 70.0 if provider.availability.status != "unavailable" else 20.0
    preference_fit = _preference_fit(intake, provider, strengths, concerns)
    quality_fit = min(provider.quality.rating / 5.0, 1.0) * 100
    referral_fit = 100.0 if provider.referral.eligible else 0.0

    total = (
        care_fit * WEIGHTS["care_fit"]
        + budget_fit * WEIGHTS["budget_fit"]
        + location_fit * WEIGHTS["location_fit"]
        + availability_fit * WEIGHTS["availability_fit"]
        + preference_fit * WEIGHTS["preference_fit"]
        + quality_fit * WEIGHTS["quality_fit"]
        + referral_fit * WEIGHTS["referral_fit"]
    )
    return total, strengths, concerns


def _care_fit(
    intake: IntakeRecord,
    provider: ProviderRecord,
    strengths: list[str],
    concerns: list[str],
) -> float:
    score = 50.0
    requested = set(intake.care_needs.requested_care_types)
    provider_levels = {provider.provider_type, *provider.care_levels}
    if requested and not requested.isdisjoint(provider_levels):
        score += 25
        strengths.append(f"Provides {', '.join(sorted(requested & provider_levels))}")

    if intake.care_needs.memory_concerns and provider.supports.memory_support:
        score += 10
        strengths.append("Offers memory support")
    elif intake.care_needs.memory_concerns:
        concerns.append("Memory support not clearly listed")

    if intake.care_needs.overnight_support_needed and provider.supports.overnight_supervision:
        score += 10
        strengths.append("Offers overnight supervision")

    return min(score, 100.0)


def _budget_fit(
    intake: IntakeRecord,
    provider: ProviderRecord,
    strengths: list[str],
    concerns: list[str],
) -> float:
    budget_min = intake.financial.monthly_budget_min
    budget_max = intake.financial.monthly_budget_max
    if budget_max is None:
        return 60.0

    if provider.pricing.monthly_min <= budget_max and provider.pricing.monthly_max >= (
        budget_min or 0
    ):
        strengths.append("Estimated price overlaps stated monthly budget")
        return 100.0

    if provider.pricing.monthly_min <= budget_max:
        concerns.append("Upper price range may exceed budget")
        return 70.0

    concerns.append("Pricing may exceed stated budget")
    return 20.0


def _location_fit(
    intake: IntakeRecord,
    provider: ProviderRecord,
    strengths: list[str],
    concerns: list[str],
) -> float:
    postal_code = intake.preferred_postal_code()
    if not postal_code:
        return 60.0

    distance = _approx_distance_miles(postal_code, provider.address.postal_code)
    if distance <= 5:
        strengths.append(f"Located about {distance:.1f} miles from preferred ZIP code")
        return 100.0
    if distance <= 10:
        strengths.append(f"Located about {distance:.1f} miles from preferred ZIP code")
        return 85.0
    if distance <= 15:
        return 65.0

    concerns.append("May be farther than preferred distance")
    return 35.0


def _preference_fit(
    intake: IntakeRecord,
    provider: ProviderRecord,
    strengths: list[str],
    concerns: list[str],
) -> float:
    score = 60.0
    if intake.preferences.private_room_required and "private_rooms" in provider.amenities:
        score += 15
        strengths.append("Offers private rooms")
    elif intake.preferences.private_room_required:
        concerns.append("Private room availability not verified")

    if intake.preferences.pet_friendly and "pet_friendly" in provider.amenities:
        score += 10
        strengths.append("Pet friendly")

    if intake.preferences.language_preferences:
        overlap = set(intake.preferences.language_preferences).intersection(provider.languages)
        if overlap:
            score += 10
            strengths.append(f"Supports {', '.join(sorted(overlap))}-speaking families")

    if "transportation" in intake.preferences.amenities and "transportation" in provider.amenities:
        score += 5
        strengths.append("Transportation available")

    return min(score, 100.0)


def _approx_distance_miles(postal_a: str, postal_b: str) -> float:
    if postal_a[:3] == postal_b[:3]:
        return 3.0
    if postal_a[:2] == postal_b[:2]:
        return 8.0
    return 20.0 + abs(_zip_prefix_value(postal_a) - _zip_prefix_value(postal_b)) / 100.0


def _zip_prefix_value(postal_code: str) -> int:
    digits = "".join(ch for ch in postal_code if ch.isdigit())
    return int(digits[:3]) if len(digits) >= 3 else 0
