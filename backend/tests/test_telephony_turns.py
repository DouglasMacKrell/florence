from app.voice.telephony_turns import shorten_for_phone, should_ignore_transcript


def test_should_ignore_filler_transcripts() -> None:
    assert should_ignore_transcript("Sure.")
    assert should_ignore_transcript("Remember.")
    assert should_ignore_transcript("  ")


def test_should_accept_real_utterances() -> None:
    assert not should_ignore_transcript("Hi my name is Doug and I need help for my father.")
    assert not should_ignore_transcript("347 495 1122")


def test_shorten_for_phone_limits_length() -> None:
    long_text = "word " * 80
    shortened = shorten_for_phone(long_text, max_chars=50)
    assert len(shortened) <= 50
    assert shortened.endswith("…")
