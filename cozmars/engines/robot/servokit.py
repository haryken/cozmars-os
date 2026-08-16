"""PCA9685 wrapper — copy hành vi rcute_servokit, import mềm."""

from __future__ import annotations


class ServoKit:
    def __init__(self, channels: int = 16, frequency: int = 60) -> None:
        try:
            from adafruit_servokit import ServoKit as Real  # type: ignore

            self._kit = Real(channels=channels, frequency=frequency)
            self.servo = self._kit.servo
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"adafruit_servokit: {exc}") from exc
