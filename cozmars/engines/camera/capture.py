"""JPEG → BGR. cv2 optional; không imshow trên Pi."""

from __future__ import annotations


def decode_jpeg(data: bytes):
    try:
        import cv2
        import numpy as np

        arr = np.frombuffer(data, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is not None:
            img = cv2.flip(img, -1)
        return img
    except Exception as exc:  # noqa: BLE001
        print(f"[CAMERA] decode skip: {exc}", flush=True)
        return None
