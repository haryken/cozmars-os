#!/usr/bin/env bash
# Đóng gói fat ARM trên laptop x86 bằng Docker + QEMU (không cần Pi vật lý).
#
# Mục tiêu mặc định = Pi Zero 2W + Raspberry Pi OS Lite 32-bit (Bullseye):
#   - CPU userspace: linux/arm/v7 (armhf) — Zero 2W chạy 32-bit OS
#   - Base: debian:bullseye (cùng nhánh với Pi OS Bullseye)
#
# Đây KHÔNG phải giả lập đủ phần cứng Zero 2W (GPIO/SPI/WiFi/cam không có trong
# container). Chỉ để biên dịch/đóng venv ARM giống chip ARM trên board.
#
# Usage:
#   ./scripts/pack-fat-docker.sh              # Zero 2W 32-bit (mặc định)
#   ARCH=aarch64 ./scripts/pack-fat-docker.sh  # nếu dùng Pi OS 64-bit
#
# Output: dist/cozmars-<ver>-armhf-bundle.tgz
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ARCH_TARGET="${ARCH:-armhf}"
# Giới hạn RAM gần Zero 2W (512 MB); tắt: MEM_LIMIT= ./scripts/pack-fat-docker.sh
MEM_LIMIT="${MEM_LIMIT:-512m}"
case "$ARCH_TARGET" in
  armhf|armv7l)
    PLATFORM="linux/arm/v7"
    IMAGE="arm32v7/debian:bullseye"
    TAG="armhf"
    ;;
  aarch64|arm64)
    PLATFORM="linux/arm64"
    IMAGE="arm64v8/debian:bullseye"
    TAG="aarch64"
    ;;
  *)
    echo "[pack-fat-docker] ARCH phải là armhf hoặc aarch64 (hiện: $ARCH_TARGET)" >&2
    exit 1
    ;;
esac

if ! command -v docker >/dev/null 2>&1; then
  cat >&2 <<'EOF'
[pack-fat-docker] ERROR: chưa có Docker.

  Ubuntu/WSL:  sudo apt install docker.io
  hoặc Docker Desktop + bật WSL integration
  rồi: sudo usermod -aG docker $USER  (logout/login)
EOF
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "[pack-fat-docker] ERROR: docker không chạy / không có quyền (thử: sudo docker info)" >&2
  exit 1
fi

echo "[pack-fat-docker] đăng ký QEMU binfmt (giả ARM trên x86)…"
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes >/dev/null

VER="$(python3 -c "import sys; sys.path.insert(0,'$ROOT'); from cozmars.version import __version__; print(__version__)")"
OUT="$ROOT/dist"
mkdir -p "$OUT"

DOCKER_MEM=()
if [[ -n "${MEM_LIMIT}" ]]; then
  DOCKER_MEM=(--memory "$MEM_LIMIT" --memory-swap "$MEM_LIMIT")
  echo "[pack-fat-docker] RAM cap $MEM_LIMIT (gần Zero 2W) — OOM: MEM_LIMIT=1g $0"
fi

echo "[pack-fat-docker] Zero2W-like: platform=$PLATFORM image=$IMAGE"
echo "[pack-fat-docker] (userspace ARM giống OS 32-bit; không giả GPIO/SPI/WiFi)…"
docker run --rm --platform "$PLATFORM" \
  "${DOCKER_MEM[@]}" \
  -v "$ROOT:/src:rw" \
  -w /src \
  -e DEBIAN_FRONTEND=noninteractive \
  "$IMAGE" \
  bash -c '
    set -euo pipefail
    apt-get update -y
    apt-get install -y rsync sudo ca-certificates
    bash scripts/pack-fat.sh
  '

if ! ls -1 "$OUT"/cozmars-*-bundle.tgz >/dev/null 2>&1; then
  echo "[pack-fat-docker] ERROR: không thấy bundle trong $OUT" >&2
  exit 1
fi
LATEST="$(ls -1t "$OUT"/cozmars-*-bundle.tgz | head -1)"
echo "[pack-fat-docker] OK → $LATEST"
echo "[pack-fat-docker] tiếp: ./scripts/build-sd-image.sh $LATEST"
echo "[pack-fat-docker] hoặc: sudo bash scripts/install-fat.sh $LATEST  (trên Pi thật)"
