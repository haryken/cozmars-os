"""Xiaozhi WS — OTA + mic Opus / text listen → cloud LLM. Không LLM local."""

from __future__ import annotations

import json
import os
import random
import re
import time
import unicodedata
import uuid
from collections import deque
from pathlib import Path
from typing import Any, Optional
from urllib import error as urlerror
from urllib import request as urlrequest

OTA_DEFAULT = "https://api.tenclass.net/"
WSS_DEFAULT = "wss://api.tenclass.net/xiaozhi/v1/"

# Shared tenclass slots (giống Vector vi_pool) — chat được không cần xiaozhi.me.
_VI_POOL = [
    "1c:db:d4:b5:73:3c",
    "58:a0:23:a6:fe:31",
    "a8:b5:44:dd:e3:cf",
    "1c:db:d4:b5:74:7c",
    "1c:db:d4:b5:6a:d8",
    "dc:b4:d9:0c:a4:9c",
    "dc:b4:d9:0c:a4:80",
    "28:df:eb:02:6c:7d",
]

_ws = None
_session = None
_session_id = ""
_cfg: dict[str, Any] = {}
_inbox = None
_reader_task = None
_turn_lock = None
_pcm_q = None
_pcm_pre: deque[bytes] = deque(maxlen=60)
_pcm_end_pending = False
_tts_idle = None
_tts_idle_pending = False
_session_bye = False

_WAKE_KEYS = (
    "xin chao cozmars",
    "xin chao cozmo",
    "xin chao cosmos",
    "xin chao robot",
    "xin chao",
    "chao cozmars",
    "chao cozmo",
    "chao cosmos",
    "chao robot",
    "oi cozmars",
    "oi cozmo",
    "oi robot",
    "nay cozmars",
    "nay cozmo",
    "thuc day",
    "hey cozmars",
    "hey cosmos",
    "hey kozmars",
    "hey cozmo",
    "hey kozmo",
    "hey vector",
    "hey coz",
    "hey cos",
    "hey koz",
    "hey co",
    "hay cozmars",
    "ok google",
    "xiaozhi",
    "cozmars",
    "cozmo",
    "cosmos",
    "vector",
    "hello",
    "hey",
)

_WAKE_JUNK = {
    "cosmos",
    "cosmo",
    "cosm",
    "cozmo",
    "mars",
    "hey",
    "vector",
    "ok",
    "google",
    "xiaozhi",
    "cozmars",
    "hello",
    "chao",
}


def _home() -> Path:
    override = os.environ.get("COZMARS_HOME")
    return Path(override) if override else Path.home() / ".cozmars"


def config_path() -> Path:
    return _home() / "xiaozhi.json"


def load_cfg() -> dict[str, Any]:
    global _cfg
    path = config_path()
    cfg: dict[str, Any] = {
        "enabled": True,
        "ota_base_url": os.environ.get("COZMARS_XZ_OTA", OTA_DEFAULT),
        "endpoint": os.environ.get("COZMARS_XZ_WS", WSS_DEFAULT),
        "device_id": os.environ.get("COZMARS_XZ_DID", ""),
        "client_id": os.environ.get("COZMARS_XZ_CID", ""),
        "token": os.environ.get("COZMARS_XZ_TOKEN", ""),
        "protocol_version": 1,
        "identity_mode": "vi_pool",
        "activation_code": "",
    }
    if path.exists():
        try:
            disk = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(disk, dict):
                cfg.update(disk)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[CLOUD] xiaozhi.json hỏng — {exc}", flush=True)
    if not cfg.get("device_id"):
        cfg["device_id"] = random.choice(_VI_POOL)
    if not cfg.get("client_id"):
        cfg["client_id"] = str(uuid.uuid4())
    if not cfg.get("ota_base_url"):
        cfg["ota_base_url"] = OTA_DEFAULT
    if not cfg.get("endpoint"):
        cfg["endpoint"] = WSS_DEFAULT
    cfg["ota_base_url"] = str(cfg["ota_base_url"]).rstrip("/") + "/"
    _cfg = cfg
    return cfg


def save_cfg(cfg: dict[str, Any]) -> None:
    global _cfg
    _cfg = cfg
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


def gen_random_mac() -> str:
    b = bytearray(os.urandom(6))
    b[0] = (b[0] | 0x02) & 0xFE
    return ":".join(f"{x:02x}" for x in b)


def _in_pool(mac: str) -> bool:
    return (mac or "").strip().lower() in {m.lower() for m in _VI_POOL}


def probe() -> dict:
    cfg = load_cfg()
    try:
        import aiohttp  # noqa: F401

        print("[CLOUD] aiohttp OK — Xiaozhi WS dùng aiohttp", flush=True)
        cfg["ws_lib"] = True
    except Exception as exc:  # noqa: BLE001
        print(f"[CLOUD] MISS aiohttp — Xiaozhi WS chưa mở ({exc})", flush=True)
        cfg["ws_lib"] = False
    print(
        f"[CLOUD] Xiaozhi ota={cfg['ota_base_url']} id={cfg['device_id']} "
        f"endpoint={cfg.get('endpoint') or '(chưa)'}",
        flush=True,
    )
    return cfg


def _ota_post(cfg: dict[str, Any]) -> dict:
    url = str(cfg["ota_base_url"]).rstrip("/") + "/xiaozhi/ota/"
    body = json.dumps(
        {
            "version": 2,
            "language": "vi-VN",
            "mac_address": cfg["device_id"],
            "uuid": cfg["client_id"],
            "platform": "linux",
            "arch": "x86_64",
            "hostname": "cozmars",
            "application": {"name": "cozmars-os", "version": "1.6.0"},
            "board": {"type": "cozmars-os", "name": "cozmars", "vendor": "rcute"},
        }
    ).encode("utf-8")
    req = urlrequest.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Device-Id": cfg["device_id"],
            "Client-Id": cfg["client_id"],
            "User-Agent": "cozmars-os/1.6",
            "Accept-Language": "vi-VN",
            "Activation-Version": "1",
        },
    )
    with urlrequest.urlopen(req, timeout=20) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def _apply_ota(cfg: dict[str, Any], result: dict) -> str:
    act = result.get("activation") or {}
    ws = result.get("websocket") or {}
    code = str(act.get("code") or "").strip()
    cfg["activation_code"] = code
    if ws.get("url"):
        cfg["endpoint"] = str(ws["url"]).strip()
    if ws.get("token"):
        cfg["token"] = str(ws["token"]).strip()
    save_cfg(cfg)
    if code:
        print(f"[CLOUD] Xiaozhi chưa ghép — mã {code} tại xiaozhi.me", flush=True)
    else:
        print(f"[CLOUD] Xiaozhi đã liên kết id={cfg.get('device_id')}", flush=True)
    return code


def ota_hello(base: str = "") -> dict:
    cfg = load_cfg()
    if base:
        cfg["ota_base_url"] = str(base).rstrip("/") + "/"
    try:
        result = _ota_post(cfg)
    except (urlerror.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        print(f"[CLOUD] Xiaozhi OTA fail: {exc}", flush=True)
        return {}
    _apply_ota(cfg, result)
    return result


def generate_code(*, identity_mode: str = "", new_device: bool = False) -> dict:
    """WireOS generate_code: POST OTA → mã 6 số hoặc đã liên kết."""
    cfg = load_cfg()
    mode = (identity_mode or cfg.get("identity_mode") or "custom").strip().lower()
    if mode not in ("vi_pool", "custom"):
        mode = "custom"
    cfg["identity_mode"] = mode

    if mode == "vi_pool":
        if not cfg.get("device_id") or not _in_pool(str(cfg.get("device_id"))):
            cfg["device_id"] = random.choice(_VI_POOL)
        if not cfg.get("client_id"):
            cfg["client_id"] = str(uuid.uuid4())
    else:
        # Custom: MAC pool / trống / lấy mã mới → MAC ngẫu nhiên chưa ghép → server cấp 6 số.
        need_new = new_device or not cfg.get("device_id") or _in_pool(str(cfg.get("device_id")))
        if need_new:
            cfg["device_id"] = gen_random_mac()
            cfg["client_id"] = str(uuid.uuid4())
            cfg["token"] = ""
            cfg["activation_code"] = ""
        elif not cfg.get("client_id"):
            cfg["client_id"] = str(uuid.uuid4())

    save_cfg(cfg)
    try:
        result = _ota_post(cfg)
    except (urlerror.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        print(f"[CLOUD] Xiaozhi generate_code fail: {exc}", flush=True)
        return {"status": "error", "message": str(exc), "config": cfg}

    code = _apply_ota(cfg, result)
    linked = not bool(code)
    if linked:
        msg = (
            f"Device ID {cfg['device_id']} đã liên kết với tài khoản Xiaozhi. "
            "Đánh thức robot (hey cozmars) và dùng bình thường."
        )
    else:
        msg = (
            f"Chưa kích hoạt — nhập mã {code} tại xiaozhi.me để liên kết robot với tài khoản Xiaozhi."
        )
    return {
        "status": "success",
        "code": code,
        "linked": linked,
        "device_id": cfg["device_id"],
        "client_id": cfg["client_id"],
        "endpoint": cfg.get("endpoint") or "",
        "message": msg,
        "config": load_cfg(),
    }


def notify_tts_idle() -> None:
    global _tts_idle_pending
    ev = _tts_idle
    if ev is not None:
        ev.set()
    else:
        _tts_idle_pending = True


def push_pcm(data: bytes) -> bool:
    """PCM s16le 16 kHz từ sim /api/mic — buffer nếu ListenStart chưa kịp."""
    if not data:
        return end_pcm()
    q = _pcm_q
    if q is None:
        _pcm_pre.append(data)
        return True
    try:
        q.put_nowait(data)
        return True
    except Exception:
        return False


def end_pcm() -> bool:
    """Chỉ kết thúc lượt đang ListenStart — không để mic_end cũ giết wake sau."""
    q = _pcm_q
    if q is None:
        return True
    try:
        q.put_nowait(b"")
        return True
    except Exception:
        return False


def _fold(text: str) -> str:
    t = unicodedata.normalize("NFD", text or "")
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = t.replace("đ", "d").replace("Đ", "d").lower()
    t = re.sub(r"[^a-z0-9\s]+", " ", t)
    t = re.sub(r"\bco mars\b", "cozmars", t)
    t = re.sub(r"\bkoz mars\b", "cozmars", t)
    return re.sub(r"\s+", " ", t).strip()


def _is_bye(text: str) -> bool:
    t = _fold(text)
    if not t:
        return False
    keys = (
        "tam biet",
        "goodbye",
        "good bye",
        "bye bye",
        "hen gap lai",
        "ngu ngon",
        "good night",
        "see you",
        "chao tam biet",
    )
    if t in ("bye", "tam biet"):
        return True
    return any(k in t for k in keys)


def listen(brain) -> None:
    print("[CLOUD] Xiaozhi listen không text — chờ câu sau wake", flush=True)
    brain.handle_intent("intent_greeting_hello")


def mcp_call(brain, tool: str, args: dict | None = None) -> str:
    from . import mcp

    return mcp.dispatch(brain, tool, args or {})


def _wake_only(text: str) -> bool:
    t = _fold(text)
    if not t or t in ("manual", "button"):
        return True
    keys = _WAKE_KEYS
    rest = t
    for k in sorted(keys, key=len, reverse=True):
        rest = rest.replace(k, " ")
    leftover = rest.strip(" ,.-")
    if leftover.lower() in _WAKE_JUNK:
        return True
    return not leftover


def strip_wake(text: str) -> str:
    t = (text or "").strip()
    low = _fold(t)
    keys = _WAKE_KEYS
    for k in sorted(keys, key=len, reverse=True):
        if low.startswith(k):
            out = low[len(k) :].strip(" ,.-")
            if out in _WAKE_JUNK:
                return ""
            return out
    if low in _WAKE_JUNK:
        return ""
    return t


async def chat(brain, text: str) -> dict:
    """Gửi câu (đã STT) lên Xiaozhi. played=True nếu đã phát audio Xiaozhi (không Google)."""
    import asyncio

    global _turn_lock, _session_bye
    if _turn_lock is None:
        _turn_lock = asyncio.Lock()

    utterance = strip_wake(text)
    audio = _wake_only(text) or not utterance

    cfg = load_cfg()
    if not cfg.get("endpoint") or not cfg.get("token"):
        ota_hello()
        cfg = load_cfg()
    if cfg.get("activation_code") and not cfg.get("token"):
        code = cfg["activation_code"]
        return {"text": f"Chưa liên kết Xiaozhi. Vào xiaozhi.me nhập mã {code}.", "played": False}

    async with _turn_lock:
        _session_bye = False
        try:
            reply, played = await _dialog(brain, cfg, None if audio else utterance)
        except Exception as exc:  # noqa: BLE001
            print(f"[CLOUD] Xiaozhi turn fail: {exc}", flush=True)
            await _close_ws()
            from . import google_tts

            google_tts.sim_mic_listen(False, idle=True)
            if _session_bye:
                return {"text": "", "played": False, "path": "xiaozhi-bye"}
            ota_hello()
            try:
                _session_bye = False
                reply, played = await _dialog(brain, load_cfg(), None if audio else utterance)
            except Exception as exc2:  # noqa: BLE001
                print(f"[CLOUD] Xiaozhi retry fail: {exc2}", flush=True)
                google_tts.sim_mic_listen(False, idle=True)
                return {"text": f"Không nối được Xiaozhi: {exc2}", "played": False}
    return {"text": reply, "played": played, "path": "xiaozhi"}


async def _ensure_ws(cfg: dict[str, Any]):
    global _ws, _session, _session_id, _inbox, _reader_task
    import asyncio
    from aiohttp import ClientSession, ClientTimeout, WSMsgType

    if _ws is not None and not _ws.closed:
        return _ws

    await _close_ws()
    endpoint = cfg.get("endpoint") or WSS_DEFAULT
    token = str(cfg.get("token") or "").strip()
    if token and not token.lower().startswith("bearer "):
        token = "Bearer " + token
    headers = {
        "Protocol-Version": str(cfg.get("protocol_version") or 1),
        "Device-Id": cfg.get("device_id") or "",
        "Client-Id": cfg.get("client_id") or "",
    }
    if token:
        headers["Authorization"] = token

    _session = ClientSession(timeout=ClientTimeout(total=None, sock_connect=20))
    _ws = await _session.ws_connect(endpoint, headers=headers, heartbeat=20)
    hello = {
        "type": "hello",
        "version": cfg.get("protocol_version") or 1,
        "transport": "websocket",
        "features": {"mcp": True, "aec": False},
        "audio_params": {
            "format": "opus",
            "sample_rate": 16000,
            "channels": 1,
            "frame_duration": 60,
        },
    }
    await _ws.send_json(hello)

    for _ in range(12):
        msg = await _ws.receive(timeout=15)
        if msg.type != WSMsgType.TEXT:
            continue
        data = json.loads(msg.data)
        typ = data.get("type")
        if typ == "hello":
            _session_id = str(data.get("session_id") or "")
            print(f"[CLOUD] Xiaozhi WSS session={_session_id}", flush=True)
            _inbox = asyncio.Queue()
            _reader_task = asyncio.create_task(_ws_reader(), name="xz-ws-reader")
            return _ws
        if typ == "mcp":
            await _handle_mcp(_ws, None, data)
    raise RuntimeError("không nhận hello từ Xiaozhi")


async def _ws_reader() -> None:
    from aiohttp import WSMsgType

    assert _ws is not None and _inbox is not None
    try:
        while _ws is not None and not _ws.closed:
            msg = await _ws.receive()
            await _inbox.put(msg)
            if msg.type in (WSMsgType.CLOSED, WSMsgType.ERROR, WSMsgType.CLOSING):
                break
    except Exception as exc:  # noqa: BLE001
        print(f"[CLOUD] Xiaozhi reader: {exc}", flush=True)
        if _inbox is not None:
            await _inbox.put(exc)


async def _close_ws() -> None:
    global _ws, _session, _session_id, _inbox, _reader_task
    if _reader_task is not None:
        _reader_task.cancel()
        try:
            await _reader_task
        except Exception:
            pass
        _reader_task = None
    if _ws is not None:
        try:
            await _ws.close()
        except Exception:
            pass
        _ws = None
    if _session is not None:
        try:
            await _session.close()
        except Exception:
            pass
        _session = None
    _session_id = ""
    _inbox = None


async def _drain_inbox() -> None:
    while _inbox is not None and not _inbox.empty():
        try:
            _inbox.get_nowait()
        except Exception:
            break


def _rms16(pcm: bytes) -> float:
    n = len(pcm) // 2
    if n <= 0:
        return 0.0
    total = 0
    for i in range(0, n * 2, 2):
        s = int.from_bytes(pcm[i : i + 2], "little", signed=True)
        total += s * s
    return (total / n) ** 0.5


async def _dialog(brain, cfg: dict[str, Any], first_text: str | None) -> tuple[str, bool]:
    from . import google_tts

    global _session_bye
    parts: list[str] = []
    played_any = False
    try:
        if first_text:
            reply, played = await _ws_turn(brain, cfg, first_text)
            if reply:
                parts.append(reply)
            played_any |= played
            if _session_bye:
                print("[CLOUD] Xiaozhi tạm biệt — đóng mic, chờ wake", flush=True)
                return " ".join(parts).strip(), played_any
        for n in range(20):
            if _session_bye:
                break
            reply, played, heard = await _audio_turn(brain, cfg, use_pre=(n == 0 and not first_text))
            if _session_bye:
                print("[CLOUD] Xiaozhi tạm biệt — đóng mic, chờ wake", flush=True)
                if reply:
                    parts.append(reply)
                played_any |= played
                break
            if not heard:
                if n == 0 and not first_text:
                    print("[CLOUD] Xiaozhi — không có câu hỏi sau wake", flush=True)
                else:
                    print("[CLOUD] Xiaozhi hết phiên — chờ wake", flush=True)
                break
            if reply:
                parts.append(reply)
            played_any |= played
            print("[CLOUD] Xiaozhi relisten after playback", flush=True)
    finally:
        google_tts.sim_mic_listen(False, idle=True)
        await _close_ws()
    return " ".join(parts).strip(), played_any


async def _wait_speaker() -> None:
    import asyncio

    global _tts_idle, _tts_idle_pending

    from . import google_tts

    remain = google_tts.speaker_remain() + 0.5
    full = google_tts.play_duration() + 0.8
    timeout = max(remain, full, 2.0)
    _tts_idle = asyncio.Event()
    if _tts_idle_pending:
        _tts_idle.set()
        _tts_idle_pending = False
    print(f"[CLOUD] Xiaozhi wait speaker ≤{timeout * 1000:.0f}ms", flush=True)
    try:
        await asyncio.wait_for(_tts_idle.wait(), timeout=timeout + 2.5)
        print("[CLOUD] Xiaozhi speaker idle (loa máy xong)", flush=True)
    except asyncio.TimeoutError:
        print("[CLOUD] Xiaozhi speaker idle timeout — relisten", flush=True)
    await asyncio.sleep(0.35)
    google_tts.reset_play()
    _tts_idle = None


async def _ws_turn(brain, cfg: dict[str, Any], utterance: str) -> tuple[str, bool]:
    ws = await _ensure_ws(cfg)
    await _drain_inbox()
    await ws.send_json(
        {
            "type": "listen",
            "state": "detect",
            "text": utterance,
            "source": "text",
            "session_id": _session_id,
        }
    )
    print(f"[CLOUD] Xiaozhi listen detect {utterance!r}", flush=True)
    return await _collect_reply(brain, ws, utterance)


async def _audio_turn(brain, cfg: dict[str, Any], use_pre: bool = False) -> tuple[str, bool, bool]:
    import asyncio

    global _pcm_q, _pcm_end_pending

    from . import google_tts
    from .opus_pcm import OpusEncoder

    ws = await _ensure_ws(cfg)
    await _drain_inbox()
    _pcm_q = asyncio.Queue(maxsize=200)
    if use_pre:
        while _pcm_pre:
            chunk = _pcm_pre.popleft()
            if not chunk:
                continue
            try:
                _pcm_q.put_nowait(chunk)
            except Exception:
                break
    else:
        _pcm_pre.clear()
    _pcm_end_pending = False

    enc = None
    frames = 0
    try:
        enc = OpusEncoder(16000, 60)
    except Exception as exc:  # noqa: BLE001
        print(f"[CLOUD] Xiaozhi encoder off — {exc}", flush=True)
        _pcm_q = None
        return "Không encode được mic (thiếu libopus).", False, False

    google_tts.sim_mic_listen(True)
    await asyncio.sleep(0.4)
    await ws.send_json(
        {
            "type": "listen",
            "state": "start",
            "mode": "manual",
            "session_id": _session_id,
        }
    )
    print("[CLOUD] Xiaozhi ListenStart — chờ mic PCM", flush=True)

    buf = bytearray()
    speech = False
    quiet_ms = 0
    got_pcm = False
    t0 = time.monotonic()
    first_deadline = t0 + 6.0
    speech_deadline = t0 + 10.0
    echo_gate = t0 + 0.6
    try:
        while time.monotonic() - t0 < 12.0:
            try:
                chunk = await asyncio.wait_for(_pcm_q.get(), timeout=0.2)
            except asyncio.TimeoutError:
                chunk = None
            if chunk == b"":
                break
            if chunk:
                got_pcm = True
                now = time.monotonic()
                if now < echo_gate:
                    continue
                buf.extend(chunk)
                rms = _rms16(chunk)
                dur_ms = (len(chunk) // 2) * 1000 / 16000
                if rms > 900:
                    speech = True
                    quiet_ms = 0
                elif speech:
                    quiet_ms += dur_ms
                    if quiet_ms > 1200:
                        break
                elif now > speech_deadline:
                    print("[CLOUD] Xiaozhi ListenStart — im lặng, hết phiên", flush=True)
                    break
            elif not got_pcm and time.monotonic() > first_deadline:
                print("[CLOUD] Xiaozhi ListenStart — không có PCM từ mic", flush=True)
                break
            while len(buf) >= enc.frame_bytes:
                frame = bytes(buf[: enc.frame_bytes])
                del buf[: enc.frame_bytes]
                pkt = enc.encode(frame)
                if pkt:
                    await ws.send_bytes(pkt)
                    frames += 1
                    if frames == 1 or frames % 25 == 0:
                        print(f"[CLOUD] Xiaozhi uplink opus frames={frames}", flush=True)
        if buf:
            pkt = enc.encode(bytes(buf))
            if pkt:
                await ws.send_bytes(pkt)
                frames += 1
    finally:
        enc.close()
        _pcm_q = None
        _pcm_pre.clear()

    await ws.send_json(
        {
            "type": "listen",
            "state": "stop",
            "session_id": _session_id,
        }
    )
    print(f"[CLOUD] Xiaozhi ListenStop frames={frames} speech={speech}", flush=True)
    google_tts.sim_mic_listen(False)
    if frames == 0 or not speech:
        return "", False, False
    reply, played = await _collect_reply(brain, ws, "")
    return reply, played, True


async def _collect_reply(brain, ws, hint: str) -> tuple[str, bool]:
    import asyncio
    from aiohttp import WSMsgType

    global _session_bye

    from . import google_tts
    from .opus_pcm import OpusDecoder, pcm16_to_wav

    sentences: list[str] = []
    llm_bits: list[str] = []
    pending = bytearray()
    flushed = 0
    opus_n = 0
    dec = None
    try:
        dec = OpusDecoder(24000)
    except Exception as exc:  # noqa: BLE001
        print(f"[CLOUD] Opus off — {exc}", flush=True)

    google_tts.reset_play()
    flush_bytes = 24000 * 2 // 8  # ~125 ms

    def _flush(final: bool = False) -> None:
        nonlocal flushed
        if not pending:
            return
        if not final and len(pending) < flush_bytes:
            return
        chunk = bytes(pending)
        pending.clear()
        wav = pcm16_to_wav(chunk, 24000)
        label = (sentences[-1] if sentences else hint) or ""
        google_tts.note_play(chunk, 24000)
        google_tts.play_wav(label, wav, stream=True)
        flushed += len(chunk)

    deadline = 45.0
    t0 = time.monotonic()
    while time.monotonic() - t0 < deadline:
        if _inbox is None:
            raise RuntimeError("WSS inbox mất")
        try:
            msg = await asyncio.wait_for(_inbox.get(), timeout=max(1.0, deadline - (time.monotonic() - t0)))
        except asyncio.TimeoutError:
            break
        if isinstance(msg, Exception):
            raise msg
        if msg.type == WSMsgType.BINARY:
            opus_n += 1
            if dec is not None and msg.data:
                pending.extend(dec.decode(bytes(msg.data)))
                _flush()
            continue
        if msg.type in (WSMsgType.CLOSED, WSMsgType.ERROR, WSMsgType.CLOSING):
            _session_bye = True
            print("[CLOUD] Xiaozhi WSS đóng — hết phiên, chờ wake", flush=True)
            await _close_ws()
            break
        if msg.type != WSMsgType.TEXT:
            continue
        data = json.loads(msg.data)
        typ = data.get("type")
        if typ == "stt" and data.get("text"):
            print(f"[CLOUD] Xiaozhi STT cloud: {data.get('text')!r}", flush=True)
            if _is_bye(str(data.get("text") or "")):
                _session_bye = True
                print("[CLOUD] Xiaozhi STT tạm biệt — sẽ đóng phiên sau TTS", flush=True)
        elif typ == "llm" and data.get("text"):
            llm_bits.append(str(data["text"]))
        elif typ == "tts":
            state = data.get("state")
            if state == "sentence_start" and data.get("text"):
                sentences.append(str(data["text"]))
                print(f"[CLOUD] Xiaozhi TTS: {data['text']}", flush=True)
                _flush(final=True)
            if state == "stop":
                break
        elif typ == "mcp":
            await _handle_mcp(ws, brain, data)
        elif typ == "error":
            raise RuntimeError(data.get("error") or data.get("text") or "server error")
        elif typ == "goodbye":
            _session_bye = True
            print("[CLOUD] Xiaozhi goodbye — đóng WSS + mic, chờ wake", flush=True)
            await _close_ws()
            break

    _flush(final=True)
    if dec is not None:
        dec.close()
    reply = " ".join(sentences).strip() or "".join(llm_bits).strip()
    played = flushed > 0
    if played:
        print(f"[CLOUD] Xiaozhi speaker opus_frames={opus_n} pcm={flushed}", flush=True)
        await _wait_speaker()
    elif not reply:
        reply = "Mình nghe rồi nhưng cloud chưa trả lời."
    return reply, played


async def _handle_mcp(ws, brain, data: dict) -> None:
    payload = data.get("payload") if isinstance(data.get("payload"), dict) else data
    method = str(payload.get("method") or "")
    req_id = payload.get("id")
    params = payload.get("params") if isinstance(payload.get("params"), dict) else {}
    result: Any = {}
    if method == "initialize":
        result = {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "cozmars-os", "version": "1.6.0"},
        }
    elif method == "tools/list":
        from .mcp import TOOL_TO_INTENT

        tools = []
        for name in TOOL_TO_INTENT:
            tools.append(
                {
                    "name": name,
                    "description": name,
                    "inputSchema": {"type": "object", "properties": {}},
                }
            )
        result = {"tools": tools}
    elif method == "tools/call":
        if brain is None:
            print("[CLOUD] Xiaozhi MCP tools/call trước khi brain sẵn sàng", flush=True)
            return
        name = str(params.get("name") or "")
        args = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
        out = mcp_call(brain, name, args)
        result = {"content": [{"type": "text", "text": str(out)}]}
    elif method in ("notifications/cancelled", "notifications/initialized"):
        return
    else:
        print(f"[CLOUD] Xiaozhi MCP skip {method}", flush=True)
        return
    await ws.send_json(
        {
            "type": "mcp",
            "session_id": _session_id,
            "payload": {"jsonrpc": "2.0", "id": req_id, "result": result},
        }
    )
