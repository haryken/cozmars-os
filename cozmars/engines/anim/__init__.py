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
from . import eye_color as eye_color_mod
from . import procedural_face
from .expression_map import expression_for

ROOT = Path(__file__).resolve().parents[3]
CATALOG = Path(__file__).with_name("sfx_catalog.json")
ACTION = Path(__file__).with_name("action_sfx.json")

# Scan/tread/huh lúc khám phá — lặp mỗi 2–4s, dễ khó chịu. Wake/show không mute.
DEFAULT_MUTE = ("Gazing_Scan",)
SYS_ACTIONS = frozenset(
    {"explore", "look_around", "explore_huh", "explore_scan", "obstacle", "cliff", "idle"}
)
WAKE_ACTIONS = frozenset({"wake", "wake_fail", "boot"})
SHOW_ACTIONS = frozenset({"firetruck", "dance", "fistbump", "hello", "nod"})


def sfx_tag(event: str, action: str | None = None) -> str:
    a = action or ""
    e = event or ""
    if a in WAKE_ACTIONS or "Wake_Word" in e:
        return "wake"
    if a in SHOW_ACTIONS or "Distress_Alert" in e or "Fist_Bump" in e or "Codelab_Firetruck" in e:
        return "show"
    if a in SYS_ACTIONS or "Gazing_Scan" in e or "Tread_" in e:
        return "sys"
    if "Eye_Color" in e:
        return "emote"
    if "Emote_" in e:
        return "emote"
    return "sfx"


class AnimEngine:
    name = "anim"

    def __init__(self, robot, env: dict | None = None) -> None:
        self.robot = robot
        self.env = env or {}
        self.expression = "auto"
        self.eye_color_name = "TIP_OVER_TEAL"
        self._catalog = json.loads(CATALOG.read_text(encoding="utf-8")) if CATALOG.exists() else {}
        self._action = json.loads(ACTION.read_text(encoding="utf-8")) if ACTION.exists() else {}
        self._lock = threading.Lock()
        self.volume = 0.8
        extra: list[str] = []
        if env and "sfx_mute" in env:
            if isinstance(env.get("sfx_mute"), list):
                extra = [str(x) for x in env["sfx_mute"] if x]
        else:
            extra = list(DEFAULT_MUTE)
        env_csv = os.environ.get("COZMARS_SFX_MUTE", "")
        if env_csv.strip():
            extra.extend(p.strip() for p in env_csv.split(",") if p.strip())
        self._mute = tuple(dict.fromkeys(extra))
        n_wav = len(list((ROOT / "assets" / "sfx").glob("*.wav")))
        print(
            f"[ANIM] sfx catalog {len(self._catalog)}  actions {len(self._action)}  "
            f"wav={n_wav}  (thiếu file → synth + đẩy loa sim)",
            flush=True,
        )
        print(
            f"[ANIM] SFX nhãn [sys]=khám phá [wake]=đánh thức [show]=xe/nhảy [emote]=cảm xúc  "
            f"mute={list(self._mute)}",
            flush=True,
        )
        self._try_opencv()
        boot = str(self.env.get("eye_color") or "TIP_OVER_TEAL")
        hue = self.env.get("eye_hue")
        sat = self.env.get("eye_sat")
        self.set_eye_color(
            boot,
            hue=None if hue is None else float(hue),
            sat=None if sat is None else float(sat),
            play=False,
        )

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
        face = procedural_face.named(name)
        if color:
            self.set_eye_color(str(color), play=False)
        self.robot.expression(name)
        self.robot.face(face)
        print(f"[ANIM] eyes {name}", flush=True)

    def set_face(self, frame: dict) -> None:
        face = procedural_face.from_keyframe(frame)
        self.robot.face(face)

    def set_eye_color(
        self,
        name: str,
        *,
        hue: float | None = None,
        sat: float | None = None,
        play: bool = True,
    ) -> str:
        key, h, s, rainbow = eye_color_mod.hsv(name, hue, sat)
        self.eye_color_name = key
        self.env["eye_color"] = key
        self.env["eye_hue"] = h
        self.env["eye_sat"] = s
        self.robot.eye_color(key, h, s, rainbow)
        rgb = eye_color_mod.hsv_to_rgb(h, s)
        print(
            f"[ANIM] eye color {key}  hue={h:.2f} sat={s:.2f} rgb={rgb}"
            f"{' rainbow' if rainbow else ''}",
            flush=True,
        )
        if play:
            try:
                from cozmars.config import save_env

                save_env(self.env)
            except Exception:
                pass
            self.play_action("eye_color")
        return key

    def cycle_eye_color(self) -> str:
        nxt = eye_color_mod.next_color(self.eye_color_name)
        return self.set_eye_color(nxt)

    def from_action(self, action: str) -> None:
        self.set_expression(expression_for(action))
        self.play_action(action)

    def play_action(self, action: str, tag: str | None = None) -> None:
        evs = self._action.get(action) or []
        if not evs:
            if action in self._catalog:
                evs = [action]
        if not evs:
            return
        ev = random.choice(evs)
        self.play_sfx(ev, tag=tag or sfx_tag(ev, action))

    def play_mood(self, kind: str, stim: float = 0.0, tag: str | None = None) -> None:
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
            self.play_sfx(ev, tag=tag or sfx_tag(ev, kind))
            return
        self.play_action(kind, tag=tag)

    def play_sfx(self, event_name: str, tag: str | None = None) -> None:
        if self.volume <= 0.01:
            return
        label = tag or sfx_tag(event_name)
        if any(m and m in event_name for m in self._mute):
            print(f"[ANIM] SFX MUTE [{label}] {event_name}", flush=True)
            return
        wav_name = self._catalog.get(event_name, event_name if event_name.endswith(".wav") else event_name + ".wav")
        path = self._pick_wav(ROOT / "assets" / "sfx", wav_name)
        src = "file"
        data = self._audible_wav(path) if path else b""
        if not data:
            src = "synth"
            data = synth.render(event_name, self.volume)
        print(f"[ANIM] SFX [{label}] {event_name} ({src} {len(data)}B)", flush=True)
        self.robot.speaker_power(True)
        threading.Thread(target=self._mix, args=(event_name, data), daemon=True).start()

    def _pick_wav(self, folder: Path, wav_name: str) -> Path | None:
        stem = wav_name[:-4] if wav_name.endswith(".wav") else wav_name
        cands = [folder / f"{stem}.wav"]
        cands.extend(sorted(folder.glob(f"{stem}.[0-9]*.wav")))
        exist = [p for p in cands if p.exists()]
        if not exist:
            return None
        return random.choice(exist)

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
                subprocess.run(["aplay", "-q", tmp.name], check=False, timeout=16)
            except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
                print(f"[ANIM] aplay skip: {exc}", flush=True)
