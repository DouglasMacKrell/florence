from pydantic import BaseModel, Field


class MatchResult(BaseModel):
    provider_id: str
    score: float
    rank: int
    strengths: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    disqualifiers: list[str] = Field(default_factory=list)
    referral_eligible: bool = True
    estimated_referral_value: int = 0
