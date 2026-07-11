from pydantic import BaseModel, Field

from app.models.intake import IntakeRecord


class CreateSessionResponse(BaseModel):
    session_id: str
    state: str
    greeting: str


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1)


class SendMessageResponse(BaseModel):
    content: str
    state: str
    intake: IntakeRecord
    matches: list[dict] | None = None
    care_recommendation: dict | None = None


class SelectProviderRequest(BaseModel):
    provider_id: str


class SessionDetailResponse(BaseModel):
    session_id: str
    state: str
    status: str
    intake: IntakeRecord
    completion_percent: int
    missing_fields: list[str]
    messages: list[dict]
    matches: list[dict]
    care_recommendation: dict | None = None
    referral: dict | None = None


class OperatorSessionResponse(BaseModel):
    session_id: str
    state: str
    status: str
    intake: IntakeRecord
    completion_percent: int
    missing_fields: list[str]
    lead_score: int
    lead_category: str
    lead_breakdown: dict[str, int]
    transcript: list[dict]
    matches: list[dict]
    care_recommendation: dict | None = None
    referral: dict | None = None
