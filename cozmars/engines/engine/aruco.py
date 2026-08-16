"""ArUco 4×4_50 — OpenCV optional, không imshow."""

from __future__ import annotations


def detect(_bgr) -> list:
    try:
        import cv2  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        print(f"[ARUCO] MISS cv2 — {exc}", flush=True)
        return []
    print("[ARUCO] detector chưa load dictionary (phase 1)", flush=True)
    return []
