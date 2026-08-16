"""ws JSON RPC — không bắt buộc wsmprpc (msgpack firmware)."""

from __future__ import annotations

import json


class SwitchboardEngine:
    name = "switchboard"

    def __init__(self, robot) -> None:
        self.robot = robot
        try:
            import wsmprpc  # noqa: F401

            print("[RPC] wsmprpc ok", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[RPC] MISS wsmprpc — JSON /rpc fallback ({exc})", flush=True)

    def call(self, method: str, *args) -> None:
        print(f"[RPC] {method}{args}", flush=True)
        if method == "speed" and len(args) >= 2:
            self.robot.speed(float(args[0]), float(args[1]))
        elif method == "head" and args:
            self.robot.head(float(args[0]))
        elif method == "lift" and args:
            self.robot.lift(float(args[0]))
        elif method == "stop":
            self.robot.stop()
