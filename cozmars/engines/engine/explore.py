from __future__ import annotations

import math


class Explore:
    """Freeplay tới-lui — sonar/IR do brain chặn trước."""

    def __init__(self, robot) -> None:
        self.robot = robot

    def tick(self, t: float, sensors: dict) -> None:
        if sensors.get("inRange") or int(sensors.get("cliff", 1)) == 0:
            self.robot.speed(-0.25, 0.45)
            return
        wobble = 0.14 * math.sin(t * 0.7)
        self.robot.speed(0.42 + wobble, 0.42 - wobble)
        self.robot.head(8 * math.sin(t * 1.1))
