"""Mood Vector-lite: Happy + Stimulated (xem engine/moodSystem + emotionevents)."""

from __future__ import annotations

# Giá trị gần interaction_events / reaction_events WireOS (không copy full graph).
EVENTS = {
    "explore_start": {"Happy": 0.12, "Stimulated": 0.28},
    "look_around": {"Happy": 0.04, "Stimulated": 0.10},
    "examine_obstacle": {"Happy": 0.10, "Stimulated": 0.12},  # ExploringExamineObstacle
    "drive": {"Stimulated": 0.02},
    "stuck": {"Happy": -0.12, "Stimulated": 0.08},
    "cliff": {"Happy": -0.25, "Stimulated": 0.18},
    "praise": {"Happy": 0.35, "Stimulated": 0.20},
    "scold": {"Happy": -0.35, "Stimulated": 0.15},
    "hello": {"Happy": 0.15, "Stimulated": 0.12},
    "firetruck": {"Happy": 0.08, "Stimulated": 0.35},
}


class Mood:
    def __init__(self) -> None:
        self.happy = 0.40
        self.stimulated = 0.18

    def event(self, name: str) -> None:
        for key, delta in EVENTS.get(name, {}).items():
            if key == "Happy":
                self.happy = max(0.0, min(1.0, self.happy + delta))
            elif key == "Stimulated":
                self.stimulated = max(0.0, min(1.0, self.stimulated + delta))

    def decay(self, dt: float, exploring: bool = False) -> None:
        # Vector stim decay chậm khi đang explore
        rate = 0.018 if exploring else 0.06
        self.stimulated = max(0.0, self.stimulated - rate * dt)
        self.happy = max(0.15, self.happy - 0.012 * dt)

    def high_stim(self) -> bool:
        return self.stimulated >= 0.45

    def face(self, *, exploring: bool = False) -> str:
        if self.happy < 0.28:
            return "sad"
        if exploring and self.stimulated >= 0.62:
            return "happy"
        if exploring and self.stimulated < 0.22:
            return "focused"
        if self.happy >= 0.55:
            return "happy"
        return "happy" if exploring else "auto"
