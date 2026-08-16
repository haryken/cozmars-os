"""Wake: nút GPIO 4 + energy mic. Earcon giống Vector (file wav khi có)."""

from __future__ import annotations


def earcon(source: str) -> None:
    print(f"[WAKE] earcon source={source}  (SFX On — thiếu wav thì chỉ log)", flush=True)
