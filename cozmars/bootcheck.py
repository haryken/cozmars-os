"""Probe Python libraries. Missing ones are logged, never crash boot."""

from __future__ import annotations

import importlib
import sys
from typing import List, Tuple

REQUIRED: List[Tuple[str, str]] = [
    ("json", "stdlib"),
    ("asyncio", "stdlib"),
    ("urllib.request", "stdlib HAL sim"),
]

OPTIONAL: List[Tuple[str, str]] = [
    ("gpiozero", "Pi HAL: motor N20, IR, nút GPIO"),
    ("board", "Pi HAL: PCA9685 / ST7789 (Blinka)"),
    ("digitalio", "Pi HAL: SPI màn hình"),
    ("adafruit_rgb_display.st7789", "Pi HAL: ST7789 240×135"),
    ("adafruit_motor.servo", "Pi HAL: servo kit"),
    ("numpy", "mắt OpenCV / camera decode"),
    ("cv2", "mắt 80×80 + ArUco"),
    ("sounddevice", "I2S INMP441 / MAX98357"),
    ("picamera", "CSI OV5647 (Bullseye)"),
    ("picamera2", "CSI OV5647 (Bookworm)"),
    ("sanic", "web :80 firmware-style"),
    ("aiohttp", "web / RPC phụ"),
    ("vosk", "STT offline English small"),
    ("wsmprpc", "RPC ws://IP/rpc"),
]


def _try(mod: str) -> Tuple[bool, str]:
    try:
        importlib.import_module(mod)
        return True, "ok"
    except Exception as exc:  # noqa: BLE001 — want any import failure
        return False, f"{type(exc).__name__}: {exc}"


def report() -> dict:
    missing: list[dict] = []
    rows: list[dict] = []
    print(f"[DEPS] python {sys.version.split()[0]}  {sys.executable}", flush=True)
    for mod, why in REQUIRED + OPTIONAL:
        kind = "required" if (mod, why) in REQUIRED else "optional"
        ok, err = _try(mod)
        rows.append({"mod": mod, "ok": ok, "kind": kind, "why": why, "error": None if ok else err})
        tag = "OK  " if ok else "MISS"
        extra = "" if ok else f"  ({err})"
        print(f"[DEPS] {tag} {mod:28s} {why}{extra}", flush=True)
        if not ok:
            missing.append({"mod": mod, "kind": kind, "why": why, "error": err})
    req_fail = [m for m in missing if m["kind"] == "required"]
    print(
        f"[DEPS] summary  required_fail={len(req_fail)}  optional_miss={len(missing) - len(req_fail)}",
        flush=True,
    )
    return {"python": sys.version.split()[0], "missing": missing, "rows": rows}


def main() -> int:
    info = report()
    return 1 if any(m["kind"] == "required" for m in info["missing"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
