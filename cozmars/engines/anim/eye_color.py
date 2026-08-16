"""Màu mắt Vector: hue/sat toàn cục, không gắn biểu cảm."""

from __future__ import annotations

PRESETS: dict[str, tuple[float, float]] = {
    "TIP_OVER_TEAL": (0.42, 1.00),
    "OVERFIT_ORANGE": (0.05, 0.95),
    "UNCANNY_YELLOW": (0.11, 1.00),
    "NON_LINEAR_LIME": (0.21, 1.00),
    "SINGULARITY_SAPPHIRE": (0.57, 1.00),
    "FALSE_POSITIVE_PURPLE": (0.83, 0.76),
    "CONFUSION_MATRIX_GREEN": (0.30, 1.00),
    "RAINBOW_EYES": (0.97, 0.98),
    "ROBOT_RED": (0.97, 0.98),
}

ALIASES = {
    "teal": "TIP_OVER_TEAL",
    "cyan": "TIP_OVER_TEAL",
    "xanh": "TIP_OVER_TEAL",
    "xanh ngọc": "TIP_OVER_TEAL",
    "orange": "OVERFIT_ORANGE",
    "cam": "OVERFIT_ORANGE",
    "yellow": "UNCANNY_YELLOW",
    "vàng": "UNCANNY_YELLOW",
    "lime": "NON_LINEAR_LIME",
    "blue": "SINGULARITY_SAPPHIRE",
    "sapphire": "SINGULARITY_SAPPHIRE",
    "xanh dương": "SINGULARITY_SAPPHIRE",
    "xanh lam": "SINGULARITY_SAPPHIRE",
    "purple": "FALSE_POSITIVE_PURPLE",
    "tím": "FALSE_POSITIVE_PURPLE",
    "green": "CONFUSION_MATRIX_GREEN",
    "xanh lá": "CONFUSION_MATRIX_GREEN",
    "rainbow": "RAINBOW_EYES",
    "cầu vồng": "RAINBOW_EYES",
    "red": "ROBOT_RED",
    "đỏ": "ROBOT_RED",
}

CYCLE = [
    "TIP_OVER_TEAL",
    "OVERFIT_ORANGE",
    "UNCANNY_YELLOW",
    "NON_LINEAR_LIME",
    "SINGULARITY_SAPPHIRE",
    "FALSE_POSITIVE_PURPLE",
    "CONFUSION_MATRIX_GREEN",
    "ROBOT_RED",
    "RAINBOW_EYES",
]


def resolve(name: str | None) -> str:
    raw = (name or "TIP_OVER_TEAL").strip()
    if raw.upper() == "CUSTOM":
        return "CUSTOM"
    key = raw.replace("COLOR_", "").replace("-", "_").replace(" ", "_").upper()
    if key in PRESETS:
        return key
    alias = ALIASES.get(raw.lower().strip())
    if alias:
        return alias
    return "TIP_OVER_TEAL"


def hsv(name: str | None, hue: float | None = None, sat: float | None = None) -> tuple[str, float, float, bool]:
    key = resolve(name)
    if key == "CUSTOM":
        h = 0.5 if hue is None else float(hue)
        s = 1.0 if sat is None else float(sat)
        return "CUSTOM", h, s, False
    h, s = PRESETS[key]
    if hue is not None:
        h = float(hue)
    if sat is not None:
        s = float(sat)
    return key, h, s, key == "RAINBOW_EYES"


def next_color(current: str | None) -> str:
    key = resolve(current)
    if key not in CYCLE:
        return CYCLE[0]
    return CYCLE[(CYCLE.index(key) + 1) % len(CYCLE)]


def hsv_to_rgb(h: float, s: float, v: float = 1.0) -> tuple[int, int, int]:
    h = h % 1.0
    i = int(h * 6)
    f = h * 6 - i
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    r, g, b = (
        (v, t, p),
        (q, v, p),
        (p, v, t),
        (p, q, v),
        (t, p, v),
        (v, p, q),
    )[i % 6]
    return int(r * 255), int(g * 255), int(b * 255)
