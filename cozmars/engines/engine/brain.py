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
        self.pet_explore = True
        self._show_at: dict[str, float] = {}
        self._last_os_cmd = None
        self._stim_lock: float | None = None

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

    def _take_os_cmd(self, sensors: dict) -> None:
        cmd = sensors.get("osCmd")
        if not isinstance(cmd, dict):
            return
        seq = cmd.get("seq")
        if seq is None or seq == self._last_os_cmd:
            return
        self._last_os_cmd = seq
        hal = getattr(self.robot, "hal", None)
        if hal is not None and hasattr(hal, "_post"):
            hal._post({"op": "os_cmd_ack"})
        self._apply_os_cmd(cmd)

    def _apply_os_cmd(self, cmd: dict) -> None:
        kind = str(cmd.get("kind") or "")
        print(f"[ENGINE] os cmd {kind} seq={cmd.get('seq')}", flush=True)
        if kind == "assume":
            self.mode = "teleop"
            self.robot.speed(0, 0)
            return
        if kind == "release":
            self.mode = "idle"
            self.robot.speed(0, 0)
            return
        if kind == "eye_color":
            name = str(cmd.get("name") or "TIP_OVER_TEAL")
            if cmd.get("custom") or name.upper() == "CUSTOM":
                self.anim.set_eye_color(
                    "CUSTOM",
                    hue=float(cmd.get("hue") or 0.5),
                    sat=float(cmd.get("sat") or 1.0),
                )
            else:
                hue = cmd.get("hue")
                sat = cmd.get("sat")
                self.anim.set_eye_color(
                    name,
                    hue=None if hue is None else float(hue),
                    sat=None if sat is None else float(sat),
                )
            return
        if kind == "volume":
            lvl = max(0, min(5, int(cmd.get("level", 3))))
            pct = (0, 20, 40, 60, 80, 100)[lvl]
            self.anim.volume = pct / 100.0
            self.env["say_vol"] = pct
            self._save_env()
            return
        if kind == "expression":
            self.anim.set_expression(str(cmd.get("name") or "auto"))
            return
        if kind == "say":
            text = str(cmd.get("text") or "").strip()
            if text:
                from cozmars.engines.cloud import google_tts

                google_tts.say(text, "vi")
            return
        if kind == "intent":
            self.request(str(cmd.get("name") or "idle"))
            return
        if kind == "settings":
            self._apply_settings_patch(cmd.get("patch") or {})

    def _apply_settings_patch(self, patch: dict) -> None:
        if not isinstance(patch, dict):
            return
        if "cliff_stop" in patch:
            self.env["cliff_stop"] = bool(patch["cliff_stop"])
        if "location" in patch:
            self.env["location"] = str(patch["location"] or "")
        if "timezone" in patch:
            self.env["timezone"] = str(patch["timezone"] or "Asia/Bangkok")
        if "temp_unit" in patch:
            self.env["temp_unit"] = str(patch["temp_unit"] or "c")
        if "volume_level" in patch:
            lvl = max(0, min(5, int(patch["volume_level"])))
            pct = (0, 20, 40, 60, 80, 100)[lvl]
            self.anim.volume = pct / 100.0
            self.env["say_vol"] = pct
        if "stim_mode" in patch:
            if str(patch["stim_mode"]) == "auto":
                self._stim_lock = None
            else:
                self._stim_lock = float(patch.get("stim", self.mood.stimulated))
        if "stim" in patch and self._stim_lock is not None:
            self._stim_lock = max(0.0, min(1.0, float(patch["stim"])))
            self.mood.stimulated = self._stim_lock
        if "eye_color" in patch or "eye_hue" in patch:
            name = str(patch.get("eye_color") or self.env.get("eye_color") or "TIP_OVER_TEAL")
            hue = patch.get("eye_hue", self.env.get("eye_hue"))
            sat = patch.get("eye_sat", self.env.get("eye_sat"))
            custom = bool(patch.get("eye_custom")) or name.upper() == "CUSTOM"
            if custom:
                self.anim.set_eye_color(
                    "CUSTOM",
                    hue=float(hue if hue is not None else 0.5),
                    sat=float(sat if sat is not None else 1.0),
                )
            else:
                self.anim.set_eye_color(
                    name,
                    hue=None if hue is None else float(hue),
                    sat=None if sat is None else float(sat),
                )
        self._save_env()

    def _save_env(self) -> None:
        try:
            from cozmars.config import save_env

            save_env(self.env)
        except Exception:
            pass

    async def run(self) -> None:
        print("[ENGINE] brain start — boot → khám phá", flush=True)
        self.anim.from_action("boot")
        while self.running:
            await self._drain_intents()
            sensors = self.robot.sensors()
            self._take_os_cmd(sensors)
            if sensors.get("ctrlAssumed") and self.mode not in ("show", "boot", "teleop"):
                self.mode = "teleop"
            intent = sensors.get("osIntent")
            if intent:
                print(f"[ENGINE] sim intent {intent}", flush=True)
                hal = getattr(self.robot, "hal", None)
                if hal is not None and hasattr(hal, "_post"):
                    hal._post({"op": "os_intent_ack"})
                self.request(str(intent))
            elapsed = time.monotonic() - self.t0
            cliff_on = bool(self.env.get("cliff_stop", True))
            if self._stim_lock is not None:
                self.mood.stimulated = self._stim_lock
            if self.mode == "boot":
                self._boot(elapsed)
            elif self.mode == "teleop":
                pass
            elif self.mode == "show":
                pass
            elif self.mode == "listen" or getattr(self.robot, "listening", False):
                self.robot.speed(0, 0)
                self.robot.head(14)
            else:
                was_cliff = self.cliff.owning
                if self.cliff.tick(sensors, cliff_on):
                    if self.mode == "explore" and self.cliff.just_started:
                        self.explore.notify_cliff(self.cliff.side)
                elif was_cliff and self.mode == "explore":
                    self.explore.after_cliff(self.cliff.side)
                elif self.mode == "explore":
                    self.explore.tick(elapsed, sensors)
                elif sensors.get("inRange") and self.mode in ("idle",):
                    self.anim.from_action("obstacle")
                    self.robot.speed(-0.22, 0.42)
                    self.robot.head(12)
                elif self.mode == "idle":
                    self._idle(elapsed)
            await asyncio.sleep(0.05)

    async def _sleep_motion(self, seconds: float) -> None:
        """Giữ lệnh chạy đủ thời gian cả khi Xiaozhi đang nghe (như firetruck)."""
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
            print("[ENGINE] boot xong — khám phá", flush=True)
            self.pet_explore = True
            self._resume_pet(restart=True)

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

    def interrupt_for_wake(self) -> None:
        was = self.mode
        if self.cliff.owning:
            self.cliff.phase = "idle"
            self.cliff.owning = False
        self.robot.stop()
        self.robot.listening = True
        self.mode = "listen"
        self.t0 = time.monotonic()
        print(f"[ENGINE] wake — đứng lại (đang {was})", flush=True)

    def finish_wake(self) -> None:
        self.robot.listening = False
        if self.mode != "listen":
            return
        if self.pet_explore:
            self._resume_pet(restart=False)
            print("[ENGINE] hết nói — khám phá tiếp", flush=True)
        else:
            self.mode = "idle"
            self.t0 = time.monotonic()
            self.robot.stop()
            print("[ENGINE] wake xong — idle", flush=True)

    def _resume_pet(self, *, restart: bool = False) -> None:
        self.mode = "explore"
        self.t0 = time.monotonic()
        if restart or self.explore.phase == "idle":
            self.explore.start()

    def _show_recent(self, name: str, window: float) -> bool:
        now = time.monotonic()
        last = self._show_at.get(name, 0.0)
        if now - last < window:
            print(f"[ENGINE] {name} skip — vừa chạy {now - last:.1f}s trước", flush=True)
            return True
        return False

    def _show_mark(self, name: str) -> None:
        self._show_at[name] = time.monotonic()

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
            print("[ENGINE] forward 1.4s", flush=True)
            self.anim.play_action("forward")
            self.robot.speed(0.50, 0.50)
            await self._sleep_motion(1.4)
            self.robot.stop()
            self.mode = "idle"
        elif action == "backup":
            print("[ENGINE] backup 1.2s", flush=True)
            self.anim.play_action("backward")
            self.robot.speed(-0.45, -0.45)
            await self._sleep_motion(1.2)
            self.robot.stop()
            self.mode = "idle"
        elif action in ("turn_left", "turn_right", "turn_around"):
            s = 0.52 if action != "turn_right" else -0.52
            dur = 1.8 if action == "turn_around" else 1.1
            print(f"[ENGINE] {action} {dur:.1f}s", flush=True)
            self.anim.play_action("turn_left")
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
            if self._show_recent("firetruck", 16.0):
                self.mode = "idle"
            else:
                if self.cliff.owning:
                    self.cliff.phase = "idle"
                    self.cliff.owning = False
                self.mood.event("firetruck")
                print("[ENGINE] firetruck — chạy show WireOS 13.2s", flush=True)
                ran = await shows.firetruck(self.robot, self.anim)
                if float(ran or 0) >= 4.0:
                    self._show_mark("firetruck")
                else:
                    print(f"[ENGINE] firetruck ngắn {float(ran or 0):.1f}s — không khóa cooldown", flush=True)
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
        elif action == "eye_color":
            wanted = str(params.get("color") or "").strip()
            if wanted:
                self.anim.set_eye_color(wanted)
            else:
                self.anim.cycle_eye_color()
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
        if action == "halt":
            self.pet_explore = False
            self.robot.listening = False
        elif getattr(self.robot, "listening", False):
            self.mode = "listen"
        elif action == "explore":
            self.pet_explore = True
        elif self.mode == "idle" and self.pet_explore:
            self._resume_pet(restart=False)
        self.t0 = time.monotonic()

    def stop(self) -> None:
        self.running = False
        self.robot.stop()
