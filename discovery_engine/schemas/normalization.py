"""Helpers to normalize loosely formatted LLM output values."""

from typing import Any

_STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "to", "for", "of",
    "in", "on", "and", "or", "with", "that", "this", "it", "not", "be",
    "have", "has", "do", "does", "from", "they", "their", "i", "we",
    "you", "my", "our", "its", "but", "so", "if", "as", "at", "by",
    "up", "out", "about", "when", "how", "what", "which", "who", "will",
}


def text_similarity(text_a: str, text_b: str) -> float:
    """Jaccard similarity on significant words + bigrams (0..1)."""

    def _tokens(text: str) -> set[str]:
        words = [w.lower().strip(".,!?;:\"'()") for w in text.split()]
        words = [w for w in words if len(w) > 2 and w not in _STOP_WORDS]
        unigrams = set(words)
        bigrams = {f"{words[i]}_{words[i + 1]}" for i in range(len(words) - 1)}
        return unigrams | bigrams

    ta, tb = _tokens(text_a), _tokens(text_b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


_TEXT_SCORES: dict[str, float] = {"high": 0.8, "medium": 0.5, "low": 0.2}


def to_score_0_1(value: Any) -> float:
    """Normalize scores into 0..1 (supports %, 0-10, 0-100, numeric strings, high/medium/low)."""
    if value is None or value == "":
        return 0.0
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, str):
        raw = value.strip().lower().rstrip("%")
        if not raw:
            return 0.0
        if raw in _TEXT_SCORES:
            return _TEXT_SCORES[raw]
        value = raw
    try:
        num = float(value)
    except (TypeError, ValueError):
        return 0.0

    if num > 1.0:
        if num <= 10.0:
            num = num / 10.0
        elif num <= 100.0:
            num = num / 100.0
    if num < 0.0:
        return 0.0
    if num > 1.0:
        return 1.0
    return num


def map_importance(value: Any) -> str:
    text = to_text(value).lower()
    if text in {"critical", "high", "medium", "low"}:
        return text
    try:
        score = float(text)
    except ValueError:
        return to_text(value)
    if score >= 8:
        return "critical"
    if score >= 6:
        return "high"
    if score >= 4:
        return "medium"
    return "low"


def map_satisfaction(value: Any) -> str:
    text = to_text(value).lower()
    allowed = {
        "very_unsatisfied",
        "unsatisfied",
        "neutral",
        "satisfied",
        "very_satisfied",
    }
    if text in allowed:
        return text
    try:
        score = float(text)
    except ValueError:
        return to_text(value)
    if score <= 2:
        return "very_unsatisfied"
    if score <= 4:
        return "unsatisfied"
    if score <= 6:
        return "neutral"
    if score <= 8:
        return "satisfied"
    return "very_satisfied"


def map_severity(value: Any) -> str:
    text = to_text(value).lower()
    if text in {"critical", "high", "medium", "low"}:
        return text
    try:
        score = float(text)
    except ValueError:
        return to_text(value)
    if score >= 8:
        return "critical"
    if score >= 6:
        return "high"
    if score >= 4:
        return "medium"
    return "low"
