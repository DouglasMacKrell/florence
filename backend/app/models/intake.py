from pydantic import BaseModel, Field


class CallerInfo(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    relationship_to_care_recipient: str | None = None
    preferred_contact_method: str | None = None


class LocationInfo(BaseModel):
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None


class CareRecipientInfo(BaseModel):
    name: str | None = None
    age: int | None = None
    current_location: LocationInfo = Field(default_factory=LocationInfo)
    living_situation: str | None = None
    is_participating_in_decision: bool | None = None


class ActivitiesOfDailyLiving(BaseModel):
    bathing: bool | None = None
    dressing: bool | None = None
    toileting: bool | None = None
    transferring: bool | None = None
    eating: bool | None = None
    mobility: bool | None = None


class InstrumentalNeeds(BaseModel):
    meal_preparation: bool | None = None
    medication_reminders: bool | None = None
    transportation: bool | None = None
    housekeeping: bool | None = None
    shopping: bool | None = None


class CareNeedsInfo(BaseModel):
    requested_care_types: list[str] = Field(default_factory=list)
    activities_of_daily_living: ActivitiesOfDailyLiving = Field(
        default_factory=ActivitiesOfDailyLiving
    )
    instrumental_needs: InstrumentalNeeds = Field(default_factory=InstrumentalNeeds)
    memory_concerns: bool | None = None
    wandering_risk: bool | None = None
    fall_risk: bool | None = None
    behavioral_support_needed: bool | None = None
    overnight_support_needed: bool | None = None
    medical_equipment: list[str] = Field(default_factory=list)
    conditions_relevant_to_care: list[str] = Field(default_factory=list)
    notes: str | None = None


class TimingInfo(BaseModel):
    urgency: str | None = None
    desired_start_date: str | None = None
    temporary_or_long_term: str | None = None


class LocationPreferences(BaseModel):
    preferred_city: str | None = None
    preferred_state: str | None = None
    postal_code: str | None = None
    maximum_distance_miles: float | None = None
    must_remain_near_family: bool | None = None


class FinancialInfo(BaseModel):
    monthly_budget_min: int | None = None
    monthly_budget_max: int | None = None
    payment_sources: list[str] = Field(default_factory=list)
    long_term_care_insurance: bool | None = None
    medicaid: bool | None = None
    medicare: bool | None = None
    veterans_benefits: bool | None = None
    home_sale_expected: bool | None = None
    financial_notes: str | None = None


class PreferencesInfo(BaseModel):
    private_room_required: bool | None = None
    pet_friendly: bool | None = None
    language_preferences: list[str] = Field(default_factory=list)
    cultural_preferences: list[str] = Field(default_factory=list)
    religious_preferences: list[str] = Field(default_factory=list)
    gender_preferences_for_caregiver: str | None = None
    transportation_available: bool | None = None
    amenities: list[str] = Field(default_factory=list)
    deal_breakers: list[str] = Field(default_factory=list)


class DecisionProcessInfo(BaseModel):
    decision_makers: list[str] = Field(default_factory=list)
    other_family_involved: bool | None = None
    has_toured_providers: bool | None = None
    providers_already_considered: list[str] = Field(default_factory=list)
    main_obstacle: str | None = None


class ConsentInfo(BaseModel):
    consent_to_store_information: bool | None = None
    consent_to_contact: bool | None = None
    consent_to_share_with_matched_providers: bool | None = None
    referral_disclosure_acknowledged: bool | None = None


class SafetyInfo(BaseModel):
    immediate_danger: bool = False
    possible_emergency: bool = False
    abuse_or_neglect_concern: bool = False
    unsafe_living_situation: bool = False
    human_followup_required: bool = False
    safety_notes: str | None = None


REQUIRED_FIELD_CHECKS: list[tuple[str, str]] = [
    ("caller.name", "caller name"),
    ("caller.phone", "caller phone"),
    ("caller.relationship_to_care_recipient", "relationship to care recipient"),
    ("care_recipient.age", "care recipient age"),
    ("location", "location"),
    ("care_needs", "care needs"),
    ("timing.urgency", "timing or urgency"),
    ("financial", "budget or payment constraints"),
    ("consent.consent_to_contact", "consent to follow up"),
]


class IntakeRecord(BaseModel):
    caller: CallerInfo = Field(default_factory=CallerInfo)
    care_recipient: CareRecipientInfo = Field(default_factory=CareRecipientInfo)
    care_needs: CareNeedsInfo = Field(default_factory=CareNeedsInfo)
    timing: TimingInfo = Field(default_factory=TimingInfo)
    location_preferences: LocationPreferences = Field(default_factory=LocationPreferences)
    financial: FinancialInfo = Field(default_factory=FinancialInfo)
    preferences: PreferencesInfo = Field(default_factory=PreferencesInfo)
    decision_process: DecisionProcessInfo = Field(default_factory=DecisionProcessInfo)
    consent: ConsentInfo = Field(default_factory=ConsentInfo)
    safety: SafetyInfo = Field(default_factory=SafetyInfo)

    def missing_required_fields(self) -> list[str]:
        missing: list[str] = []
        if not self.caller.name:
            missing.append("caller.name")
        if not self.caller.phone:
            missing.append("caller.phone")
        if not self.caller.relationship_to_care_recipient:
            missing.append("caller.relationship_to_care_recipient")
        if self.care_recipient.age is None:
            missing.append("care_recipient.age")
        if not self._has_location():
            missing.append("location_preferences.postal_code")
        if not self._has_care_needs():
            missing.append("care_needs")
        if not self.timing.urgency:
            missing.append("timing.urgency")
        if not self._has_financial_constraints():
            missing.append("financial.monthly_budget_max")
        if self.consent.consent_to_contact is not True:
            missing.append("consent.consent_to_contact")
        return missing

    def completion_percent(self) -> int:
        total = len(REQUIRED_FIELD_CHECKS)
        filled = total - len(self.missing_required_fields())
        return int(round((filled / total) * 100))

    def is_qualified(self) -> bool:
        return self.completion_percent() == 100

    def _has_location(self) -> bool:
        return bool(
            self.location_preferences.postal_code
            or self.care_recipient.current_location.postal_code
            or (
                self.location_preferences.preferred_city
                and self.location_preferences.preferred_state
            )
        )

    def _has_care_needs(self) -> bool:
        adl = self.care_needs.activities_of_daily_living
        instrumental = self.care_needs.instrumental_needs
        return bool(
            self.care_needs.requested_care_types
            or self.care_needs.notes
            or any(
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
                    instrumental.transportation,
                    instrumental.housekeeping,
                    instrumental.shopping,
                    self.care_needs.memory_concerns,
                    self.care_needs.overnight_support_needed,
                )
            )
        )

    def _has_financial_constraints(self) -> bool:
        return bool(
            self.financial.monthly_budget_min is not None
            or self.financial.monthly_budget_max is not None
            or self.financial.payment_sources
        )

    def preferred_postal_code(self) -> str | None:
        return (
            self.location_preferences.postal_code
            or self.care_recipient.current_location.postal_code
        )
