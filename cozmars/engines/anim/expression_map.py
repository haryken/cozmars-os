"""Vector-style: hành động → expression. SFX đi kèm catalog."""

MAP = {
    "boot": "focused",
    "idle": "auto",
    "explore": "happy",
    "wander": "happy",
    "obstacle": "surprised",
    "cliff": "sad",
    "wake": "surprised",
    "listen": "surprised",
    "nod": "happy",
    "lift": "focused",
    "firetruck": "angry",
    "dance": "happy",
    "sing": "happy",
    "scold": "sad",
    "hello": "happy",
    "goodbye": "sad",
    "sleep": "sleepy",
}


def expression_for(action: str) -> str:
    return MAP.get(action, "neutral")
