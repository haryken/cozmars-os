"""Pi Zero 2W HAL — gpiozero + PCA9685. Import fail → log, không crash supervisor."""

from __future__ import annotations

from typing import Any, Dict


class PiHal:
    name = "pi"

    def __init__(self, conf: dict) -> None:
        self.conf = conf
        self.lmotor = self.rmotor = None
        self.head_servo = self.lift_l = self.lift_r = None
        self._ok = False
        try:
            from gpiozero import Motor  # type: ignore

            m = conf["motor"]
            self.lmotor = Motor(*m["left"])
            self.rmotor = Motor(*m["right"])
            self._ok = True
            print("[HAL] gpiozero Motor L/R ok", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[HAL] MISS gpiozero Motor — {exc}", flush=True)
        try:
            from .servokit import ServoKit  # local thin wrapper

            kit = ServoKit(channels=16, frequency=conf.get("servo", {}).get("freq", 60))
            sv = conf["servo"]
            self.head_servo = kit.servo[sv["head"]["channel"]]
            self.lift_l = kit.servo[sv["left_arm"]["channel"]]
            self.lift_r = kit.servo[sv["right_arm"]["channel"]]
            print("[HAL] PCA9685 servo kit ok", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[HAL] MISS PCA9685 — {exc}", flush=True)

    def speed(self, left: float, right: float) -> None:
        if not self.lmotor:
            print(f"[HAL] (no motor) L={left:.2f} R={right:.2f}", flush=True)
            return
        self.lmotor.value = max(-1.0, min(1.0, left))
        self.rmotor.value = max(-1.0, min(1.0, right))

    def head(self, angle: float) -> None:
        angle = max(-30.0, min(30.0, angle))
        if not self.head_servo:
            print(f"[HAL] (no servo) head {angle:.1f}°", flush=True)
            return
        # map −30…30 → 0…1 fraction of pulse range — firmware uses pulse us
        self.head_servo.angle = angle + 90  # SG90 mid

    def lift(self, height: float) -> None:
        height = max(0.0, min(1.0, height))
        if not self.lift_l:
            print(f"[HAL] (no servo) lift {height * 100:.0f}%", flush=True)
            return
        ang = height * 90
        self.lift_l.angle = ang
        self.lift_r.angle = ang

    def expression(self, name: str) -> None:
        print(f"[HAL] ST7789 expression {name} (anim vẽ frame)", flush=True)

    def backlight(self, value: float) -> None:
        print(f"[HAL] backlight ch15 {value:.2f}", flush=True)

    def speaker_power(self, on: bool) -> None:
        print(f"[HAL] speaker ch0 {int(bool(on))}", flush=True)

    def sensors(self) -> Dict[str, Any]:
        return {"sonarCm": 50.0, "inRange": False, "lir": 1, "rir": 1, "cliff": 1, "button": False}

    def close(self) -> None:
        self.speed(0, 0)
        for m in (self.lmotor, self.rmotor):
            if m:
                try:
                    m.close()
                except Exception:
                    pass
