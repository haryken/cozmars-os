"""Show trên thân + greeting. Firetruck ~12s như docs."""

from __future__ import annotations

import asyncio
import math
import time


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


async def firetruck(robot, anim) -> None:
    print("[SHOW] firetruck ~12s", flush=True)
    anim.from_action("firetruck")
    t0 = time.monotonic()
    last_sfx = t0
    aborted = False
    while time.monotonic() - t0 < 12:
        if _over_cliff(robot):
            print("[SHOW] firetruck abort — cliff", flush=True)
            aborted = True
            robot.stop()
            break
        t = time.monotonic() - t0
        robot.speed(0.48, 0.22 if int(t * 5) % 2 == 0 else 0.58)
        robot.head(20 if int(t * 4) % 2 == 0 else -10)
        now = time.monotonic()
        if now - last_sfx >= 1.4:
            anim.play_sfx("Play__Robot_Vic_Sfx__Distress_Alert")
            last_sfx = now
        await asyncio.sleep(0.18)
    robot.stop()
    robot.head(0)
    if aborted:
        return
    anim.set_expression("happy")
    anim.play_action("eye_happy")


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
