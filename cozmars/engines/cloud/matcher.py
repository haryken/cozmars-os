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
