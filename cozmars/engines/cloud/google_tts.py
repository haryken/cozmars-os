"""Google HTTP TTS + đẩy audio/lệnh lên sim (queue, không chặn asyncio)."""

from __future__ import annotations

import base64
import json
import os
import queue
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

_cmd_q: queue.Queue | None = None
_sfx_q: queue.Queue | None = None
_mic_listen: dict | None = None
_play_samples = 0
_play_rate = 24000
_play_t0: float | None = None
_play_last: float | None = None
_stream_logged = False


def _ensure_worker() -> None:
    global _cmd_q
    if _cmd_q is not None:
        return
    _cmd_q = queue.Queue()

    def _run() -> None:
        while True:
            body = _cmd_q.get()
            if body is None:
                continue
            if body.get("op") == "mic_listen":
                latest = _mic_listen
                if latest is None:
                    continue
                if latest.get("gen") != body.get("gen"):
                    continue
                body = latest
            _post_sim(body)

    threading.Thread(target=_run, daemon=True, name="sim-tts").start()


def _ensure_sfx_worker() -> None:
    global _sfx_q
    if _sfx_q is not None:
        return
    _sfx_q = queue.Queue()

    def _run() -> None:
        while True:
            body = _sfx_q.get()
            if body is None:
                continue
            _post_sim(body)

    threading.Thread(target=_run, daemon=True, name="sim-sfx").start()


def _post_sim(body: dict) -> None:
    sim = os.environ.get("COZMARS_SIM_URL", "").rstrip("/")
    if not sim:
        return
    raw = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        sim + "/api/cmd",
        data=raw,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            resp.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"[TTS] sim play fail: {exc}", flush=True)


def sim_cmd(body: dict) -> None:
    _ensure_worker()
    assert _cmd_q is not None
    _cmd_q.put(body)


def sim_mic_listen(on: bool, idle: bool = False, reason: str = "") -> None:
    global _mic_listen
    gen = int((_mic_listen or {}).get("gen") or 0) + 1
    body = {"op": "mic_listen", "on": on, "idle": idle, "reason": reason, "source": "os", "gen": gen}
    _mic_listen = body
    sim_cmd(body)


def play_bytes(
    text: str,
    data: bytes | None,
    mime: str = "audio/mpeg",
    lang: str = "vi",
    stream: bool = False,
    kind: str = "tts",
) -> None:
    body: dict = {
        "op": "tts",
        "text": text,
        "lang": lang,
        "source": "os",
        "mime": mime,
        "stream": stream,
        "kind": kind,
    }
    if data:
        body["b64"] = base64.b64encode(data).decode("ascii")
    if kind == "sfx":
        _ensure_sfx_worker()
        assert _sfx_q is not None
        _sfx_q.put(body)
        return
    sim_cmd(body)


def reset_play() -> None:
    global _play_samples, _play_t0, _play_last, _stream_logged
    _play_samples = 0
    _play_t0 = None
    _play_last = None
    _stream_logged = False


def note_play(pcm: bytes, rate: int = 24000) -> None:
    global _play_samples, _play_t0, _play_last, _play_rate
    n = len(pcm) // 2
    if n <= 0:
        return
    _play_rate = rate
    now = time.monotonic()
    _play_last = now
    if _play_t0 is None:
        _play_t0 = now
    _play_samples += n


def play_duration() -> float:
    if _play_samples <= 0:
        return 0.0
    return _play_samples / float(_play_rate)


def speaker_remain() -> float:
    if _play_t0 is None or _play_samples <= 0:
        return 0.0
    dur = _play_samples / float(_play_rate)
    return dur - (time.monotonic() - _play_t0)


def last_note_age() -> float:
    if _play_last is None:
        return 99.0
    return time.monotonic() - _play_last


def play_wav(text: str, wav: bytes, lang: str = "vi", stream: bool = False) -> None:
    global _stream_logged
    if stream:
        if not _stream_logged:
            print(f"[TTS] xiaozhi stream {len(wav)} bytes…", flush=True)
            _stream_logged = True
    else:
        print(f"[TTS] xiaozhi wav {len(wav)} bytes  {text[:80]!r}", flush=True)
    play_bytes(text, wav, mime="audio/wav", lang=lang, stream=stream)


def say(text: str, lang: str = "vi") -> bytes | None:
    if not text:
        return None
    print(f"[TTS] google lang={lang} {text[:80]!r}", flush=True)
    q = urllib.parse.urlencode({"ie": "UTF-8", "q": text[:180], "tl": lang, "client": "tw-ob"})
    try:
        req = urllib.request.Request(
            "https://translate.google.com/translate_tts?" + q,
            headers={"User-Agent": "Mozilla/5.0 cozmars-os"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = resp.read()
        print(f"[TTS] got {len(data)} bytes", flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"[TTS] skip: {exc}", flush=True)
        play_bytes(text, None, lang=lang)
        return None
    play_bytes(text, data, mime="audio/mpeg", lang=lang)
    return data
