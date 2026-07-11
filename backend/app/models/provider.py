from pydantic import BaseModel, Field


class ProviderAddress(BaseModel):
    street: str
    city: str
    state: str
    postal_code: str
    latitude: float
    longitude: float


class ProviderSupports(BaseModel):
    bathing: bool = False
    dressing: bool = False
    toileting: bool = False
    mobility: bool = False
    medication_management: bool = False
    memory_support: bool = False
    two_person_transfer: bool = False
    overnight_supervision: bool = False


class ProviderPricing(BaseModel):
    monthly_min: int
    monthly_max: int
    entrance_fee: int = 0


class ProviderAvailability(BaseModel):
    status: str = "unknown"
    last_verified_at: str | None = None


class ProviderReferral(BaseModel):
    eligible: bool = True
    estimated_bounty: int = 0
    requirements: str | None = None


class ProviderQuality(BaseModel):
    rating: float = 0.0
    review_count: int = 0
    license_status: str = "unverified_for_demo"


class ProviderRecord(BaseModel):
    id: str
    name: str
    provider_type: str
    address: ProviderAddress
    service_area_miles: float = 15.0
    care_levels: list[str] = Field(default_factory=list)
    supports: ProviderSupports = Field(default_factory=ProviderSupports)
    pricing: ProviderPricing
    payment_options: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    amenities: list[str] = Field(default_factory=list)
    availability: ProviderAvailability = Field(default_factory=ProviderAvailability)
    referral: ProviderReferral = Field(default_factory=ProviderReferral)
    quality: ProviderQuality = Field(default_factory=ProviderQuality)
    notes: str | None = None
