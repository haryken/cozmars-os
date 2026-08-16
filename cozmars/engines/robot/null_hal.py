from __future__ import annotations

from typing import Any, Dict


class NullHal:
    name = "null"

    def __init__(self) -> None:
        self._s: Dict[str, Any] = {
            "sonarCm": 50.0,
            "inRange": False,
            "lir": 1,
            "rir": 1,
            "cliff": 1,
            "button": False,
        }

    def speed(self, left: float, right: float) -> None:
        print(f"[HAL] speed L={left:.2f} R={right:.2f}", flush=True)

    def head(self, angle: float) -> None:
        print(f"[HAL] head {angle:.1f}°", flush=True)

    def lift(self, height: float) -> None:
        print(f"[HAL] lift {height * 100:.0f}%", flush=True)

    def expression(self, name: str) -> None:
        print(f"[HAL] expression {name}", flush=True)

    def backlight(self, value: float) -> None:
        print(f"[HAL] backlight {value:.2f}", flush=True)

    def speaker_power(self, on: bool) -> None:
        print(f"[HAL] speaker_power {int(bool(on))}", flush=True)

    def sensors(self) -> Dict[str, Any]:
        return dict(self._s)

    def close(self) -> None:
        self.speed(0, 0)
