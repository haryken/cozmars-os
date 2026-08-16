from __future__ import annotations

from typing import Any, Dict

from .hal import Hal, open_hal


class RobotEngine:
    """vic-robot: sở hữu motor / servo / cảm biến."""

    name = "robot"

    def __init__(self, hal: Hal) -> None:
        self.hal = hal
        self.last_left = 0.0
        self.last_right = 0.0
        self.listening = False

    def speed(self, left: float, right: float) -> None:
        self.last_left = left
        self.last_right = right
        self.hal.speed(left, right)

    def head(self, angle: float) -> None:
        self.hal.head(max(-30.0, min(30.0, angle)))

    def lift(self, height: float) -> None:
        self.hal.lift(max(0.0, min(1.0, height)))

    def expression(self, name: str) -> None:
        self.hal.expression(name)

    def sensors(self) -> Dict[str, Any]:
        return self.hal.sensors()

    def stop(self) -> None:
        self.last_left = 0.0
        self.last_right = 0.0
        self.hal.speed(0, 0)

    def speaker_power(self, on: bool) -> None:
        self.hal.speaker_power(on)

    def backlight(self, value: float) -> None:
        self.hal.backlight(value)

    def close(self) -> None:
        self.hal.close()


def build(kind: str, sim_url: str, conf: dict) -> RobotEngine:
    return RobotEngine(open_hal(kind, sim_url=sim_url, conf=conf))
