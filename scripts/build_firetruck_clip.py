#!/usr/bin/env python3
"""Xuất clip firetruck từ WireOS anim_petdetection_dog_02 + Missing_sfx.bnk."""

from __future__ import annotations

import json
import math
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from extract_vector_sfx import decode_wem, write_wav  # noqa: E402

ANIM = Path(
    "/home/linh/Projects/wire-os/anki/victor/EXTERNALS/animation-assets/animations"
    "/anim_petdetection_dog_02.json"
)
BNK = Path(
    "/home/linh/Projects/wire-os/anki/victor/EXTERNALS/victor-audio-assets"
    "/victor_robot/victor_linux/Missing_sfx.bnk"
)
WEM_IDS = (137932741, 621609733, 697066089)  # Codelab_Firetruck 02/01/03
HALF_BASE = 23.0
MAX_MMPS = 220.0
LIFT_MM = 92.0
HEAD_LIM = 30.0

AUDIO_MAP = {
    "Play__Robot_Sfx__Scrn_Curious": "Play__Robot_Vic_Sfx__Scrn_Curious",
    "Play__Robot_Vo__Shared_Curious": "Play__Robot_Vic_Sfx__Emote_Curious_Short",
    "Play__Robot_Sfx__Srv_Surprised": "Play__Robot_Vic_Sfx__Tread_Surprised",
    "Play__Robot_Vo__Gp_Cs_Thinking_Medium_Got_It": "Play__Robot_Vic_Sfx__Concentrate_Success",
    "Play__Robot_Sfx__Srv_Happy": "Play__Robot_Vic_Sfx__Tread_Happy",
    "Play__Robot_Vo__Codelab_Firetruck": "Play__Robot_Vo__Codelab_Firetruck",
    "Play__Robot_Vo__Shared_Happy_Long": "Play__Robot_Vic_Sfx__Emote_Happy_Long",
}


def _clip(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def _wheels(speed: float, radius) -> tuple[float, float]:
    if radius == "TURN_IN_PLACE" or radius == "POINT_TURN":
        mmps = (float(speed) * math.pi / 180.0) * HALF_BASE
        left, right = -mmps, mmps
    elif radius == "STRAIGHT":
        left = right = float(speed)
    else:
        r = float(radius)
        if abs(r) < 0.5:
            mmps = (float(speed) * math.pi / 180.0) * HALF_BASE
            left, right = -mmps, mmps
        else:
            left = float(speed) * (1.0 - HALF_BASE / r)
            right = float(speed) * (1.0 + HALF_BASE / r)
    return (
        round(_clip(left / MAX_MMPS, -1.0, 1.0), 3),
        round(_clip(right / MAX_MMPS, -1.0, 1.0), 3),
    )


def _light_v(kf: dict) -> float:
    peak = 0.0
    for key in ("Front", "Middle", "Back", "Left", "Right"):
        rgb = kf.get(key) or []
        for c in rgb[:3]:
            peak = max(peak, float(c or 0))
    return round(_clip(peak, 0.0, 1.0), 3)


def build_clip(frames: list[dict]) -> dict:
    audio = []
    body = []
    head = []
    lift = []
    light = []
    tmax = 0.0
    last_light = -1.0
    last_lt = -999
    for f in frames:
        t = float(f.get("triggerTime_ms") or 0)
        d = float(f.get("durationTime_ms") or 0)
        tmax = max(tmax, t + d)
        name = f.get("Name")
        if name == "RobotAudioKeyFrame":
            src = (f.get("audioName") or [""])[0]
            ev = AUDIO_MAP.get(src, src)
            audio.append({"t": int(round(t)), "e": ev})
        elif name == "BodyMotionKeyFrame":
            l, r = _wheels(f.get("speed") or 0, f.get("radius_mm"))
            body.append([int(round(t)), int(round(d)), l, r])
        elif name == "HeadAngleKeyFrame":
            head.append([int(round(t)), round(_clip(float(f.get("angle_deg") or 0), -HEAD_LIM, HEAD_LIM), 2)])
        elif name == "LiftHeightKeyFrame":
            lift.append([int(round(t)), round(_clip(float(f.get("height_mm") or 0) / LIFT_MM, 0.0, 1.0), 3)])
        elif name == "BackpackLightsKeyFrame":
            v = _light_v(f)
            if abs(v - last_light) >= 0.08 or t - last_lt >= 180:
                light.append([int(round(t)), v])
                last_light, last_lt = v, t
    return {
        "name": "anim_petdetection_dog_02",
        "duration_ms": int(round(max(tmax, 13200))),
        "audio": audio,
        "face": [
            {"t": 0, "e": "surprised"},
            {"t": 1680, "e": "focused"},
            {"t": 2670, "e": "angry"},
            {"t": 9760, "e": "happy"},
        ],
        "body": body,
        "head": head,
        "lift": lift,
        "light": light,
    }


def parse_didx(raw: bytes) -> dict[int, tuple[int, int]]:
    if raw[:4] != b"BKHD":
        raise ValueError("not a bnk")
    i = 0
    didx = data_off = None
    while i + 8 <= len(raw):
        cid = raw[i : i + 4]
        sz = int.from_bytes(raw[i + 4 : i + 8], "little")
        payload = i + 8
        if cid == b"DIDX":
            didx = raw[payload : payload + sz]
        elif cid == b"DATA":
            data_off = payload
            break
        i = payload + sz
    if not didx or data_off is None:
        raise ValueError("bnk missing DIDX/DATA")
    out = {}
    for o in range(0, len(didx) - 11, 12):
        wid = int.from_bytes(didx[o : o + 4], "little")
        off = int.from_bytes(didx[o + 4 : o + 8], "little")
        size = int.from_bytes(didx[o + 8 : o + 12], "little")
        out[wid] = (data_off + off, size)
    return out


def extract_firetruck_wavs() -> None:
    raw = BNK.read_bytes()
    idx = parse_didx(raw)
    out_dir = ROOT / "assets" / "sfx"
    out_dir.mkdir(parents=True, exist_ok=True)
    wrote = 0
    for n, wid in enumerate(WEM_IDS):
        if wid not in idx:
            print(f"missing wem id {wid}", file=sys.stderr)
            continue
        off, size = idx[wid]
        blob = raw[off : off + size]
        with tempfile.NamedTemporaryFile(suffix=".wem", delete=True) as tmp:
            tmp.write(blob)
            tmp.flush()
            rate, pcm = decode_wem(Path(tmp.name))
        name = "Play__Robot_Vo__Codelab_Firetruck.wav" if n == 0 else f"Play__Robot_Vo__Codelab_Firetruck.{n + 1}.wav"
        write_wav(out_dir / name, pcm, rate)
        print(f"wav {name}  {len(pcm)}B  {len(pcm) / (2 * rate):.2f}s")
        wrote += 1
    if wrote == 0:
        raise SystemExit("no firetruck wavs extracted")


def main() -> int:
    if not ANIM.exists() or not BNK.exists():
        print("missing WireOS anim/bnk", file=sys.stderr)
        return 1
    frames = json.loads(ANIM.read_text(encoding="utf-8"))["anim_petdetection_dog_02"]
    clip = build_clip(frames)
    dest = ROOT / "cozmars/engines/engine/clips/firetruck.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(clip, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"clip {dest}  body={len(clip['body'])} audio={len(clip['audio'])} dur={clip['duration_ms']}ms")
    extract_firetruck_wavs()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
