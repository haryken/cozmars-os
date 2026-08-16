"""Não: idle / explore / intent. Tick ~20 Hz."""

from __future__ import annotations

import asyncio
import math
import time

from . import intents, shows
from .explore import Explore
from .mood import Mood
from ..robot.cliff import CliffReactor


class BrainEngine:
    name = "engine"

    def __init__(self, robot, anim, env: dict) -> None:
        self.robot = robot
        self.anim = anim
        self.env = env
        self.mode = "boot"
        self.t0 = time.monotonic()
        self.running = True
        self.mood = Mood()
        self.explore = Explore(robot, anim, self.mood)
        self.cliff = CliffReactor(robot, anim, self.mood)
        self._intent_q: asyncio.Queue[tuple[str, dict]] = asyncio.Queue()

    def handle_intent(self, name: str, params: dict | None = None) -> None:
        self._intent_q.put_nowait((name, params or {}))

    def request(self, action: str) -> None:
        mapped = {
            "wander": "intent_explore_start",
            "explore": "intent_explore_start",
            "idle": "intent_imperative_halt",
            "stop": "intent_imperative_halt",
            "nod": "intent_imperative_come",
            "lift": "intent_play_fistbump",
            "firetruck": "intent_play_firetruck",
        }.get(action, action)
        self.handle_intent(mapped)

    async def run(self) -> None:
        print("[ENGINE] brain start — boot → idle", flush=True)
        self.anim.from_action("boot")
        while self.running:
            await self._drain_intents()
            sensors = self.robot.sensors()
            intent = sensors.get("osIntent")
            if intent:
                print(f"[ENGINE] sim intent {intent}", flush=True)
                hal = getattr(self.robot, "hal", None)
                if hal is not None and hasattr(hal, "_post"):
                    hal._post({"op": "os_intent_ack"})
                self.request(str(intent))
            elapsed = time.monotonic() - self.t0
            cliff_on = bool(self.env.get("cliff_stop", True))
            was_cliff = self.cliff.owning
            if self.cliff.tick(sensors, cliff_on):
                if self.mode == "explore" and self.cliff.just_started:
                    self.explore.notify_cliff(self.cliff.side)
            elif was_cliff and self.mode == "explore":
                self.explore.after_cliff(self.cliff.side)
            elif self.mode == "explore":
                self.explore.tick(elapsed, sensors)
            elif sensors.get("inRange") and self.mode in ("boot", "idle"):
                self.anim.from_action("obstacle")
                self.robot.speed(-0.22, 0.42)
                self.robot.head(12)
            elif self.mode == "boot":
                self._boot(elapsed)
            elif self.mode == "idle":
                self._idle(elapsed)
            elif self.mode == "show":
                pass
            await asyncio.sleep(0.05)

    async def _sleep_motion(self, seconds: float) -> None:
        t0 = time.monotonic()
        on = bool(self.env.get("cliff_stop", True))
        while time.monotonic() - t0 < seconds and self.running:
            s = self.robot.sensors()
            if self.cliff.tick(s, on):
                while self.running and self.cliff.tick(self.robot.sensors(), on):
                    await asyncio.sleep(0.05)
                return
            await asyncio.sleep(0.05)

    def _boot(self, t: float) -> None:
        if t < 0.4:
            self.robot.head(0)
        elif t < 0.9:
            self.anim.set_expression("happy")
            self.robot.head(16)
        elif t < 1.4:
            self.robot.head(-10)
        elif t < 2.0:
            self.robot.head(0)
            self.robot.lift(0.4)
        elif t < 2.5:
            self.robot.lift(0.05)
        else:
            print("[ENGINE] boot xong — idle", flush=True)
            self.mode = "idle"
            self.t0 = time.monotonic()
            self.anim.from_action("idle")

    def _idle(self, t: float) -> None:
        self.mood.decay(0.05, exploring=False)
        self.robot.speed(0, 0)
        self.robot.head(10 * math.sin(t * 0.55))
        self.robot.lift(0.06 + 0.05 * (0.5 + 0.5 * math.sin(t * 0.32)))

    async def _drain_intents(self) -> None:
        while not self._intent_q.empty():
            name, params = self._intent_q.get_nowait()
            print(f"[ENGINE] intent {name} {params}", flush=True)
            action = intents.dispatch(name)
            if not action:
                print(f"[ENGINE] intent chưa map {name}", flush=True)
                continue
            await self._do(action, params)

    async def _do(self, action: str, params: dict) -> None:
        self.mode = "show"
        if action == "halt":
            self.mode = "idle"
            self.t0 = time.monotonic()
            self.robot.stop()
            self.anim.from_action("idle")
        elif action == "explore":
            self.mode = "explore"
            self.t0 = time.monotonic()
            self.explore.start()
        elif action == "forward":
            self.anim.play_action("forward")
            self.robot.speed(0.45, 0.45)
            await self._sleep_motion(1.2)
            self.robot.stop()
            self.mode = "idle"
        elif action == "backup":
            self.anim.play_action("backward")
            self.robot.speed(-0.4, -0.4)
            await self._sleep_motion(1.0)
            self.robot.stop()
            self.mode = "idle"
        elif action in ("turn_left", "turn_right", "turn_around"):
            self.anim.play_action("turn_left")
            s = 0.45 if action != "turn_right" else -0.45
            dur = 1.6 if action == "turn_around" else 0.7
            self.robot.speed(-s, s)
            await self._sleep_motion(dur)
            self.robot.stop()
            self.mode = "idle"
        elif action in ("come", "nod"):
            await shows.come(self.robot, self.anim)
            self.mode = "idle"
        elif action == "lookatme":
            await shows.lookatme(self.robot, self.anim)
            self.mode = "idle"
        elif action == "lookoverthere":
            self.robot.head(-10)
            await asyncio.sleep(0.8)
            self.mode = "idle"
        elif action == "fistbump":
            await shows.lift_show(self.robot, self.anim)
            self.mode = "idle"
        elif action == "firetruck":
            self.mood.event("firetruck")
            await shows.firetruck(self.robot, self.anim)
            self.mode = "idle"
        elif action == "dance":
            await shows.dance(self.robot, self.anim)
            self.mode = "idle"
        elif action == "sing":
            await shows.sing(self.robot, self.anim)
            self.mode = "idle"
        elif action == "hello":
            self.anim.from_action("hello")
            await shows.nod(self.robot, self.anim)
            self.mode = "idle"
        elif action == "goodbye":
            self.anim.set_expression("sad")
            await shows.sleep_show(self.robot, self.anim)
            self.mode = "idle"
        elif action == "sleep":
            await shows.sleep_show(self.robot, self.anim)
            self.mode = "idle"
        elif action in ("happy",):
            self.mood.event("praise")
            self.anim.from_action("hello")
            self.anim.play_mood("happy", self.mood.stimulated)
            self.mode = "idle"
        elif action in ("scold", "sad"):
            self.mood.event("scold")
            self.anim.set_expression("sad")
            self.anim.play_mood("sad", self.mood.stimulated)
            self.mode = "idle"
        elif action == "quiet":
            self.anim.volume = 0
            print("[ENGINE] volume 0", flush=True)
            self.mode = "idle"
        elif action == "vol_up":
            self.anim.volume = min(1.0, self.anim.volume + 0.15)
            print(f"[ENGINE] volume {self.anim.volume:.2f}", flush=True)
            self.mode = "idle"
        elif action == "vol_down":
            self.anim.volume = max(0.0, self.anim.volume - 0.15)
            print(f"[ENGINE] volume {self.anim.volume:.2f}", flush=True)
            self.mode = "idle"
        elif action == "vol_set":
            lvl = float(params.get("level", 0.7))
            self.anim.volume = max(0.0, min(1.0, lvl))
            self.mode = "idle"
        elif action in ("find_cube", "pickup_cube", "fetch_cube", "roll_cube", "keepaway"):
            from . import cube as cube_mod

            await cube_mod.run(self.robot, self.anim, action)
            self.mode = "idle"
        elif action.startswith("game_"):
            print(f"[ENGINE] open game {action} — wired /games", flush=True)
            self.anim.set_expression("focused")
            self.mode = "idle"
        elif action == "photo":
            print("[ENGINE] photo → camera capture", flush=True)
            self.mode = "idle"
        elif action == "charger":
            print("[ENGINE] go charger — ArUco id 0 (commented upstream, skip HW)", flush=True)
            self.mode = "idle"
        elif action in ("say_time", "weather", "feeling", "listen", "yes", "no", "skip"):
            print(f"[ENGINE] {action} (cloud/voice)", flush=True)
            self.anim.set_expression("surprised" if action == "listen" else "neutral")
            self.mode = "idle"
        else:
            print(f"[ENGINE] action {action} no-op", flush=True)
            self.mode = "idle"
        self.t0 = time.monotonic()

    def stop(self) -> None:
        self.running = False
        self.robot.stop()
