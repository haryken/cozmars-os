#!/usr/bin/env python3
"""Extract Vector SFX from WireOS Wwise .wem (IMA-ADPCM in a WAV wrapper) → assets/sfx."""

from __future__ import annotations

import json
import re
import struct
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SRC = Path(
    "/home/linh/Projects/wire-os/anki/victor/EXTERNALS/victor-audio-assets"
)
OUT_RATE = 22050
PREFERRED_HASH = "18FE9C92"

INDEX_TABLE = [-1, -1, -1, -1, 2, 4, 6, 8, -1, -1, -1, -1, 2, 4, 6, 8]
STEP_TABLE = [
    7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45,
    50, 55, 60, 66, 73, 80, 88, 97, 107, 118, 130, 143, 157, 173, 190, 209, 230,
    253, 279, 307, 337, 371, 408, 449, 494, 544, 598, 658, 724, 796, 876, 963,
    1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066, 2272, 2499, 2749, 3024, 3327,
    3660, 4026, 4428, 4871, 5358, 5894, 6484, 7132, 7845, 8630, 9493, 10442, 11487,
    12635, 13899, 15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794, 32767,
]


def _clamp(n: int, lo: int, hi: int) -> int:
    return lo if n < lo else hi if n > hi else n


def parse_riff(raw: bytes) -> tuple[int, int, int, int, bytes]:
    if raw[:4] != b"RIFF" or raw[8:12] != b"WAVE":
        raise ValueError("not RIFF WAVE")
    i = 12
    fmt = b""
    data = b""
    while i + 8 <= len(raw):
        cid = raw[i : i + 4]
        sz = int.from_bytes(raw[i + 4 : i + 8], "little")
        chunk = raw[i + 8 : i + 8 + sz]
        i += 8 + sz + (sz & 1)
        if cid == b"fmt ":
            fmt = chunk
        elif cid == b"data":
            data = chunk
    if len(fmt) < 16 or not data:
        raise ValueError("missing fmt/data")
    audio_fmt, ch, rate, _br, align, _bits = struct.unpack_from("<HHIIHH", fmt, 0)
    return audio_fmt, ch, rate, align, data


def decode_ima(data: bytes, channels: int, align: int) -> bytes:
    """Wwise Linux SFX: format tag 2, IMA-ADPCM blocks (4-byte header / channel)."""
    header = 4 * channels
    out: list[int] = []
    for off in range(0, len(data) - header + 1, align):
        block = data[off : off + align]
        if len(block) < header:
            break
        pred = [0] * channels
        index = [0] * channels
        p = 0
        for ch in range(channels):
            pred[ch] = int.from_bytes(block[p : p + 2], "little", signed=True)
            index[ch] = block[p + 2]
            p += 4
            out.append(pred[ch])
        nibble_i = 0
        while p < len(block):
            byte = block[p]
            p += 1
            for nibble in (byte & 0x0F, byte >> 4):
                ch = nibble_i % channels
                nibble_i += 1
                step = STEP_TABLE[_clamp(index[ch], 0, 88)]
                diff = step >> 3
                if nibble & 1:
                    diff += step >> 2
                if nibble & 2:
                    diff += step >> 1
                if nibble & 4:
                    diff += step
                pred[ch] = pred[ch] + diff if (nibble & 8) == 0 else pred[ch] - diff
                pred[ch] = _clamp(pred[ch], -32768, 32767)
                index[ch] = _clamp(index[ch] + INDEX_TABLE[nibble], 0, 88)
                out.append(pred[ch])
    return struct.pack("<" + "h" * len(out), *out)


def downmix(ch: int, pcm: bytes) -> bytes:
    if ch <= 1:
        return pcm
    n = len(pcm) // 2
    s = struct.unpack("<" + "h" * n, pcm)
    out = [int(sum(s[i : i + ch]) / ch) for i in range(0, n - ch + 1, ch)]
    return struct.pack("<" + "h" * len(out), *out)


def resample_mono(pcm: bytes, src_rate: int, dst_rate: int) -> bytes:
    if src_rate == dst_rate:
        return pcm
    n = len(pcm) // 2
    if n < 2:
        return pcm
    samples = struct.unpack("<" + "h" * n, pcm)
    out_n = max(1, int(round(n * dst_rate / src_rate)))
    out = []
    for i in range(out_n):
        x = i * (n - 1) / (out_n - 1)
        j = int(x)
        f = x - j
        a = samples[j]
        b = samples[j + 1] if j + 1 < n else a
        out.append(int(a + (b - a) * f))
    return struct.pack("<" + "h" * len(out), *out)


def peak16(pcm: bytes) -> int:
    peak = 0
    for i in range(0, len(pcm) - 1, 2):
        peak = max(peak, abs(int.from_bytes(pcm[i : i + 2], "little", signed=True)))
        if peak > 1000:
            return peak
    return peak


def write_wav(path: Path, pcm: bytes, rate: int) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)


def event_from_short(short: str) -> str:
    s = short.replace(".wav", "")
    if s.endswith("_WM"):
        s = s[:-3]
    s = re.sub(r"_\d{2}$", "", s)
    return s if s.startswith("Play__") else "Play__" + s


def codec_hash(path: str) -> str:
    return path.rsplit("_", 1)[-1].replace(".wem", "").upper() if path else ""


def load_wanted() -> set[str]:
    want: set[str] = set()
    cat = ROOT / "cozmars/engines/anim/sfx_catalog.json"
    act = ROOT / "cozmars/engines/anim/action_sfx.json"
    if cat.exists():
        want.update(json.loads(cat.read_text(encoding="utf-8")).keys())
    if act.exists():
        for evs in json.loads(act.read_text(encoding="utf-8")).values():
            want.update(evs)
    return want


def decode_wem(path: Path) -> tuple[int, bytes]:
    audio_fmt, ch, rate, align, payload = parse_riff(path.read_bytes())
    if audio_fmt == 1:
        pcm = payload
    else:
        pcm = decode_ima(payload, ch, align)
    pcm = downmix(ch, pcm)
    pcm = resample_mono(pcm, rate, OUT_RATE)
    return OUT_RATE, pcm


def main() -> int:
    src_root = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SRC
    meta = src_root / "metadata" / "Victor_Linux" / "Victor_SFX.json"
    wem_dir = src_root / "victor_robot" / "victor_linux"
    if not meta.exists() or not wem_dir.is_dir():
        print(f"missing Vector audio at {src_root}", file=sys.stderr)
        return 1
    files = json.loads(meta.read_text(encoding="utf-8"))["SoundBanksInfo"]["SoundBanks"][0]["IncludedMemoryFiles"]
    want = load_wanted()
    out_dir = ROOT / "assets" / "sfx"
    out_dir.mkdir(parents=True, exist_ok=True)

    grouped: dict[str, list[tuple[int, Path]]] = {}
    for f in files:
        ev = event_from_short(f.get("ShortName") or "")
        if ev not in want:
            continue
        h = codec_hash(f.get("Path") or "")
        if h and h != PREFERRED_HASH:
            continue
        wem = wem_dir / f"{f['Id']}.wem"
        if not wem.exists():
            continue
        grouped.setdefault(ev, []).append((int(f["Id"]), wem))

    ok = fail = 0
    for ev, items in sorted(grouped.items()):
        items.sort()
        wrote = 0
        for i, (_id, wem) in enumerate(items):
            name = f"{ev}.wav" if wrote == 0 else f"{ev}.{wrote + 1}.wav"
            try:
                _rate, pcm = decode_wem(wem)
                if peak16(pcm) <= 200:
                    fail += 1
                    continue
                write_wav(out_dir / name, pcm, OUT_RATE)
                ok += 1
                wrote += 1
            except Exception as exc:  # noqa: BLE001
                fail += 1
                print(f"fail {wem.name} {ev}: {exc}")
    print(f"extracted {ok} wavs ({fail} skip/fail) events={len(grouped)} → {out_dir}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
