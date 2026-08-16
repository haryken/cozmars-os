"""Xiaozhi MCP self.* → intent queue. Mic đóng đến wake (deferred)."""

from __future__ import annotations

TOOL_TO_INTENT = {
    "self.drive.forward": "intent_imperative_forward",
    "self.drive.back": "intent_imperative_backup",
    "self.drive.left": "intent_imperative_turnleft",
    "self.drive.right": "intent_imperative_turnright",
    "self.drive.stop": "intent_imperative_halt",
    "self.show.firetruck": "intent_play_firetruck",
    "self.show.dance": "intent_imperative_dance",
    "self.show.sing": "intent_imperative_sing",
    "self.cube.find": "intent_imperative_findcube",
    "self.cube.pick": "intent_play_pickupcube",
    "self.cube.roll": "intent_play_rollcube",
    "self.game.start": "intent_play_anygame",
}


class Deferred:
    def __init__(self) -> None:
        self.pending: str | None = None
        self.mic_open = True

    def take(self, name: str) -> None:
        self.pending = name
        self.mic_open = False
        print(f"[MCP] deferred {name} — mic closed until wake", flush=True)

    def deliver(self, brain) -> None:
        if self.pending:
            print(f"[MCP] deliver {self.pending}", flush=True)
            brain.handle_intent(self.pending)
            self.pending = None
        self.mic_open = True


DEFERRED = Deferred()


def dispatch(brain, tool: str, args: dict) -> str:
    if tool == "self.look.head":
        brain.robot.head(float(args.get("angle", 10)))
        return "ok"
    if tool == "self.lift.set":
        brain.robot.lift(float(args.get("height", 0.5)))
        return "ok"
    if tool == "self.volume.set":
        brain.handle_intent("intent_imperative_volumelevel_extend", {"level": float(args.get("level", 0.7))})
        return "ok"
    if tool == "self.battery.get":
        return "không đo được (V2 không ADC)"
    intent = TOOL_TO_INTENT.get(tool)
    if not intent:
        if tool.startswith("self.game"):
            intent = "intent_play_anygame"
        elif tool.startswith("self.chess"):
            return "chess summary via wired"
    if intent:
        DEFERRED.take(intent)
        DEFERRED.deliver(brain)
        return f"queued {intent}"
    print(f"[MCP] unknown tool {tool}", flush=True)
    return "unknown"
