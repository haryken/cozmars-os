"""Cliff 2 IR trước dưới đít (GPIO 12/16). Vector ReactToCliff rút gọn — không mắt sau."""

from __future__ import annotations

import time


def flags(sensors: dict) -> tuple[bool, bool]:
    """True = hụt sàn (vực). gpiozero LineSensor pull_up: 0 = no reflection."""
    left = int(sensors.get("lir", 1)) == 0
    right = int(sensors.get("rir", 1)) == 0
    if int(sensors.get("cliff", 1)) == 0 and not left and not right:
        left = right = True
    return left, right


def should_stop(sensors: dict, enabled: bool) -> bool:
    if not enabled:
        return False
    left, right = flags(sensors)
    return left or right


class CliffReactor:
    """Dừng → (lùi ngắn nếu đang đi tới) → rẽ khỏi IR đang hụt. Pickup: cả 2=0 lúc đứng."""

    debounce_s = 0.07
    backup_s = 0.55
    turn_s = 0.85

    def __init__(self, robot, anim=None, mood=None) -> None:
        self.robot = robot
        self.anim = anim
        self.mood = mood
        self.phase = "idle"
        self.side = "none"  # left | right | both | pickup
        self.owning = False
        self.just_started = False
        self._t0 = 0.0
        self._seen = 0  # bit0 left, bit1 right
        self._sfx = False
        self._was_fwd = False

    def tick(self, sensors: dict, enabled: bool) -> bool:
        self.just_started = False
        if not enabled:
            if self.phase != "idle":
                self.phase = "idle"
                self.robot.stop()
            self.owning = False
            return False

        left, right = flags(sensors)
        hole = left or right
        now = time.monotonic()

        if self.phase == "idle":
            if not hole:
                self.owning = False
                return False
            self.phase = "debounce"
            self._t0 = now
            self._seen = (1 if left else 0) | (2 if right else 0)
            self._was_fwd = self._going_forward()
            self.robot.stop()
            self.owning = True
            return True

        if hole:
            self._seen |= (1 if left else 0) | (2 if right else 0)

        if self.phase == "debounce":
            self.robot.stop()
            if not hole and (now - self._t0) < self.debounce_s:
                self.phase = "idle"
                self.owning = False
                return False
            if now - self._t0 >= self.debounce_s:
                both = bool(self._seen & 1) and bool(self._seen & 2)
                if both and not self._was_fwd:
                    self._start("pickup", pickup=True)
                else:
                    self._start("backup" if self._was_fwd else "turn")
            return True

        if self.phase == "pickup":
            self.robot.stop()
            self.robot.lift(0.35)
            if not hole and (now - self._t0) > 0.25:
                print("[CLIFF] pickup xong — lại có sàn", flush=True)
                self.phase = "idle"
                self.owning = False
                return False
            return True

        if self.phase == "backup":
            self.robot.speed(-0.42, -0.42)
            self.robot.lift(0.45)
            if now - self._t0 >= self.backup_s:
                self._t0 = now
                self.phase = "turn"
                print(f"[CLIFF] rẽ tránh {self.side}", flush=True)
            return True

        if self.phase == "turn":
            if self.side == "left":
                self.robot.speed(0.45, -0.45)
            elif self.side == "right":
                self.robot.speed(-0.45, 0.45)
            else:
                self.robot.speed(-0.42, 0.42)
            self.robot.head(12)
            if now - self._t0 >= self.turn_s or not hole:
                self.robot.stop()
                self.phase = "idle"
                self.owning = False
                print("[CLIFF] xong — trả não", flush=True)
                return False
            return True

        self.owning = False
        return False

    def _start(self, phase: str, pickup: bool = False) -> None:
        self.just_started = True
        self._t0 = time.monotonic()
        self._sfx = False
        if pickup:
            self.side = "pickup"
            self.phase = "pickup"
            print("[CLIFF] pickup — cả 2 IR hụt sàn, không lùi", flush=True)
        else:
            if self._seen == 1:
                self.side = "left"
            elif self._seen == 2:
                self.side = "right"
            else:
                self.side = "both"
            self.phase = phase
            print(f"[CLIFF] ReactToCliff {self.side} → {phase}", flush=True)
        if self.mood:
            self.mood.event("cliff")
        if self.anim:
            self.anim.from_action("cliff")
            self.anim.set_expression("sad")

    def _going_forward(self) -> bool:
        l = float(getattr(self.robot, "last_left", 0.0) or 0.0)
        r = float(getattr(self.robot, "last_right", 0.0) or 0.0)
        return (l + r) > 0.12
