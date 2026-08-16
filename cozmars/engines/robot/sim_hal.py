"""HAL client: OS process → Cozmars Sim HTTP (không GPIO)."""

from __future__ import annotations

import json
import queue
import threading
import urllib.error
import urllib.request
from typing import Any, Dict


class SimHal:
    name = "sim"

    def __init__(self, url: str) -> None:
        self.url = (url or "http://127.0.0.1:8088").rstrip("/")
        self._timeout = 0.35
        self._last: Dict[str, Any] = {}
        self._q: queue.Queue = queue.Queue(maxsize=96)
        self._alive = True
        threading.Thread(target=self._pump, name="sim-hal", daemon=True).start()

    def _sig(self, body: dict) -> Any:
        op = body.get("op")
        if op == "drive":
            return (round(float(body.get("left", 0)), 2), round(float(body.get("right", 0)), 2))
        if op == "head":
            return round(float(body.get("angle", 0)), 0)
        if op == "lift":
            return round(float(body.get("height", 0)), 2)
        if op == "expression":
            return str(body.get("name") or "")
        if op == "face":
            left = body.get("L") or []
            return (
                round(float(body.get("a") or 0), 2),
                round(float(body.get("cx") or 0), 1),
                round(float(body.get("cy") or 0), 1),
                round(float(body.get("sx") or 1), 2),
                tuple(round(float(left[i]), 2) if i < len(left) else 0.0 for i in (0, 2, 3, 4, 13, 16)),
            )
        if op == "eye_color":
            return (str(body.get("name") or ""), round(float(body.get("hue") or 0), 3), bool(body.get("rainbow")))
        if op == "backlight":
            return round(float(body.get("value", 0)), 2)
        if op == "speaker":
            return bool(body.get("on"))
        return None

    def _post(self, body: dict) -> None:
        body = {**body, "source": "os"}
        op = str(body.get("op") or "")
        sig = self._sig(body)
        if sig is not None and self._last.get(op) == sig:
            return
        if sig is not None:
            self._last[op] = sig
        try:
            self._q.put_nowait(body)
        except queue.Full:
            pass

    def _pump(self) -> None:
        while self._alive:
            try:
                body = self._q.get(timeout=0.2)
            except queue.Empty:
                continue
            if body is None:
                return
            data = json.dumps(body).encode("utf-8")
            req = urllib.request.Request(
                self.url + "/api/cmd",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                    resp.read()
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                print(f"[HAL] sim POST fail {body.get('op')}: {exc}", flush=True)

    def speed(self, left: float, right: float) -> None:
        self._post({"op": "drive", "left": left, "right": right})

    def head(self, angle: float) -> None:
        self._post({"op": "head", "angle": angle})

    def lift(self, height: float) -> None:
        self._post({"op": "lift", "height": height})

    def expression(self, name: str) -> None:
        self._post({"op": "expression", "name": name})

    def face(self, frame: dict) -> None:
        self._post({"op": "face", **(frame or {})})

    def eye_color(self, name: str, hue: float, sat: float, rainbow: bool) -> None:
        self._post(
            {
                "op": "eye_color",
                "name": name,
                "hue": float(hue),
                "sat": float(sat),
                "rainbow": bool(rainbow),
            }
        )

    def backlight(self, value: float) -> None:
        self._post({"op": "backlight", "value": value})

    def speaker_power(self, on: bool) -> None:
        self._post({"op": "speaker", "on": bool(on)})

    def sensors(self) -> Dict[str, Any]:
        extra = {}
        try:
            with urllib.request.urlopen(self.url + "/api/state", timeout=self._timeout) as resp:
                snap = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            print(f"[HAL] sim GET fail: {exc}", flush=True)
            return {"sonarCm": 50.0, "inRange": False, "lir": 1, "rir": 1, "cliff": 1, "button": False}
        s = snap.get("sensors") or {}
        extra["osIntent"] = (snap.get("software") or {}).get("osIntent")
        extra["osCmd"] = (snap.get("software") or {}).get("osCmd")
        extra["ctrlAssumed"] = bool((snap.get("software") or {}).get("ctrlAssumed"))
        return {
            "sonarCm": s.get("sonarCm", 50.0),
            "inRange": bool(s.get("inRange")),
            "lir": s.get("lir", 1),
            "rir": s.get("rir", 1),
            "cliff": s.get("cliff", 1),
            "button": bool(s.get("button")),
            **extra,
        }

    def close(self) -> None:
        self._alive = False
        try:
            self._q.put_nowait(None)
        except queue.Full:
            pass
        self.speed(0, 0)
        self.head(0)
        self.lift(0)
