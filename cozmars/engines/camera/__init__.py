"""CSI + decode. Sim: lấy JPEG/PNG từ dashboard. Pi: picamera/picamera2."""

from __future__ import annotations

import os
import urllib.request


class CameraEngine:
    name = "camera"

    def __init__(self, sim_url: str = "") -> None:
        self.sim_url = (sim_url or os.environ.get("COZMARS_SIM_URL", "")).rstrip("/")
        self.backend = None
        if self.sim_url:
            self.backend = "sim-http"
            print(f"[CAMERA] sim frames {self.sim_url}/api/camera.png", flush=True)
            return
        for mod in ("picamera2", "picamera"):
            try:
                __import__(mod)
                self.backend = mod
                print(f"[CAMERA] backend {mod}", flush=True)
                break
            except Exception as exc:  # noqa: BLE001
                print(f"[CAMERA] MISS {mod} — {exc}", flush=True)
        if not self.backend:
            print("[CAMERA] không CSI", flush=True)

    def capture(self, **_opts) -> bytes:
        if self.backend == "sim-http":
            try:
                with urllib.request.urlopen(self.sim_url + "/api/camera.png", timeout=1.5) as resp:
                    return resp.read()
            except Exception as exc:  # noqa: BLE001
                print(f"[CAMERA] sim frame fail: {exc}", flush=True)
                return b""
        return b""
