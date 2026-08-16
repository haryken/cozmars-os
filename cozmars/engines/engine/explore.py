"""Khám phá kiểu Vector Exploring (behaviorExploring.cpp).

Chu kỳ: get-in → drive ~0.3–0.5 m → look → (huh nếu sonar) → lặp.
SFX chỉ khi cảm biến: vực (IR), vật cản mới (sonar cạnh lên). Không SFX theo đồng hồ DRIVE/LOOK.
"""

from __future__ import annotations

import math
import random
import time


class Explore:
    def __init__(self, robot, anim=None, mood=None) -> None:
        self.robot = robot
        self.anim = anim
        self.mood = mood
        self.phase = "idle"
        self._t0 = 0.0
        self._dur = 0.0
        self._turn = 1.0
        self._curve = 0.0
        self._last_face = ""
        self._drive_n = 0
        self._stim_t = 0.0
        self._was_range = False

    def start(self) -> None:
        if self.mood:
            self.mood.event("explore_start")
        self._begin("get_in", 1.7)
        self._drive_n = 0
        self._was_range = False
        self._face()
        print(f"[ENGINE] explore GET-IN  stim={self._stim():.2f} happy={self._happy():.2f}", flush=True)

    def tick(self, _t: float, sensors: dict) -> None:
        now = time.monotonic()
        dt = 0.05
        if self.mood:
            self.mood.decay(dt, exploring=True)
        in_range = bool(sensors.get("inRange"))
        if in_range and self.phase not in ("examine", "escape", "cliff_hold"):
            self._begin_examine(sfx=not self._was_range)
            self._was_range = True
            return
        self._was_range = in_range

        elapsed = now - self._t0
        if self.phase == "get_in":
            self.robot.speed(0.0, 0.0)
            self.robot.head(16 * math.sin(elapsed * 3.2))
            self.robot.lift(0.12 + 0.18 * abs(math.sin(elapsed * 2.4)))
            if elapsed >= self._dur:
                self._begin_drive()
        elif self.phase == "drive":
            if self.mood:
                self.mood.stimulated = min(1.0, self.mood.stimulated + 0.07 * dt)
            base = 0.62
            self.robot.speed(base + self._curve, base - self._curve)
            self.robot.head(10 * math.sin(elapsed * 1.3))
            self.robot.lift(0.08)
            if elapsed >= self._dur:
                self._begin_look()
        elif self.phase == "look":
            s = 0.42 * self._turn
            self.robot.speed(-s, s)
            self.robot.head(18 * math.sin(elapsed * 2.0))
            if elapsed >= self._dur:
                self._after_look()
        elif self.phase == "examine":
            self.robot.speed(0.0, 0.0)
            self.robot.head(22 if int(elapsed * 4) % 2 == 0 else -8)
            self.robot.lift(0.35)
            if elapsed >= self._dur:
                self._begin_escape()
        elif self.phase == "escape":
            if self._turn > 0:
                self.robot.speed(-0.22, 0.48)
            else:
                self.robot.speed(0.48, -0.22)
            self.robot.head(8)
            if elapsed >= self._dur:
                self._begin_drive()
        elif self.phase == "cliff_hold":
            pass
        else:
            self._begin_drive()
        self._face(throttle=True)
        self._stim_light()

    def _begin(self, phase: str, dur: float) -> None:
        self.phase = phase
        self._t0 = time.monotonic()
        self._dur = dur

    def _begin_drive(self) -> None:
        self._drive_n += 1
        self._curve = random.uniform(-0.16, 0.16)
        # Vector maxSearchRadius 0.5 m; sim v≈0.10 m/s @ motor 0.62 → 1.8–4.2 s
        self._begin("drive", random.uniform(1.8, 4.2))
        print(
            f"[ENGINE] explore DRIVE #{self._drive_n} {self._dur:.1f}s  stim={self._stim():.2f}",
            flush=True,
        )

    def _begin_look(self) -> None:
        if self.mood:
            self.mood.event("look_around")
        self._turn = 1.0 if random.random() > 0.5 else -1.0
        # 45–140° @ ~90°/s → 0.6–1.8 s
        self._begin("look", random.uniform(0.7, 1.8))
        print(f"[ENGINE] explore LOOK  stim={self._stim():.2f}", flush=True)

    def _after_look(self) -> None:
        self.robot.speed(0.0, 0.0)
        self._begin_drive()

    def _begin_examine(self, *, sfx: bool = False) -> None:
        if self.mood:
            self.mood.event("examine_obstacle")
        self._begin("examine", 1.15)
        if sfx:
            self._sfx("explore_huh")
        if self.anim:
            self.anim.set_expression("surprised")
        print(f"[ENGINE] explore HUH obstacle  stim={self._stim():.2f}", flush=True)

    def notify_cliff(self, side: str) -> None:
        self.phase = "cliff_hold"
        self._t0 = time.monotonic()
        print(f"[ENGINE] explore nhường CLIFF {side}", flush=True)

    def after_cliff(self, side: str) -> None:
        self._turn = -1.0 if side == "left" else 1.0
        self._begin_escape(keep_turn=True)
        print(f"[ENGINE] explore sau cliff → escape {side}", flush=True)

    def _begin_escape(self, keep_turn: bool = False) -> None:
        if not keep_turn or self._turn == 0:
            self._turn = 1.0 if random.random() > 0.5 else -1.0
        self._begin("escape", random.uniform(0.7, 1.2))

    def _cliff(self) -> None:
        self.notify_cliff("both")

    def _sfx(self, action: str) -> None:
        if not self.anim:
            return
        if self._stim() >= 0.45 and action in ("explore", "look_around"):
            self.anim.play_mood(action, self._stim(), tag="sys")
        else:
            self.anim.play_action(action, tag="sys")

    def _mood_sfx(self, kind: str) -> None:
        if self.anim:
            self.anim.play_mood(kind, self._stim(), tag="emote")

    def _face(self, throttle: bool = False) -> None:
        if not self.anim or not self.mood:
            return
        name = self.mood.face(exploring=True)
        if throttle and name == self._last_face:
            return
        self._last_face = name
        self.anim.set_expression(name)

    def _stim_light(self) -> None:
        now = time.monotonic()
        if now - self._stim_t < 0.35:
            return
        self._stim_t = now
        try:
            self.robot.backlight(0.42 + 0.58 * self._stim())
        except Exception:
            pass
        hal = getattr(self.robot, "hal", None)
        if hal is not None and hasattr(hal, "_post"):
            try:
                hal._post({"op": "stim", "value": round(self._stim(), 3)})
            except Exception:
                pass

    def _stim(self) -> float:
        return float(getattr(self.mood, "stimulated", 0.2) or 0.2)

    def _happy(self) -> float:
        return float(getattr(self.mood, "happy", 0.4) or 0.4)
