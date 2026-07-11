from sqlalchemy.orm import Session

from app.api.schemas import OperatorSessionResponse
from app.db.tables import (
    CareRecommendationRecordORM,
    MatchRecordORM,
    ReferralRecordORM,
)
from app.models.intake import IntakeRecord
from app.services.conversation import get_session
from app.services.lead_scoring import compute_lead_score


def build_operator_session_view(db: Session, session_id: str) -> OperatorSessionResponse:
    session = get_session(db, session_id)
    if session is None:
        raise ValueError("Session not found")

    intake = IntakeRecord.model_validate(session.intake.structured_json if session.intake else {})
    lead = compute_lead_score(intake)
    messages = [
        {
            "role": message.role,
            "content": message.content,
            "created_at": message.created_at.isoformat(),
        }
        for message in sorted(session.messages, key=lambda item: item.created_at)
    ]
    matches = [
        row.explanation_json
        for row in db.query(MatchRecordORM)
        .filter_by(session_id=session_id)
        .order_by(MatchRecordORM.rank)
    ]
    recommendation = (
        db.query(CareRecommendationRecordORM).filter_by(session_id=session_id).one_or_none()
    )
    referral = db.query(ReferralRecordORM).filter_by(session_id=session_id).one_or_none()

    selected_referral_value = None
    if referral is not None:
        for match in matches:
            if match.get("provider_id") == referral.provider_id:
                selected_referral_value = match.get("estimated_referral_value")
                break

    return OperatorSessionResponse(
        session_id=session.id,
        state=session.current_state,
        status=session.status,
        intake=intake,
        completion_percent=intake.completion_percent(),
        missing_fields=intake.missing_required_fields(),
        lead_score=lead.score,
        lead_category=lead.category,
        lead_breakdown=lead.breakdown,
        transcript=messages,
        matches=matches,
        care_recommendation=(
            {
                "primary": recommendation.primary_care_type,
                "alternatives": recommendation.alternatives_json,
                "rationale": recommendation.rationale,
            }
            if recommendation
            else None
        ),
        referral=(
            {
                "provider_id": referral.provider_id,
                "status": referral.status,
                "estimated_referral_value": selected_referral_value,
            }
            if referral
            else None
        ),
    )
