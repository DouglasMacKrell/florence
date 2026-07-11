from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.agent.care_recommender import recommend_care_types
from app.agent.state_machine import ConversationState, advance_state
from app.config import get_settings
from app.db.tables import (
    CareRecommendationRecordORM,
    IntakeRecordORM,
    MatchRecordORM,
    MessageRecord,
    ReferralRecordORM,
    SessionRecord,
)
from app.matching.engine import match_providers
from app.models.enums import ConversationState as ConversationStateEnum
from app.models.intake import IntakeRecord
from app.services.intake_extraction import extract_with_ollama, extract_with_rules
from app.services.provider_loader import list_provider_records
from app.services.response_generation import generate_assistant_reply


@dataclass
class AssistantTurn:
    content: str
    state: str
    intake: IntakeRecord
    matches: list[dict] | None = None
    care_recommendation: dict | None = None


STATE_PROMPTS = {
    ConversationState.GREETING: (
        "Thank you for reaching out. I'm Florence, a care-navigation assistant. "
        "I can help you understand elder-care options and find providers that may fit."
    ),
    ConversationState.DISCLOSURE_AND_CONSENT: (
        "Before we begin, I'm an automated assistant, not a medical professional. "
        "With your permission, I'll save what you share so a care specialist can follow up. "
        "May I store the information you provide?"
    ),
    ConversationState.UNDERSTAND_REASON_FOR_CALL: (
        "Could you tell me what has been happening and what led you to look for care now?"
    ),
    ConversationState.IDENTIFY_CARE_RECIPIENT: ("Who is the care for, and about how old are they?"),
    ConversationState.ASSESS_CARE_NEEDS: (
        "What kinds of help have become difficult — bathing, meals, mobility, or memory?"
    ),
    ConversationState.ASSESS_URGENCY_AND_SAFETY: ("How soon are you hoping care can start?"),
    ConversationState.COLLECT_LOCATION_REQUIREMENTS: ("What city or ZIP code should care be near?"),
    ConversationState.COLLECT_FINANCIAL_REQUIREMENTS: (
        "Do you have a monthly budget range in mind, or payment sources we should keep in mind?"
    ),
    ConversationState.COLLECT_PREFERENCES: (
        "Are there any preferences that matter — private room, language, pets, or transportation?"
    ),
    ConversationState.UNDERSTAND_DECISION_PROCESS: (
        "Who else is involved in making this decision?"
    ),
    ConversationState.CONFIRM_SUMMARY: (
        "Let me make sure I have this right. Does that summary sound accurate?"
    ),
    ConversationState.MATCH_PROVIDERS: (
        "Based on what you shared, I found a few providers that may fit. I'll show them next."
    ),
    ConversationState.EXPLAIN_RECOMMENDATIONS: (
        "Here are the strongest matches I found and why each may fit."
    ),
    ConversationState.CAPTURE_FOLLOWUP_CONSENT: (
        "May we share your information with the provider you choose so they can follow up?"
    ),
    ConversationState.END_OR_HUMAN_HANDOFF: (
        "Thank you. A care specialist can follow up with the next steps."
    ),
}


def create_session(db: Session) -> SessionRecord:
    session = SessionRecord()
    db.add(session)
    db.flush()
    db.add(
        IntakeRecordORM(
            session_id=session.id, structured_json={}, current_state=session.current_state
        )
    )
    greeting = STATE_PROMPTS[ConversationState.GREETING]
    db.add(MessageRecord(session_id=session.id, role="assistant", content=greeting))
    db.flush()
    return session


def get_session(db: Session, session_id: str) -> SessionRecord | None:
    return db.get(SessionRecord, session_id)


def process_user_message(db: Session, session_id: str, content: str) -> AssistantTurn:
    session = db.get(SessionRecord, session_id)
    if session is None:
        raise ValueError("Session not found")

    db.add(MessageRecord(session_id=session_id, role="user", content=content))
    intake_orm = session.intake
    if intake_orm is None:
        intake_orm = IntakeRecordORM(session_id=session_id, structured_json={})
        db.add(intake_orm)
        db.flush()

    intake = IntakeRecord.model_validate(intake_orm.structured_json)
    current_state = ConversationStateEnum(session.current_state)
    if current_state == ConversationStateEnum.GREETING:
        session.current_state = ConversationStateEnum.DISCLOSURE_AND_CONSENT.value
        intake_orm.current_state = session.current_state
        current_state = ConversationStateEnum.DISCLOSURE_AND_CONSENT

    _extract_intake_fields(intake, content, current_state, _message_history(session))

    next_state = advance_state(current_state, intake)
    if next_state != current_state:
        session.current_state = next_state.value
        intake_orm.current_state = next_state.value

    intake_orm.structured_json = intake.model_dump()
    intake_orm.completion_percent = intake.completion_percent()

    fallback = STATE_PROMPTS.get(
        ConversationStateEnum(session.current_state), "Thank you for sharing that."
    )
    reply = generate_assistant_reply(
        intake=intake,
        state=ConversationStateEnum(session.current_state),
        history=_message_history(session),
        fallback=fallback,
    )
    care_recommendation_data = None
    matches_data = None

    if (
        next_state == ConversationState.MATCH_PROVIDERS
        and current_state != ConversationState.MATCH_PROVIDERS
    ):
        recommendation = recommend_care_types(intake)
        care_recommendation_data = {
            "primary": recommendation.primary,
            "alternatives": recommendation.alternatives,
            "rationale": recommendation.rationale,
        }
        db.merge(
            CareRecommendationRecordORM(
                session_id=session_id,
                primary_care_type=recommendation.primary,
                alternatives_json=recommendation.alternatives,
                rationale=recommendation.rationale,
            )
        )
        providers = list_provider_records(db)
        matches = match_providers(intake, providers, limit=3)
        matches_data = [match.model_dump() for match in matches]
        for match in matches:
            db.add(
                MatchRecordORM(
                    session_id=session_id,
                    provider_id=match.provider_id,
                    score=match.score,
                    rank=match.rank,
                    explanation_json=match.model_dump(),
                )
            )
        reply = (
            f"I recommend exploring {recommendation.primary.replace('_', ' ')} first. "
            f"I found {len(matches)} provider options that may fit."
        )

    db.add(MessageRecord(session_id=session_id, role="assistant", content=reply))
    db.flush()

    return AssistantTurn(
        content=reply,
        state=session.current_state,
        intake=intake,
        matches=matches_data,
        care_recommendation=care_recommendation_data,
    )


def _message_history(session: SessionRecord) -> list[dict[str, str]]:
    return [
        {"role": message.role, "content": message.content}
        for message in sorted(session.messages, key=lambda item: item.created_at)
    ]


def _extract_intake_fields(
    intake: IntakeRecord,
    content: str,
    state: ConversationStateEnum,
    history: list[dict[str, str]],
) -> None:
    settings = get_settings()
    if settings.enable_ollama:
        signals = extract_with_ollama(intake, content, state, history)
        if signals is not None:
            extract_with_rules(intake, content, state)
            return
    extract_with_rules(intake, content, state)


def select_provider(db: Session, session_id: str, provider_id: str) -> dict:
    session = db.get(SessionRecord, session_id)
    if session is None:
        raise ValueError("Session not found")
    intake = IntakeRecord.model_validate(session.intake.structured_json if session.intake else {})
    referral = ReferralRecordORM(
        session_id=session_id,
        provider_id=provider_id,
        status="pending",
        validation_snapshot=intake.model_dump(),
    )
    db.merge(referral)
    db.flush()
    return {"session_id": session_id, "provider_id": provider_id, "status": "pending"}


def confirm_referral(db: Session, session_id: str) -> dict:
    session = db.get(SessionRecord, session_id)
    if session is None:
        raise ValueError("Session not found")
    intake = IntakeRecord.model_validate(session.intake.structured_json if session.intake else {})
    if intake.consent.consent_to_contact is not True:
        raise ValueError("Consent to contact is required")
    referral = db.query(ReferralRecordORM).filter_by(session_id=session_id).one_or_none()
    if referral is None:
        raise ValueError("No provider selected")
    referral.status = "mock_complete"
    session.status = "completed"
    db.flush()
    return {
        "session_id": session_id,
        "provider_id": referral.provider_id,
        "status": referral.status,
    }
