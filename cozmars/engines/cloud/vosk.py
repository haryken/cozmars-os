"""Vosk small EN. Model: assets/vosk hoặc ~/.cozmars/vosk/."""

from __future__ import annotations

from pathlib import Path


def model_dirs() -> list[Path]:
    home = Path.home() / ".cozmars" / "vosk"
    here = Path(__file__).resolve().parents[3] / "assets" / "vosk"
    return [home, here]


def probe() -> None:
    try:
        import vosk  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        print(f"[CLOUD] MISS vosk — {exc}", flush=True)
        return
    for d in model_dirs():
        if d.exists() and any(d.iterdir()):
            print(f"[CLOUD] vosk model dir {d}", flush=True)
            return
    print("[CLOUD] vosk import OK nhưng chưa có model small (vosk-model-small-en-us-0.15)", flush=True)


def listen(brain) -> None:
    print("[CLOUD] Vosk listen skipped (cần mic + model) — matcher text nếu có", flush=True)


def transcribe_pcm(_pcm: bytes) -> str:
    return ""
