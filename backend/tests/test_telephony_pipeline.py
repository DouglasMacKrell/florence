from app.voice.pipeline import _telephony_vad_analyzer


def test_telephony_vad_analyzer_uses_lenient_phone_thresholds() -> None:
    analyzer = _telephony_vad_analyzer()
    assert analyzer.params.confidence >= 0.6
    assert analyzer.params.min_volume >= 0.4
    assert analyzer.params.stop_secs >= 0.9
