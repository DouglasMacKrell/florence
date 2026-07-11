from app.agent.safety import detect_safety_signals


def test_detects_emergency_language() -> None:
    result = detect_safety_signals("He is having chest pain and can barely breathe.")
    assert result.possible_emergency is True
    assert result.human_followup_required is True


def test_detects_abuse_concern() -> None:
    result = detect_safety_signals("I think my aunt is being neglected by her caregiver.")
    assert result.abuse_or_neglect_concern is True


def test_routine_intake_is_not_flagged() -> None:
    result = detect_safety_signals("My mother needs help with meals and bathing.")
    assert result.possible_emergency is False
    assert result.abuse_or_neglect_concern is False


def test_negated_serious_injury_is_not_emergency() -> None:
    result = detect_safety_signals("He fell recently without a serious injury.")
    assert result.possible_emergency is False
