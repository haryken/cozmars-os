"""SFX Vector-style khi chưa extract wav thật từ robot.

Tạo WAV PCM 16-bit mono 22050 Hz — đủ nghe siren / vui / buồn / đập tay.
File trong assets/sfx/*.wav (extract-vector-sfx.sh) được ưu tiên hơn.
"""

from __future__ import annotations

import io
import math
import struct
import wave

RATE = 22050


def _pack(samples: list[float]) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        frames = bytearray()
        for s in samples:
            v = max(-0.98, min(0.98, s))
            frames += struct.pack("<h", int(v * 32767))
        w.writeframes(bytes(frames))
    return buf.getvalue()


def _tone(freq: float, dur: float, amp: float = 0.38, attack: float = 0.012, release: float = 0.06) -> list[float]:
    n = max(1, int(RATE * dur))
    out: list[float] = []
    for i in range(n):
        t = i / RATE
        env = 1.0
        if t < attack:
            env = t / max(attack, 1e-4)
        remain = dur - t
        if remain < release:
            env *= max(0.0, remain / max(release, 1e-4))
        out.append(amp * env * math.sin(2 * math.pi * freq * t))
    return out


def _sweep(f0: float, f1: float, dur: float, amp: float = 0.32) -> list[float]:
    n = max(1, int(RATE * dur))
    out: list[float] = []
    for i in range(n):
        t = i / RATE
        p = i / n
        freq = f0 + (f1 - f0) * p
        env = math.sin(math.pi * p)
        out.append(amp * env * math.sin(2 * math.pi * freq * t))
    return out


def _noise(dur: float, amp: float = 0.12) -> list[float]:
    n = max(1, int(RATE * dur))
    seed = 12345
    out: list[float] = []
    for i in range(n):
        seed = (1103515245 * seed + 12345) & 0x7FFFFFFF
        t = i / RATE
        env = math.sin(math.pi * t / dur) if dur > 0 else 1.0
        out.append(amp * env * ((seed / 0x7FFFFFFF) * 2 - 1))
    return out


def _kind(event: str) -> str:
    e = event.lower()
    if "distress" in e or "timer_alarm" in e:
        return "siren"
    if "fist_bump" in e:
        return "bump"
    if "wake_word_success" in e:
        return "wake_ok"
    if "wake_word_fail" in e:
        return "wake_fail"
    if "wake_word_off" in e:
        return "wake_off"
    if "wake_word" in e or "power_on" in e:
        return "wake_on"
    if "happy" in e or "greeting_hello" in e or "good_robot" in e:
        return "happy"
    if "sad" in e or "apology" in e or "goodbye" in e:
        return "sad"
    if "angry" in e or "cant_do" in e or "bad_robot" in e:
        return "angry"
    if "curious" in e or "surprised" in e:
        return "curious"
    if "tread" in e:
        return "tread"
    if "lift_up" in e or "lift_high_up" in e:
        return "lift_up"
    if "lift_down" in e or "lift_high_down" in e:
        return "lift_down"
    if "dancing" in e:
        return "dance"
    if "head_up" in e:
        return "head_up"
    if "head_down" in e:
        return "head_down"
    if "blink" in e:
        return "blink"
    if "cube_search" in e or "charger_search" in e or "scan" in e:
        return "ping"
    if "sleep" in e or "snore" in e:
        return "sleepy"
    if "attention" in e or "power_off" in e:
        return "off"
    return "blip"


def render(event: str, volume: float = 0.8) -> bytes:
    amp = max(0.05, min(1.0, volume)) * 0.55
    kind = _kind(event)
    samples: list[float]
    if kind == "siren":
        samples = []
        for _ in range(5):
            samples += _tone(740, 0.16, amp)
            samples += _tone(980, 0.16, amp)
    elif kind == "happy":
        samples = _tone(523, 0.08, amp) + _tone(659, 0.08, amp) + _tone(784, 0.18, amp * 1.05)
    elif kind == "sad":
        samples = _tone(392, 0.14, amp) + _tone(330, 0.16, amp * 0.9) + _tone(262, 0.28, amp * 0.75)
    elif kind == "angry":
        samples = _tone(220, 0.12, amp) + _tone(185, 0.22, amp * 1.1)
    elif kind == "curious":
        samples = _tone(880, 0.07, amp * 0.8) + _tone(1320, 0.14, amp)
    elif kind == "bump":
        samples = (
            _noise(0.05, amp * 0.7)
            + _tone(140, 0.12, amp * 1.2, attack=0.002, release=0.08)
            + _tone(880, 0.06, amp * 0.5)
        )
    elif kind == "wake_ok":
        samples = _tone(880, 0.07, amp) + _tone(1175, 0.07, amp) + _tone(1568, 0.16, amp)
    elif kind == "wake_on":
        samples = _sweep(400, 1200, 0.28, amp) + _tone(1400, 0.1, amp * 0.7)
    elif kind == "wake_fail":
        samples = _tone(440, 0.1, amp) + _tone(280, 0.22, amp)
    elif kind == "wake_off":
        samples = _tone(990, 0.08, amp) + _tone(520, 0.14, amp * 0.8)
    elif kind == "tread":
        samples = _tone(180, 0.05, amp * 0.55, attack=0.005, release=0.03)
        samples += _tone(210, 0.05, amp * 0.5, attack=0.005, release=0.03)
        samples += _tone(165, 0.08, amp * 0.45, attack=0.005, release=0.04)
    elif kind == "lift_up":
        samples = _sweep(220, 520, 0.22, amp * 0.7)
    elif kind == "lift_down":
        samples = _sweep(520, 220, 0.22, amp * 0.7)
    elif kind == "head_up":
        samples = _sweep(400, 720, 0.12, amp * 0.55)
    elif kind == "head_down":
        samples = _sweep(720, 400, 0.12, amp * 0.55)
    elif kind == "blink":
        samples = _tone(2400, 0.04, amp * 0.35, attack=0.002, release=0.02)
    elif kind == "ping":
        samples = _tone(1760, 0.06, amp * 0.7) + [0.0] * int(RATE * 0.08) + _tone(1760, 0.06, amp * 0.45)
    elif kind == "dance":
        samples = []
        for f in (392, 494, 587, 784, 587, 494):
            samples += _tone(f, 0.09, amp)
    elif kind == "sleepy":
        samples = _tone(196, 0.35, amp * 0.45) + _tone(165, 0.4, amp * 0.35)
    elif kind == "off":
        samples = _sweep(900, 200, 0.4, amp * 0.6)
    else:
        h = sum(ord(c) for c in event) % 400
        samples = _tone(500 + h, 0.12, amp)
    return _pack(samples)
