"""Anim: mắt + mixer SFX. OpenCV optional; sim nhận expression qua HAL."""

from __future__ import annotations

import json
import random
import threading
import wave
from pathlib import Path

from .expression_map import expression_for

ROOT = Path(__file__).resolve().parents[3]
CATALOG = Path(__file__).with_name("sfx_catalog.json")
ACTION = Path(__file__).with_name("action_sfx.json")


class AnimEngine:
    name = "anim"

    def __init__(self, robot) -> None:
        self.robot = robot
        self.expression = "auto"
        self._catalog = json.loads(CATALOG.read_text(encoding="utf-8")) if CATALOG.exists() else {}
        self._action = json.loads(ACTION.read_text(encoding="utf-8")) if ACTION.exists() else {}
        self._lock = threading.Lock()
        self.volume = 0.8
        print(f"[ANIM] sfx catalog {len(self._catalog)}  actions {len(self._action)}", flush=True)
        self._try_opencv()

    def _try_opencv(self) -> None:
        try:
            import cv2  # noqa: F401
            import numpy  # noqa: F401

            print("[ANIM] OpenCV+numpy OK — mắt 80×80 có thể vẽ trên Pi", flush=True)
            self.cv = True
        except Exception as exc:  # noqa: BLE001
            print(f"[ANIM] mắt HAL expression (MISS cv2/numpy: {exc})", flush=True)
            self.cv = False

    def set_expression(self, name: str, color=None) -> None:
        self.expression = name
        self.robot.expression(name)
        print(f"[ANIM] eyes {name}", flush=True)

    def from_action(self, action: str) -> None:
        self.set_expression(expression_for(action))
        self.play_action(action)

    def play_action(self, action: str) -> None:
        evs = self._action.get(action) or []
        if not evs:
            # treat as event name
            if action in self._catalog:
                evs = [action]
        if not evs:
            return
        ev = random.choice(evs)
        self.play_sfx(ev)

    def play_sfx(self, event_name: str) -> None:
        wav_name = self._catalog.get(event_name, event_name if event_name.endswith(".wav") else event_name + ".wav")
        path = ROOT / "assets" / "sfx" / wav_name
        if not path.exists():
            print(f"[ANIM] SFX missing {wav_name} — {event_name}", flush=True)
            return
        print(f"[ANIM] SFX {event_name} → {path.name}", flush=True)
        self.robot.speaker_power(True)
        threading.Thread(target=self._mix, args=(path,), daemon=True).start()

    def _mix(self, path: Path) -> None:
        with self._lock:
            try:
                with wave.open(str(path), "rb") as w:
                    n = w.getnframes()
                    _ = w.readframes(n)
            except Exception as exc:  # noqa: BLE001
                print(f"[ANIM] mix fail {path.name}: {exc}", flush=True)
