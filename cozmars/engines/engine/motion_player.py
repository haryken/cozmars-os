"""Timeline bánh + đầu + lift + SFX cùng lúc (không replay anim JSON 33 ms)."""

from __future__ import annotations

import asyncio
from typing import Iterable, Sequence, Tuple

Keyframe = Tuple[float, str, object]


async def play(robot, anim, keys: Sequence[Keyframe]) -> None:
    """keys: (t_sec, kind, value) kind in motor,head,lift,sfx,eyes."""
    t0 = 0.0
    for t, kind, val in keys:
        dt = max(0.0, t - t0)
        if dt:
            await asyncio.sleep(dt)
        t0 = t
        if kind == "motor":
            l, r = val
            robot.speed(float(l), float(r))
            anim.play_action("forward" if (l + r) > 0 else "backward")
        elif kind == "head":
            robot.head(float(val))
        elif kind == "lift":
            robot.lift(float(val))
        elif kind == "sfx":
            anim.play_action(str(val))
        elif kind == "eyes":
            anim.set_expression(str(val))
    robot.stop()
