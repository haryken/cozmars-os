"""Dispatch animation names từ SDK cũ."""

from __future__ import annotations

NAMES = ("search for cube", "center cube", "aim at cube", "dock with cube", "pick up cube")


def animate(brain, name: str) -> None:
    print(f"[ANIMATION] {name}", flush=True)
    if "cube" in name:
        print("[ANIMATION] cube pipeline cần camera+cv2", flush=True)
