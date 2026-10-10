from collections.abc import Iterator
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.agent.care_recommender import recommend_care_types
from app.agent.consent_boundary import (
    FOLLOW_UP_CONTACT_QUESTION,
    PROVIDER_SHARE_QUESTION,
    STORE_INFORMATION_QUESTION,
    consent_kind_for_state,
    consent_question_for_kind,
    ensure_consent_gate_state,
    is_consent_collecting_state,
    process_consent_turn,
    should_interpret_as_consent_answer,
)
from app.agent.state_machine import (
    ORDERED_STATES,
    ConversationState,
    advance_state,
    advance_through_satisfied_states,
)
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
from app.services.intake_extraction import (
    apply_decision_makers_from_message,
    extract_state_owned_rules,
    extract_with_ollama,
    extract_with_rules,
)
from app.services.intake_summary import build_intake_confirmation_message
from app.services.provider_loader import list_provider_records
from app.services.response_generation import (
    generate_assistant_reply,
    stream_assistant_reply,
    stream_text_chunks,
)


@dataclass
class AssistantTurn:
    content: str
    state: str
    intake: IntakeRecord
    matches: list[dict] | None = None
    care_recommendation: dict | None = None


@dataclass
class PreparedTurn:
    session_id: str
    state: str
    intake: IntakeRecord
    conversation_state: ConversationStateEnum
    fallback: str
    history: list[dict[str, str]]
    matches: list[dict] | None = None
    care_recommendation: dict | None = None
    reply_override: str | None = None


STATE_PROMPTS = {
    ConversationState.GREETING: (
        "Thank you for reaching out. I'm Florence, a care-navigation assistant. "
        "I can help you understand elder-care options and find providers that may fit."
    ),
    ConversationState.DISCLOSURE_AND_CONSENT: STORE_INFORMATION_QUESTION,
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
    ConversationState.COLLECT_FOLLOWUP_CONSENT: FOLLOW_UP_CONTACT_QUESTION,
    ConversationState.COLLECT_CALLER_CONTACT: (
        "What is the best phone number to reach you at for care-navigation updates "
        "and provider referral coordination?"
    ),
    ConversationState.CONFIRM_SUMMARY: (
        "Let me make sure I have this right. Does that summary sound accurate?"
    ),  # full text: build_intake_confirmation_message()
    ConversationState.MATCH_PROVIDERS: (
        "Based on what you shared, I found a few providers that may fit. I'll show them next."
    ),
    ConversationState.EXPLAIN_RECOMMENDATIONS: (
        "Here are the strongest matches I found and why each may fit."
    ),
    ConversationState.CAPTURE_FOLLOWUP_CONSENT: PROVIDER_SHARE_QUESTION,
    ConversationState.END_OR_HUMAN_HANDOFF: (
        "Thank you. A care specialist can follow up with the next steps."
    ),
}


def _advance_with_side_effects(
    current_state: ConversationState,
    intake: IntakeRecord,
) -> tuple[ConversationState, bool]:
    state = current_state
    crossed_match = False
    for _ in range(len(ORDERED_STATES)):
        next_state = advance_state(state, intake)
        if next_state == state:
            break
        if (
            next_state == ConversationState.MATCH_PROVIDERS
            and state != ConversationState.MATCH_PROVIDERS
        ):
            crossed_match = True
        state = next_state
    return state, crossed_match


def _populate_provider_matches(
    db: Session,
    session_id: str,
    intake: IntakeRecord,
) -> tuple[list[dict], dict]:
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
    return matches_data, care_recommendation_data


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


def process_user_message(
    db: Session,
    session_id: str,
    content: str,
    *,
    scripted_reply: bool = False,
) -> AssistantTurn:
    prepared = prepare_user_message_turn(
        db,
        session_id,
        content,
        rules_only_extraction=scripted_reply,
    )
    reply = _generate_reply(prepared, scripted_reply=scripted_reply)
    return complete_user_message_turn(db, prepared, reply)


def prepare_user_message_turn(
    db: Session,
    session_id: str,
    content: str,
    *,
    rules_only_extraction: bool = False,
) -> PreparedTurn:
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

    started_in_consent_state = consent_kind_for_state(current_state) is not None
    consent_outcome = None
    entered_follow_up_consent_gate = False
    history = _message_history(session)

    if started_in_consent_state:
        consent_kind = consent_kind_for_state(current_state)
        assert consent_kind is not None
        if should_interpret_as_consent_answer(content, consent_kind, history):
            consent_outcome = process_consent_turn(intake, content, consent_kind)
        else:
            _extract_intake_fields(
                intake,
                content,
                current_state,
                history,
                rules_only=rules_only_extraction,
            )
    else:
        _extract_intake_fields(
            intake,
            content,
            current_state,
            history,
            rules_only=rules_only_extraction,
        )
        if current_state == ConversationStateEnum.COLLECT_FINANCIAL_REQUIREMENTS:
            intake.financial.budget_discussed = True
        gated_state = ensure_consent_gate_state(current_state, intake)
        if gated_state != current_state:
            current_state = ConversationStateEnum(gated_state.value)
            session.current_state = current_state.value
            intake_orm.current_state = current_state.value
            entered_follow_up_consent_gate = True

    crossed_match = False
    next_state = advance_through_satisfied_states(current_state, intake)
    crossed_match = (
        next_state == ConversationState.MATCH_PROVIDERS
        and current_state != ConversationState.MATCH_PROVIDERS
    )
    if not started_in_consent_state and not entered_follow_up_consent_gate:
        next_state = ensure_consent_gate_state(next_state, intake)
    if next_state != current_state:
        session.current_state = next_state.value
        intake_orm.current_state = next_state.value
        if current_state == ConversationStateEnum.COLLECT_FINANCIAL_REQUIREMENTS:
            apply_decision_makers_from_message(
                intake,
                content,
                ConversationState.UNDERSTAND_DECISION_PROCESS,
            )

    intake_orm.structured_json = intake.model_dump()
    intake_orm.completion_percent = intake.completion_percent()

    entered_confirm_summary = (
        next_state == ConversationState.CONFIRM_SUMMARY
        and current_state != ConversationState.CONFIRM_SUMMARY
    )
    at_confirm_summary = (
        ConversationStateEnum(session.current_state) == ConversationStateEnum.CONFIRM_SUMMARY
    )

    fallback = STATE_PROMPTS.get(
        ConversationStateEnum(session.current_state), "Thank you for sharing that."
    )
    if (
        ConversationStateEnum(session.current_state) == ConversationStateEnum.COLLECT_CALLER_CONTACT
        and not intake.caller.name
    ):
        fallback = "May I have your name for care-navigation and referral coordination?"
    if entered_confirm_summary or at_confirm_summary:
        fallback = build_intake_confirmation_message(intake)

    care_recommendation_data = None
    matches_data = None
    reply_override = None
    if crossed_match:
        matches_data, care_recommendation_data = _populate_provider_matches(
            db,
            session_id,
            intake,
        )
        reply_override = (
            f"I recommend exploring {care_recommendation_data['primary'].replace('_', ' ')} first. "
            f"I found {len(matches_data)} provider options that may fit."
        )

    if entered_follow_up_consent_gate and reply_override is None:
        reply_override = FOLLOW_UP_CONTACT_QUESTION

    if consent_outcome is not None and reply_override is None:
        if consent_outcome.consent_resolved:
            reply_override = fallback
        else:
            reply_override = consent_outcome.scripted_reply

    if (
        is_consent_collecting_state(ConversationStateEnum(session.current_state))
        and reply_override is None
        and not entered_follow_up_consent_gate
    ):
        kind = consent_kind_for_state(ConversationStateEnum(session.current_state))
        if kind is not None:
            reply_override = consent_question_for_kind(kind)

    if entered_confirm_summary and reply_override is None:
        reply_override = fallback

    return PreparedTurn(
        session_id=session_id,
        state=session.current_state,
        intake=intake,
        conversation_state=ConversationStateEnum(session.current_state),
        fallback=fallback,
        history=_message_history(session),
        matches=matches_data,
        care_recommendation=care_recommendation_data,
        reply_override=reply_override,
    )


def _uses_scripted_reply(prepared: PreparedTurn) -> bool:
    if is_consent_collecting_state(prepared.conversation_state):
        return True
    return prepared.conversation_state == ConversationStateEnum.COLLECT_CALLER_CONTACT


def _generate_reply(prepared: PreparedTurn, *, scripted_reply: bool = False) -> str:
    if prepared.reply_override is not None:
        return prepared.reply_override
    if _uses_scripted_reply(prepared):
        return prepared.fallback
    return generate_assistant_reply(
        intake=prepared.intake,
        state=prepared.conversation_state,
        history=prepared.history,
        fallback=prepared.fallback,
        scripted_only=scripted_reply,
    )


def complete_user_message_turn(
    db: Session,
    prepared: PreparedTurn,
    reply: str,
) -> AssistantTurn:
    db.add(
        MessageRecord(
            session_id=prepared.session_id,
            role="assistant",
            content=reply,
        )
    )
    db.flush()
    return AssistantTurn(
        content=reply,
        state=prepared.state,
        intake=prepared.intake,
        matches=prepared.matches,
        care_recommendation=prepared.care_recommendation,
    )


def stream_user_message_tokens(prepared: PreparedTurn) -> Iterator[str]:
    if prepared.reply_override is not None:
        yield from stream_text_chunks(prepared.reply_override)
        return
    if _uses_scripted_reply(prepared):
        yield from stream_text_chunks(prepared.fallback)
        return
    yield from stream_assistant_reply(
        intake=prepared.intake,
        state=prepared.conversation_state,
        history=prepared.history,
        fallback=prepared.fallback,
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
    *,
    rules_only: bool = False,
    skip_consent_fields: bool = False,
) -> None:
    if rules_only:
        extract_with_rules(intake, content, state, skip_consent_fields=skip_consent_fields)
        return

    settings = get_settings()
    if settings.enable_ollama:
        signals = extract_with_ollama(
            intake,
            content,
            state,
            history,
            skip_consent_fields=skip_consent_fields,
        )
        if signals is not None:
            return
    extract_state_owned_rules(
        intake,
        content,
        state,
        skip_consent_fields=skip_consent_fields,
    )


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
