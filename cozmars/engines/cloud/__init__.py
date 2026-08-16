"""Cloud: Xiaozhi | Vosk — thiếu lib thì log, engine vẫn chạy."""

from __future__ import annotations

import os

from . import matcher, vosk, wake, xiaozhi
from .voice import Voice


class CloudEngine:
    name = "cloud"

    def __init__(self, brain, env: dict) -> None:
        self.brain = brain
        self.env = env
        self.mode = os.environ.get("COZMARS_VOICE") or env.get("voice_mode") or "xiaozhi"
        self.voice = Voice()
        print(f"[CLOUD] voice_mode={self.mode} (off|xiaozhi|vosk)", flush=True)
        xiaozhi.probe()
        vosk.probe()
        if self.mode == "xiaozhi":
            xiaozhi.ota_hello()

    async def handle_wake(self, source: str = "button", text: str = "") -> dict:
        if hasattr(self.brain, "interrupt_for_wake"):
            self.brain.interrupt_for_wake()
        wake.earcon(source, getattr(self.brain, "anim", None))
        print(f"[CLOUD] wake source={source} text={text!r} mode={self.mode}", flush=True)
        leftover = xiaozhi.strip_wake(text)
        if source == "energy":
            leftover = ""
        intent = matcher.match(leftover) if leftover else None
        try:
            if intent:
                print(f"[CLOUD] match {leftover!r} → {intent}", flush=True)
                self.brain.handle_intent(intent)
                return {"ok": True, "path": "intent", "intent": intent}

            if self.mode == "xiaozhi":
                out = await xiaozhi.chat(self.brain, "" if source == "energy" else text)
                reply = (out or {}).get("text") or ""
                played = bool((out or {}).get("played"))
                if reply and not played:
                    self.say(reply)
                return {"ok": True, "path": "xiaozhi", "reply": reply, "played": played}
            if self.mode == "vosk":
                vosk.listen(self.brain)
                if text:
                    intent = matcher.match(text)
                    if intent:
                        self.brain.handle_intent(intent)
                        return {"ok": True, "path": "vosk", "intent": intent}
                return {"ok": True, "path": "vosk", "reply": ""}
            print("[CLOUD] wake nhưng voice_mode=off — không gửi Xiaozhi", flush=True)
            return {"ok": True, "path": "off"}
        finally:
            if hasattr(self.brain, "finish_wake"):
                self.brain.finish_wake()

    def on_wake(self, source: str = "button", text: str = "") -> None:
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self.handle_wake(source, text))
            return
        loop.create_task(self.handle_wake(source, text))

    def say(self, text: str, lang: str = "vi") -> None:
        self.voice.say(text, lang)

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self.env["voice_mode"] = mode
        from cozmars.config import save_env

        save_env(self.env)
        print(f"[CLOUD] set_mode {mode}", flush=True)
        if mode == "xiaozhi":
            xiaozhi.ota_hello()
