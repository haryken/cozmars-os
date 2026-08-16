"""Cliff 0/1 — chưa có HW; UI mặc định off. Khi có GPIO: 1 floor, 0 hole."""

from __future__ import annotations


def should_stop(sensors: dict, enabled: bool) -> bool:
    if not enabled:
        return False
    return int(sensors.get("cliff", 1)) == 0
