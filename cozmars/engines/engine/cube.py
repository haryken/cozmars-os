"""Cube / ArUco — dùng SDK logic nếu cv2 có; không thì search bằng sonar+quay."""

from __future__ import annotations

import asyncio

from ..robot.cliff import should_stop


async def run(robot, anim, action: str) -> None:
    anim.from_action("search_cube")
    print(f"[CUBE] {action}", flush=True)
    try:
        from .sdk.aruco import ArucoDetector  # type: ignore

        print("[CUBE] ArucoDetector import OK", flush=True)
        _ = ArucoDetector
    except Exception as exc:  # noqa: BLE001
        print(f"[CUBE] MISS cv2/aruco — {exc}  fallback quay tìm", flush=True)
    anim.play_action("search_cube")
    robot.head(-12)
    robot.lift(0)
    for i in range(8):
        s = robot.sensors()
        if s.get("inRange") and action in ("pickup_cube", "fetch_cube"):
            robot.stop()
            anim.play_action("pick_up_cube")
            robot.lift(1.0)
            await asyncio.sleep(0.8)
            if action == "roll_cube":
                robot.speed(0.3, -0.3)
                await asyncio.sleep(0.4)
            robot.lift(0)
            return
        if should_stop(s, True):
            robot.stop()
            print("[CUBE] abort — cliff", flush=True)
            return
        robot.speed(-0.28 if i % 2 == 0 else 0.28, 0.28 if i % 2 == 0 else -0.28)
        await asyncio.sleep(0.35)
    robot.stop()
    anim.set_expression("sad")
    print("[CUBE] không thấy cube", flush=True)
