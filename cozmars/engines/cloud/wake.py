"""Wake: nút GPIO 4 + energy mic. Earcon giống Vector (file wav khi có)."""

from __future__ import annotations


def earcon(source: str, anim=None) -> None:
    print(f"[WAKE] earcon source={source}", flush=True)
    if anim is not None:
        anim.play_action("wake")
