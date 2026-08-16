"""Splash ST7789 lúc boot — giống vic-bootAnim (WireOS).

Chạy sớm qua systemd, vẽ logo đến khi Cozmars SIGTERM rồi nhả màn (không xóa frame).
"""

from __future__ import annotations

import json
import os
import signal
import socket
import time
import uuid
from pathlib import Path

W, H = 240, 135
CYAN = (0, 229, 255)
DIM = (0, 40, 48)
WHITE = (220, 245, 255)
_stop = False


def _serial() -> str:
    mac = hex(uuid.getnode())[2:].zfill(12)
    return mac[-4:].upper()


def _conf() -> dict:
    for p in (
        Path(os.environ.get("COZMARS_HOME", "")) / "conf.json" if os.environ.get("COZMARS_HOME") else None,
        Path("/home/pi/.cozmars/conf.json"),
        Path.home() / ".cozmars" / "conf.json",
        Path(__file__).resolve().parent.parent / "config" / "conf.json",
    ):
        if p and p.is_file():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
    return {"screen": {"cs": 8, "dc": 6, "rst": 5}, "servo": {"backlight": {"channel": 15}, "freq": 60}}


def _hostname() -> str:
    try:
        return socket.gethostname() or "cozmars"
    except Exception:
        return "cozmars"


def _font(size: int):
    from PIL import ImageFont

    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ):
        if os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def render_frame(tick: int) -> "Image.Image":
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (W, H), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    title = _font(28)
    small = _font(14)
    draw.text((48, 22), "Cozmars", fill=CYAN, font=title)
    draw.text((72, 58), _serial(), fill=WHITE, font=small)
    draw.text((38, 78), "booting…", fill=DIM, font=small)
    # 3 chấm nhấp — biết máy còn sống lúc đợi systemd.
    phase = tick % 3
    for i in range(3):
        x = 96 + i * 18
        on = i == phase
        r = 5 if on else 3
        col = CYAN if on else DIM
        draw.ellipse((x - r, 108 - r, x + r, 108 + r), fill=col)
    return img


def _open_st7789(conf: dict):
    import board
    import digitalio
    import adafruit_rgb_display.st7789 as st7789

    scr = conf.get("screen") or {}
    spi = board.SPI()
    cs = digitalio.DigitalInOut(getattr(board, f"D{int(scr.get('cs', 8))}"))
    dc = digitalio.DigitalInOut(getattr(board, f"D{int(scr.get('dc', 6))}"))
    rst = digitalio.DigitalInOut(getattr(board, f"D{int(scr.get('rst', 5))}"))
    return st7789.ST7789(
        spi,
        rotation=90,
        width=135,
        height=240,
        x_offset=53,
        y_offset=40,
        cs=cs,
        dc=dc,
        rst=rst,
        baudrate=24_000_000,
    )


def _backlight_on(conf: dict) -> None:
    try:
        from adafruit_servokit import ServoKit

        sv = conf.get("servo") or {}
        freq = int(sv.get("freq") or 60)
        ch = int((sv.get("backlight") or {}).get("channel", 15))
        kit = ServoKit(channels=16, frequency=freq)
        servo = kit.servo[ch]
        servo.set_pulse_width_range(0, 1_000_000 // freq)
        servo.fraction = 0.85
        print("[BOOTANIM] backlight on", flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"[BOOTANIM] backlight skip — {exc}", flush=True)


def _handle(sig, _frame) -> None:
    global _stop
    _stop = True


def _preview(out: Path) -> None:
    """Xuất GIF 240×135 (phóng 3×) — test trên laptop/WSL, không cần ST7789."""
    frames = [render_frame(i).resize((W * 3, H * 3)) for i in range(12)]
    out.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=280, loop=0)
    print(f"[BOOTANIM] preview {out}", flush=True)
    print("[BOOTANIM] trên sim: http://127.0.0.1:8088/ → nút «Xem splash»", flush=True)


def main(argv=None) -> None:
    import argparse

    p = argparse.ArgumentParser(description="Cozmars ST7789 boot splash")
    p.add_argument(
        "--preview",
        nargs="?",
        const="/tmp/cozmars-bootanim.gif",
        default=None,
        metavar="GIF",
        help="Xuất GIF (không cần LCD). Mặc định /tmp/cozmars-bootanim.gif",
    )
    args = p.parse_args(argv)
    if args.preview:
        _preview(Path(args.preview))
        return

    signal.signal(signal.SIGTERM, _handle)
    signal.signal(signal.SIGINT, _handle)
    conf = _conf()
    print(f"[BOOTANIM] splash {_hostname()} {_serial()}", flush=True)
    disp = None
    try:
        disp = _open_st7789(conf)
        _backlight_on(conf)
    except Exception as exc:  # noqa: BLE001
        print(f"[BOOTANIM] ST7789 miss — {exc} (đợi SIGTERM)", flush=True)
    tick = 0
    while not _stop:
        frame = render_frame(tick)
        if disp is not None:
            try:
                disp.image(frame if frame.size == (int(disp.width), int(disp.height)) else frame.resize((int(disp.width), int(disp.height))))
            except Exception as exc:  # noqa: BLE001
                print(f"[BOOTANIM] draw fail — {exc}", flush=True)
                time.sleep(0.4)
        tick += 1
        time.sleep(0.28)
    print("[BOOTANIM] stop — giữ frame, nhả SPI", flush=True)


if __name__ == "__main__":
    main()
