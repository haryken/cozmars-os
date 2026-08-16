"""Anim: mắt + mixer SFX. OpenCV optional; sim nhận expression qua HAL."""

from __future__ import annotations

import io
import json
import os
import random
import subprocess
import tempfile
import threading
import wave
from pathlib import Path

from . import synth
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
        n_wav = len(list((ROOT / "assets" / "sfx").glob("*.wav")))
        print(
            f"[ANIM] sfx catalog {len(self._catalog)}  actions {len(self._action)}  "
            f"wav={n_wav}  (thiếu file → synth + đẩy loa sim)",
            flush=True,
        )
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
            if action in self._catalog:
                evs = [action]
        if not evs:
            return
        ev = random.choice(evs)
        self.play_sfx(ev)

    def play_mood(self, kind: str, stim: float = 0.0) -> None:
        """SFX vui/buồn/curious — bản *_Stim khi stimulation cao (như Vector)."""
        high = stim >= 0.45
        mapping = {
            "happy": (
                "Play__Robot_Vic_Sfx__Emote_Happy_Short_Stim"
                if high
                else "Play__Robot_Vic_Sfx__Emote_Happy_Short"
            ),
            "sad": (
                "Play__Robot_Vic_Sfx__Emote_Sad_Short_Stim"
                if high
                else "Play__Robot_Vic_Sfx__Emote_Sad_Short"
            ),
            "curious": (
                "Play__Robot_Vic_Sfx__Emote_Curious_Short_Stim"
                if high
                else "Play__Robot_Vic_Sfx__Emote_Curious_Short"
            ),
            "look_around": "Play__Robot_Vic_Sfx__Gazing_Scan",
            "explore": (
                "Play__Robot_Vic_Sfx__Tread_Happy_Long" if high else "Play__Robot_Vic_Sfx__Tread_Happy"
            ),
            "huh": "Play__Robot_Vic_Sfx__Emote_Curious_Long",
            "explore_huh": "Play__Robot_Vic_Sfx__Emote_Curious_Long",
        }
        ev = mapping.get(kind)
        if ev:
            self.play_sfx(ev)
            return
        self.play_action(kind)

    def play_sfx(self, event_name: str) -> None:
        if self.volume <= 0.01:
            return
        wav_name = self._catalog.get(event_name, event_name if event_name.endswith(".wav") else event_name + ".wav")
        path = ROOT / "assets" / "sfx" / wav_name
        src = "file"
        data = self._audible_wav(path)
        if not data:
            src = "synth"
            data = synth.render(event_name, self.volume)
        print(f"[ANIM] SFX {event_name} ({src} {len(data)}B)", flush=True)
        self.robot.speaker_power(True)
        threading.Thread(target=self._mix, args=(event_name, data), daemon=True).start()

    def _audible_wav(self, path: Path) -> bytes:
        """Bỏ placeholder im lặng (peak=0, ~5 KB) — dùng synth."""
        if not path.exists() or path.stat().st_size < 64:
            return b""
        try:
            data = path.read_bytes()
            with wave.open(io.BytesIO(data), "rb") as w:
                frames = w.readframes(w.getnframes())
            peak = 0
            for i in range(0, min(len(frames), 8000) - 1, 2):
                v = abs(int.from_bytes(frames[i : i + 2], "little", signed=True))
                if v > peak:
                    peak = v
                if peak > 200:
                    return data
        except Exception:
            return b""
        return b""

    def _mix(self, event_name: str, data: bytes) -> None:
        with self._lock:
            try:
                self._to_speaker(event_name, data)
            except Exception as exc:  # noqa: BLE001
                print(f"[ANIM] mix fail {event_name}: {exc}", flush=True)

    def _to_speaker(self, event_name: str, data: bytes) -> None:
        sim = os.environ.get("COZMARS_SIM_URL", "").rstrip("/")
        if not sim:
            sim = str(getattr(getattr(self.robot, "hal", None), "url", "") or "").rstrip("/")
        if sim:
            os.environ.setdefault("COZMARS_SIM_URL", sim)
            from cozmars.engines.cloud.google_tts import play_bytes

            play_bytes(event_name, data, mime="audio/wav", lang="sfx", kind="sfx")
            return
        self._aplay(data)

    def _aplay(self, data: bytes) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
            tmp.write(data)
            tmp.flush()
            try:
                subprocess.run(["aplay", "-q", tmp.name], check=False, timeout=8)
            except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
                print(f"[ANIM] aplay skip: {exc}", flush=True)
