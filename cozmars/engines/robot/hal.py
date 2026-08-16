"""Robot HAL: Pi GPIO hoặc sim HTTP. Engine khác không import gpiozero."""

from __future__ import annotations

from typing import Any, Dict, Protocol


class Hal(Protocol):
    name: str

    def speed(self, left: float, right: float) -> None: ...
    def head(self, angle: float) -> None: ...
    def lift(self, height: float) -> None: ...
    def expression(self, name: str) -> None: ...
    def backlight(self, value: float) -> None: ...
    def speaker_power(self, on: bool) -> None: ...
    def sensors(self) -> Dict[str, Any]: ...
    def close(self) -> None: ...


def open_hal(kind: str, *, sim_url: str = "", conf: dict | None = None) -> Hal:
    kind = (kind or "auto").lower()
    if kind == "sim" or (kind == "auto" and sim_url):
        from .sim_hal import SimHal

        print(f"[ROBOT] HAL = sim  {sim_url}", flush=True)
        return SimHal(sim_url)
    if kind == "pi":
        from .pi_hal import PiHal

        print("[ROBOT] HAL = pi (gpiozero / PCA9685)", flush=True)
        return PiHal(conf or {})
    from .null_hal import NullHal

    print("[ROBOT] HAL = null (không phần cứng — chỉ log)", flush=True)
    return NullHal()
