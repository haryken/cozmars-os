"""Text → intent Vector. Vosk EN keyphrase + Xiaozhi / UI tiếng Việt."""

from __future__ import annotations

PHRASES = {
    "go forward": "intent_imperative_forward",
    "come here": "intent_imperative_come",
    "stop": "intent_imperative_halt",
    "backup": "intent_imperative_backup",
    "turn left": "intent_imperative_turnleft",
    "turn right": "intent_imperative_turnright",
    "look at me": "intent_imperative_lookatme",
    "firetruck": "intent_play_firetruck",
    "fire truck": "intent_play_firetruck",
    "dance": "intent_imperative_dance",
    "sing": "intent_imperative_sing",
    "hello": "intent_greeting_hello",
    "good night": "intent_greeting_goodnight",
    "find cube": "intent_imperative_findcube",
    "pick up the cube": "intent_play_pickupcube",
    "fist bump": "intent_play_fistbump",
    "be quiet": "intent_imperative_quiet",
    "volume up": "intent_imperative_volumeup",
    "đi tới": "intent_imperative_forward",
    "lại đây": "intent_imperative_come",
    "dừng": "intent_imperative_halt",
    "xe cứu hỏa": "intent_play_firetruck",
    "xe cứu hoả": "intent_play_firetruck",
    "cứu hỏa": "intent_play_firetruck",
    "cứu hoả": "intent_play_firetruck",
    "còi xe": "intent_play_firetruck",
    "nhảy": "intent_imperative_dance",
    "hát đi": "intent_imperative_sing",
    "tìm khối": "intent_imperative_findcube",
    "chơi blackjack": "intent_play_blackjack",
    "màu mắt": "intent_imperative_eyecolor",
    "đổi màu mắt": "intent_imperative_eyecolor",
    "eye color": "intent_imperative_eyecolor",
    "change eye color": "intent_imperative_eyecolor",
}


SHOW_INTENTS = frozenset(
    {
        "intent_play_firetruck",
        "intent_imperative_dance",
        "intent_imperative_sing",
        "intent_play_fistbump",
    }
)


def match(text: str) -> str | None:
    t = (text or "").strip().lower()
    if not t:
        return None
    if t in PHRASES:
        return PHRASES[t]
    for k, v in PHRASES.items():
        if k in t:
            return v
    return None


def match_show(text: str) -> str | None:
    """Show trong phiên Xiaozhi — không cần đợi MCP (LLM hay quên self.show.*)."""
    intent = match(text)
    return intent if intent in SHOW_INTENTS else None


NOW_INTENTS = SHOW_INTENTS | {
    "intent_imperative_eyecolor",
    "intent_imperative_eyecolor_specific",
    "intent_imperative_eyecolor_specific_extend",
}

_COLOR_WORDS = (
    ("cầu vồng", "RAINBOW_EYES"),
    ("rainbow", "RAINBOW_EYES"),
    ("xanh ngọc", "TIP_OVER_TEAL"),
    ("xanh dương", "SINGULARITY_SAPPHIRE"),
    ("xanh lam", "SINGULARITY_SAPPHIRE"),
    ("xanh lá", "CONFUSION_MATRIX_GREEN"),
    ("sapphire", "SINGULARITY_SAPPHIRE"),
    ("tím", "FALSE_POSITIVE_PURPLE"),
    ("purple", "FALSE_POSITIVE_PURPLE"),
    ("cam", "OVERFIT_ORANGE"),
    ("orange", "OVERFIT_ORANGE"),
    ("vàng", "UNCANNY_YELLOW"),
    ("yellow", "UNCANNY_YELLOW"),
    ("lime", "NON_LINEAR_LIME"),
    ("teal", "TIP_OVER_TEAL"),
    ("cyan", "TIP_OVER_TEAL"),
    ("đỏ", "ROBOT_RED"),
    ("red", "ROBOT_RED"),
    ("xanh", "TIP_OVER_TEAL"),
)


def match_eye_color(text: str) -> tuple[str, dict] | None:
    t = (text or "").strip().lower()
    if not t:
        return None
    talking_eyes = any(k in t for k in ("mắt", "eye color", "eyecolor", "màu mắt", "đổi màu"))
    for word, color in _COLOR_WORDS:
        if word in t and (talking_eyes or word in ("màu mắt", "đổi màu mắt")):
            return "intent_imperative_eyecolor_specific_extend", {"color": color}
    if talking_eyes and any(k in t for k in ("màu", "color", "đổi")):
        return "intent_imperative_eyecolor", {}
    return None


def match_now(text: str) -> tuple[str, dict] | None:
    """Intent chạy ngay trong phiên Xiaozhi — không đợi MCP."""
    eye = match_eye_color(text)
    if eye:
        return eye
    intent = match_show(text)
    if intent:
        return intent, {}
    return None
