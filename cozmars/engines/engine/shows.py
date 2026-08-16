"""Show trên thân + greeting. Firetruck = clip WireOS anim_petdetection_dog_02."""

from __future__ import annotations

import asyncio
import json
import math
import time
from pathlib import Path

_CLIPS = Path(__file__).with_name("clips")
_FIRETRUCK = None


def _over_cliff(robot) -> bool:
    from ..robot.cliff import flags

    left, right = flags(robot.sensors())
    return left or right


async def nod(robot, anim) -> None:
    anim.from_action("hello")
    for _ in range(6):
        robot.head(16)
        await asyncio.sleep(0.22)
        robot.head(-12)
        await asyncio.sleep(0.22)
    robot.head(0)


async def lift_show(robot, anim) -> None:
    anim.from_action("fistbump")
    anim.play_action("lift_up")
    robot.lift(1.0)
    await asyncio.sleep(1.1)
    anim.play_action("lift_down")
    robot.lift(0.05)
    await asyncio.sleep(1.0)
    robot.lift(0)


def _clip(name: str) -> dict:
    global _FIRETRUCK
    if name == "firetruck":
        if _FIRETRUCK is None:
            _FIRETRUCK = json.loads((_CLIPS / "firetruck.json").read_text(encoding="utf-8"))
        return _FIRETRUCK
    return json.loads((_CLIPS / f"{name}.json").read_text(encoding="utf-8"))


def _hold(track: list, t_ms: float, default=0.0):
    val = default
    for row in track:
        if row[0] > t_ms:
            break
        val = row[1]
    return val


def _body_lr(track: list, t_ms: float) -> tuple[float, float]:
    for t0, dur, left, right in track:
        if t0 <= t_ms < t0 + max(dur, 1):
            return float(left), float(right)
        if t0 > t_ms:
            break
    return 0.0, 0.0


async def _play_clip(robot, anim, clip: dict) -> None:
    duration = float(clip.get("duration_ms") or 0) / 1000.0
    audio = list(clip.get("audio") or [])
    face = list(clip.get("face") or [])
    body = list(clip.get("body") or [])
    head = list(clip.get("head") or [])
    lift = list(clip.get("lift") or [])
    light = list(clip.get("light") or [])
    ai = fi = 0
    last_face = None
    last_lr = (None, None)
    last_head = last_lift = last_bl = None
    t0 = time.monotonic()
    while time.monotonic() - t0 < duration:
        t_ms = (time.monotonic() - t0) * 1000.0
        while ai < len(audio) and t_ms >= float(audio[ai]["t"]):
            anim.play_sfx(str(audio[ai]["e"]), tag="show")
            ai += 1
        while fi < len(face) and t_ms >= float(face[fi]["t"]):
            expr = str(face[fi]["e"])
            if expr != last_face:
                anim.set_expression(expr)
                last_face = expr
            fi += 1
        lr = _body_lr(body, t_ms)
        if lr != last_lr:
            robot.speed(*lr)
            last_lr = lr
        h = _hold(head, t_ms, 0.0)
        if h != last_head:
            robot.head(float(h))
            last_head = h
        z = _hold(lift, t_ms, 0.0)
        if z != last_lift:
            robot.lift(float(z))
            last_lift = z
        bl = _hold(light, t_ms, 0.85)
        if bl != last_bl:
            robot.backlight(max(0.12, float(bl) if light else 0.85))
            last_bl = bl
        await asyncio.sleep(0.03)
    robot.stop()
    robot.head(0)
    robot.lift(0)
    robot.backlight(0.85)


async def firetruck(robot, anim) -> float:
    """Chạy hết clip (kể cả đang hố/pickup). Trả về số giây đã diễn."""
    clip = _clip("firetruck")
    dur = float(clip.get("duration_ms") or 13200) / 1000.0
    print(f"[SHOW] firetruck WireOS {clip.get('name')} {dur:.1f}s", flush=True)
    if _over_cliff(robot):
        print("[SHOW] firetruck — IR hụt sàn, vẫn chạy show (không abort)", flush=True)
        t_clear = time.monotonic()
        while _over_cliff(robot) and time.monotonic() - t_clear < 0.8:
            robot.speed(-0.42, -0.42)
            await asyncio.sleep(0.05)
        robot.stop()
    t0 = time.monotonic()
    await _play_clip(robot, anim, clip)
    ran = time.monotonic() - t0
    anim.set_expression("happy")
    return ran


async def dance(robot, anim) -> None:
    print("[SHOW] dance", flush=True)
    anim.from_action("dance")
    for i in range(10):
        if _over_cliff(robot):
            print("[SHOW] dance abort — cliff", flush=True)
            break
        robot.speed(0.35 if i % 2 == 0 else -0.35, -0.35 if i % 2 == 0 else 0.35)
        robot.lift(1.0 if i % 2 == 0 else 0.05)
        robot.head(18 if i % 2 == 0 else -14)
        await asyncio.sleep(0.32)
    robot.stop()
    robot.lift(0)
    robot.head(0)


async def sing(robot, anim) -> None:
    print("[SHOW] sing", flush=True)
    anim.from_action("hello")
    anim.play_action("eye_happy")
    for i in range(8):
        robot.head(12 * math.sin(i))
        await asyncio.sleep(0.28)
    robot.head(0)


async def come(robot, anim) -> None:
    anim.from_action("hello")
    anim.play_action("forward")
    t0 = time.monotonic()
    hit_cliff = False
    while time.monotonic() - t0 < 4:
        s = robot.sensors()
        if s.get("inRange"):
            break
        if _over_cliff(robot):
            hit_cliff = True
            break
        robot.speed(0.4, 0.4)
        await asyncio.sleep(0.08)
    robot.stop()
    if not hit_cliff:
        await nod(robot, anim)


async def lookatme(robot, anim) -> None:
    anim.set_expression("focused")
    robot.head(22)
    await asyncio.sleep(1.2)
    robot.head(8)


async def sleep_show(robot, anim) -> None:
    anim.set_expression("sleepy")
    anim.play_action("shutdown")
    robot.stop()
    robot.head(-18)
    robot.lift(0)
    await asyncio.sleep(1.5)
