#!/usr/bin/env bash
# Laptop (có mạng): tải wheel ARM cho Pi, để install-pi không compile.
# Không lấy opencv/numpy qua pip — Pi dùng apt.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/dist/wheels"
mkdir -p "$DEST"
PY="${1:-311}"
echo "[wheels] python $PY  platform armv7l → $DEST"
python3 -m pip download \
  -d "$DEST" \
  --python-version "$PY" \
  --platform manylinux2014_armv7l \
  --only-binary=:all: \
  aiohttp sounddevice \
  || echo "[wheels] một số gói không có wheel ARM — Pi sẽ pip/apt bù"
python3 -m pip download -d "$DEST" \
  "adafruit-circuitpython-servokit" \
  "adafruit-circuitpython-rgb-display" \
  gpiozero \
  || true
echo "[wheels] $(ls -1 "$DEST" | wc -l) files"
