"""Supervisor: python3 -m cozmars

Thứ tự: bootcheck → robot → camera → anim → switchboard → wired → engine → cloud → update
"""

from __future__ import annotations

import argparse
import asyncio
import os
import signal
import subprocess

from . import bootcheck, config
from .engines.anim import AnimEngine
from .engines.camera import CameraEngine
from .engines.cloud import CloudEngine
from .engines.engine import BrainEngine
from .engines.robot import build as build_robot
from .engines.switchboard import SwitchboardEngine
from .engines.update import UpdateEngine
from .engines.wired import WiredEngine
from .version import __version__


def _parse(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Cozmars OS supervisor")
    p.add_argument("--hal", choices=("auto", "sim", "pi", "null"), default=os.environ.get("COZMARS_HAL", "auto"))
    p.add_argument("--sim-url", default=os.environ.get("COZMARS_SIM_URL", ""))
    p.add_argument("--web", action="store_true", help="Bật wired (Pi :80/:8080).")
    p.add_argument("--no-web", action="store_true")
    p.add_argument("--web-port", type=int, default=0, help="Một port web (sim 8099). 0 = 80+8080")
    p.add_argument("--no-brain", action="store_true")
    return p.parse_args(argv)


def _resolve_hal(args: argparse.Namespace) -> tuple[str, str]:
    url = args.sim_url
    kind = args.hal
    if kind == "auto":
        if url:
            kind = "sim"
        elif os.path.exists("/sys/firmware/devicetree/base/model"):
            kind = "pi"
        else:
            kind = "null"
            print("[BOOT] auto HAL=null (không phải Pi, không --sim-url)", flush=True)
    return kind, url


def _stop_sim_splash() -> None:
    """Tắt splash trên LCD sim — cùng lúc OS thật stop systemd bootanim."""
    sim = os.environ.get("COZMARS_SIM_URL", "").rstrip("/")
    if not sim:
        return
    try:
        import json
        import urllib.request

        req = urllib.request.Request(
            sim + "/api/cmd",
            data=json.dumps({"op": "boot_splash", "on": False}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=2).read()
        print("[BOOT] sim splash off", flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"[BOOT] sim splash skip — {exc}", flush=True)


def _stop_bootanim(kind: str) -> None:
    """Nhả ST7789 cho mắt — giống vic-anim stop vic-bootAnim."""
    if kind == "sim":
        _stop_sim_splash()
        return
    if kind != "pi":
        return
    try:
        subprocess.run(
            ["systemctl", "stop", "cozmars-bootanim.service"],
            check=False,
            timeout=3,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print("[BOOT] bootanim stopped", flush=True)
    except Exception:
        pass


async def _amain(args: argparse.Namespace) -> None:
    print(f"[BOOT] Cozmars OS {__version__}", flush=True)
    bootcheck.report()
    conf, env, home = config.load()
    print(f"[BOOT] home={home}", flush=True)
    kind, url = _resolve_hal(args)
    robot = build_robot(kind, url, conf)
    camera = CameraEngine(sim_url=url)
    anim = AnimEngine(robot, env)
    rpc = SwitchboardEngine(robot)
    brain = BrainEngine(robot, anim, env)
    cloud = CloudEngine(brain, env)
    update = UpdateEngine()
    want_web = args.web or (kind == "sim" and not args.no_web)
    wired = None
    if want_web:
        if args.web_port:
            ports = (args.web_port,)
        elif kind == "sim":
            ports = (int(os.environ.get("COZMARS_WEB_PORT", "8099")),)
        else:
            ports = (80, 8080)
        wired = WiredEngine(robot, brain, cloud=cloud, update=update, camera=camera, ports=ports)
        await wired.start()
    print(
        f"[BOOT] engines: robot={robot.hal.name} camera={camera.backend or 'off'} "
        f"anim engine cloud switchboard wired={'on' if wired else 'off'} update",
        flush=True,
    )
    _stop_bootanim(kind)
    stop = asyncio.Event()

    def _stop(*_a):
        print("[BOOT] signal — stopping", flush=True)
        stop.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _stop)
        except NotImplementedError:
            pass

    tasks = []
    if not args.no_brain:
        tasks.append(asyncio.create_task(brain.run(), name="brain"))
    tasks.append(asyncio.create_task(stop.wait(), name="stop"))
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    brain.stop()
    robot.close()
    if wired:
        await wired.stop()
    for t in pending:
        t.cancel()
    print("[BOOT] exit", flush=True)
    _ = (camera, rpc, cloud, update, done)


def main(argv=None) -> None:
    args = _parse(argv)
    asyncio.run(_amain(args))


if __name__ == "__main__":
    main()
