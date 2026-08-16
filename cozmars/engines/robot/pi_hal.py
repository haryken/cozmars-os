"""Pi Zero 2W HAL — gpiozero + PCA9685. Import fail → log, không crash supervisor."""

from __future__ import annotations

from typing import Any, Dict


class PiHal:
    name = "pi"

    def __init__(self, conf: dict) -> None:
        self.conf = conf
        self.lmotor = self.rmotor = None
        self.head_servo = self.lift_l = self.lift_r = None
        self.lir = self.rir = None
        self.sonar = None
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
        ir = conf.get("ir") or {}
        try:
            from gpiozero import LineSensor  # type: ignore

            lg, rg = int(ir.get("left", 12)), int(ir.get("right", 16))
            self.lir = LineSensor(lg, queue_len=3, sample_rate=10, pull_up=True)
            self.rir = LineSensor(rg, queue_len=3, sample_rate=10, pull_up=True)
            print(f"[HAL] LineSensor cliff/floor GPIO {lg}/{rg} (1=sàn 0=vực)", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[HAL] MISS LineSensor IR — {exc}", flush=True)
        sonar_cfg = conf.get("sonar") or {}
        try:
            from .firmware.distance_sensor import DistanceSensor

            self.sonar = DistanceSensor(
                trigger=int(sonar_cfg.get("trigger", 26)),
                echo=int(sonar_cfg.get("echo", 13)),
                max_distance=float(sonar_cfg.get("max", 0.5)),
                threshold_distance=float(sonar_cfg.get("threshold", 0.1)),
            )
            print("[HAL] sonar HC-SR04 ok", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[HAL] MISS sonar — {exc}", flush=True)

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
        self.head_servo.angle = angle + 90

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

    def face(self, frame: dict) -> None:
        pass

    def eye_color(self, name: str, hue: float, sat: float, rainbow: bool) -> None:
        print(f"[HAL] eye color {name} hue={hue:.2f} rainbow={int(rainbow)}", flush=True)

    def backlight(self, value: float) -> None:
        print(f"[HAL] backlight ch15 {value:.2f}", flush=True)

    def speaker_power(self, on: bool) -> None:
        print(f"[HAL] speaker ch0 {int(bool(on))}", flush=True)

    def sensors(self) -> Dict[str, Any]:
        lir = _line_val(self.lir)
        rir = _line_val(self.rir)
        dist_m = 0.5
        if self.sonar is not None:
            try:
                dist_m = float(getattr(self.sonar, "distance", None) or 0.5)
            except Exception:
                dist_m = 0.5
        thr = float((self.conf.get("sonar") or {}).get("threshold", 0.1))
        return {
            "sonarCm": dist_m * 100.0,
            "inRange": dist_m < thr,
            "lir": lir,
            "rir": rir,
            "cliff": 0 if (lir == 0 or rir == 0) else 1,
            "button": False,
        }

    def close(self) -> None:
        self.speed(0, 0)
        for obj in (self.lmotor, self.rmotor, self.lir, self.rir, self.sonar):
            if obj is None:
                continue
            try:
                obj.close()
            except Exception:
                pass


def _line_val(sensor) -> int:
    """gpiozero LineSensor pull_up: 1 = phản xạ (sàn), 0 = không (vực)."""
    if sensor is None:
        return 1
    try:
        v = sensor.value
    except Exception:
        return 1
    if v is None:
        return 1
    return 1 if float(v) >= 0.5 else 0
