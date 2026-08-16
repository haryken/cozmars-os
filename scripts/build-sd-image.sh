#!/usr/bin/env bash
# Build SD image Cozmars (pi-gen + Docker) trên PC x86/ARM.
# Cần: Docker, gói fat ARM đã build trên Pi.
#
# Usage:
#   ./scripts/build-sd-image.sh [/path/to/cozmars-*-bundle.tgz]
#
# Output:
#   dist/cozmars-<ver>-pi-zero2w.img.xz
#   dist/cozmars-<ver>-pi-zero2w.img.xz.sha256
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VER="$(python3 -c "import sys; sys.path.insert(0,'$ROOT'); from cozmars.version import __version__; print(__version__)")"
OUT="$ROOT/dist"
mkdir -p "$OUT"

BUNDLE="${1:-}"
if [[ -z "$BUNDLE" ]]; then
  BUNDLE="$(ls -1t "$OUT"/cozmars-*-bundle.tgz 2>/dev/null | head -1 || true)"
fi
if [[ -z "$BUNDLE" || ! -f "$BUNDLE" ]]; then
  cat >&2 <<EOF
[build-sd] ERROR: chưa có gói fat ARM.

1) Trên Pi Zero 2W / Pi ARM:
     sudo bash scripts/pack-fat.sh
2) Copy file dist/cozmars-*-bundle.tgz về laptop
3) Chạy lại:
     ./scripts/build-sd-image.sh /path/to/cozmars-*-bundle.tgz
EOF
  exit 1
fi
BUNDLE="$(readlink -f "$BUNDLE")"
echo "[build-sd] fat bundle: $BUNDLE"

if ! command -v docker >/dev/null 2>&1; then
  cat >&2 <<EOF
[build-sd] ERROR: cần Docker.

  - Cài Docker Desktop / docker.io
  - User trong group docker: sudo usermod -aG docker \$USER
EOF
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "[build-sd] ERROR: docker không chạy hoặc không có quyền (docker info fail)" >&2
  exit 1
fi

PIGEN_DIR="${COZMARS_PIGEN_DIR:-$ROOT/scripts/image/pi-gen}"
PIGEN_REPO="${COZMARS_PIGEN_REPO:-https://github.com/RPi-Distro/pi-gen.git}"

if [[ ! -d "$PIGEN_DIR/.git" ]]; then
  echo "[build-sd] clone pi-gen → $PIGEN_DIR"
  git clone --depth 1 "$PIGEN_REPO" "$PIGEN_DIR"
fi

# Config Lite 32-bit (Zero 2W)
cat > "$PIGEN_DIR/config" <<EOF
IMG_NAME='cozmars'
RELEASE=bullseye
DEPLOY_COMPRESSION=xz
COMPRESSION_LEVEL=6
USE_QCOW2=0
LOCALE_DEFAULT=en_US.UTF-8
TARGET_HOSTNAME=cozmars
KEYBOARD_KEYMAP=us
KEYBOARD_LAYOUT="English (US)"
TIMEZONE_DEFAULT=Asia/Ho_Chi_Minh
FIRST_USER_NAME=pi
FIRST_USER_PASS=cozmars
DISABLE_FIRST_BOOT_USER_RENAME=1
ENABLE_SSH=1
STAGE_LIST="stage0 stage1 stage2 stage-cozmars"
EOF

# Custom stage
STAGE_DST="$PIGEN_DIR/stage-cozmars"
rm -rf "$STAGE_DST"
mkdir -p "$STAGE_DST/files"
cp -a "$ROOT/scripts/image/stage-cozmars/"*.sh "$STAGE_DST/" 2>/dev/null || true
# Empty EXPORT_IMAGE = pi-gen xuất .img ở stage này
: > "$STAGE_DST/EXPORT_IMAGE"
install -m 644 "$BUNDLE" "$STAGE_DST/files/cozmars-bundle.tgz"
chmod +x "$STAGE_DST/"*.sh

# stage2 is desktop-less if we use lite — pi-gen stage2 is lite by default when no stage3 desktop
# Ensure stage3/4/5 skipped — STAGE_LIST already limits

echo "[build-sd] chạy pi-gen (lâu: 30–90 phút)…"
cd "$PIGEN_DIR"
# Clean previous deploy partially
rm -rf work deploy 2>/dev/null || true
./build-docker.sh

# Find output
IMG="$(find "$PIGEN_DIR/deploy" -name '*.img.xz' -o -name '*.img' 2>/dev/null | head -1 || true)"
if [[ -z "$IMG" ]]; then
  echo "[build-sd] ERROR: không thấy image trong $PIGEN_DIR/deploy" >&2
  ls -la "$PIGEN_DIR/deploy" 2>/dev/null || true
  exit 1
fi

DEST="$OUT/cozmars-$VER-pi-zero2w.img.xz"
if [[ "$IMG" == *.img && "$IMG" != *.xz ]]; then
  echo "[build-sd] xz compress…"
  xz -T0 -c "$IMG" > "$DEST"
else
  cp -f "$IMG" "$DEST"
fi
( cd "$OUT" && sha256sum "$(basename "$DEST")" > "$(basename "$DEST").sha256" )
echo "[build-sd] OK $DEST"
echo "[build-sd] flash: Raspberry Pi Imager → Use custom → $(basename "$DEST")"
echo "[build-sd] hoặc: xzcat $DEST | sudo dd of=/dev/sdX bs=4M status=progress"
