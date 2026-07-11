import re

_FILLER_TRANSCRIPTS = {
    "sure",
    "sure.",
    "remember",
    "remember.",
    "yes",
    "yes.",
    "no",
    "no.",
    "ok",
    "ok.",
    "okay",
    "okay.",
    "uh",
    "um",
    "hello",
    "hi",
    "thanks",
    "thank you",
}


def should_ignore_transcript(text: str) -> bool:
    cleaned = text.strip().lower()
    if not cleaned:
        return True
    if cleaned in _FILLER_TRANSCRIPTS:
        return True
    words = re.findall(r"[a-z0-9']+", cleaned)
    return len(words) < 2 and len(cleaned) < 12


def shorten_for_phone(text: str, *, max_chars: int = 240) -> str:
    compact = " ".join(text.split())
    if len(compact) <= max_chars:
        return compact
    clipped = compact[: max_chars - 1].rsplit(" ", 1)[0]
    return f"{clipped}…"
