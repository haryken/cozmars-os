"""Xiaozhi Opus: decode 24 kHz TTS + encode 16 kHz mic (60 ms frames)."""

from __future__ import annotations

import ctypes
import io
import sys
import wave
from pathlib import Path

_lib = None
_create = None
_decode = None
_destroy = None
_enc_create = None
_encode = None
_enc_destroy = None

OPUS_APPLICATION_VOIP = 2048


def _find_lib() -> Path | None:
    names = ("libopus.so.0", "libopus.so", "opus.dll")
    roots = [
        Path(__file__).resolve().parent / "native",
        Path(__file__).resolve().parent,
    ]
    for p in sys.path:
        roots.append(Path(p) / "lib")
        roots.append(Path(p))
    seen: set[str] = set()
    for root in roots:
        key = str(root)
        if key in seen:
            continue
        seen.add(key)
        for name in names:
            cand = root / name
            if cand.is_file():
                return cand
    return None


def _load():
    global _lib, _create, _decode, _destroy, _enc_create, _encode, _enc_destroy
    if _lib is not None:
        return True
    path = _find_lib()
    if path is None:
        print("[CLOUD] MISS libopus — TTS Xiaozhi không decode được Opus", flush=True)
        return False
    lib = ctypes.CDLL(str(path))
    lib.opus_decoder_create.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
    lib.opus_decoder_create.restype = ctypes.c_void_p
    lib.opus_decode.argtypes = [
        ctypes.c_void_p,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_int16),
        ctypes.c_int,
        ctypes.c_int,
    ]
    lib.opus_decode.restype = ctypes.c_int
    lib.opus_decoder_destroy.argtypes = [ctypes.c_void_p]
    lib.opus_decoder_destroy.restype = None
    lib.opus_encoder_create.argtypes = [
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_int),
    ]
    lib.opus_encoder_create.restype = ctypes.c_void_p
    lib.opus_encode.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_int16),
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
    ]
    lib.opus_encode.restype = ctypes.c_int
    lib.opus_encoder_destroy.argtypes = [ctypes.c_void_p]
    lib.opus_encoder_destroy.restype = None
    _lib = lib
    _create, _decode, _destroy = lib.opus_decoder_create, lib.opus_decode, lib.opus_decoder_destroy
    _enc_create, _encode, _enc_destroy = lib.opus_encoder_create, lib.opus_encode, lib.opus_encoder_destroy
    print(f"[CLOUD] Opus codec {path}", flush=True)
    return True


class OpusDecoder:
    def __init__(self, rate: int = 24000) -> None:
        if not _load():
            raise RuntimeError("libopus missing")
        err = ctypes.c_int()
        self._dec = _create(rate, 1, ctypes.byref(err))
        if not self._dec or err.value != 0:
            raise RuntimeError(f"opus_decoder_create {err.value}")
        self.rate = rate
        self._pcm = (ctypes.c_int16 * 5760)()

    def decode(self, packet: bytes) -> bytes:
        n = _decode(self._dec, packet, len(packet), self._pcm, 5760, 0)
        if n < 0:
            return b""
        return ctypes.string_at(self._pcm, n * 2)

    def close(self) -> None:
        if self._dec:
            _destroy(self._dec)
            self._dec = None


class OpusEncoder:
    """16 kHz mono, 60 ms frames (960 samples) — khớp hello Xiaozhi."""

    def __init__(self, rate: int = 16000, frame_ms: int = 60) -> None:
        if not _load():
            raise RuntimeError("libopus missing")
        err = ctypes.c_int()
        self._enc = _enc_create(rate, 1, OPUS_APPLICATION_VOIP, ctypes.byref(err))
        if not self._enc or err.value != 0:
            raise RuntimeError(f"opus_encoder_create {err.value}")
        self.rate = rate
        self.frame_size = rate * frame_ms // 1000
        self.frame_bytes = self.frame_size * 2
        self._out = ctypes.create_string_buffer(4000)

    def encode(self, pcm: bytes) -> bytes:
        if len(pcm) != self.frame_bytes:
            if len(pcm) < self.frame_bytes:
                pcm = pcm + b"\x00" * (self.frame_bytes - len(pcm))
            else:
                pcm = pcm[: self.frame_bytes]
        arr = (ctypes.c_int16 * self.frame_size).from_buffer_copy(pcm)
        n = _encode(self._enc, arr, self.frame_size, self._out, len(self._out))
        if n < 0:
            return b""
        return self._out.raw[:n]

    def close(self) -> None:
        if self._enc:
            _enc_destroy(self._enc)
            self._enc = None


def pcm16_to_wav(pcm: bytes, rate: int = 24000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return buf.getvalue()
