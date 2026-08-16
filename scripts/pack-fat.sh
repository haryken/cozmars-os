#!/usr/bin/env bash
# Đóng gói fat ARM — CHẠY TRÊN Pi ARM (Zero 2W / Pi 4 armhf|aarch64).
# Laptop x86 không đóng được venv ARM.
# Output: dist/cozmars-<ver>-armhf-bundle.tgz  (kind=arm-bundle, không pip trên robot đích)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ARCH="$(uname -m)"
case "$ARCH" in
  armv7l|armhf|aarch64|arm64) ;;
  *)
    echo "[pack-fat] ERROR: cần máy ARM (hiện tại $ARCH). Chạy trên Pi Zero 2W / Pi ARM." >&2
    exit 1
    ;;
esac

VER="$(python3 -c "import sys; sys.path.insert(0,'$ROOT'); from cozmars.version import __version__; print(__version__)")"
OUT="$ROOT/dist"
STAGE="$(mktemp -d)"
BUNDLE="$STAGE/cozmars-bundle"
OPT="$BUNDLE/opt/cozmars"
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$OUT" "$OPT/src" "$BUNDLE/usr/local/bin" "$BUNDLE/etc/systemd/system" "$BUNDLE/etc/avahi/services"

echo "[pack-fat] cài layout build tại $OPT (apt + venv)…"
# Source sạch vào opt/cozmars/src
rsync -a --delete \
  --exclude '.git' --exclude 'dist' --exclude '__pycache__' --exclude '*.pyc' \
  --exclude '.venv' --exclude 'assets/vosk' \
  "$ROOT/" "$OPT/src/"

export DEBIAN_FRONTEND=noninteractive
if [[ "$(id -u)" -ne 0 ]]; then
  echo "[pack-fat] cần root để apt + đóng venv — chạy: sudo bash scripts/pack-fat.sh" >&2
  exit 1
fi

apt-get update -y
apt-get install -y \
  python3 python3-pip python3-venv python3-dev python3-cffi \
  python3-gpiozero python3-numpy python3-pil python3-spidev \
  libportaudio2 libsndfile1 ffmpeg \
  libjpeg-dev zlib1g-dev libatlas-base-dev \
  git avahi-daemon i2c-tools hostapd dnsmasq iw \
  xz-utils
apt-get install -y python3-rpi.gpio || apt-get install -y python3-rpi-lgpio || true
apt-get install -y python3-opencv || true
apt-get install -y python3-picamera python3-picamera2 || true
apt-get install -y portaudio19-dev || true

VENV="$OPT/venv"
python3 -m venv --system-site-packages "$VENV"
"$VENV/bin/pip" install -U pip setuptools wheel
PIP_ARGS=(install -e "${OPT}/src[pi,audio,web]")
WHEELS="$ROOT/dist/wheels"
if [[ -d "$WHEELS" ]] && compgen -G "$WHEELS/*.whl" >/dev/null; then
  PIP_ARGS+=(--find-links "$WHEELS" --prefer-binary)
fi
"$VENV/bin/pip" "${PIP_ARGS[@]}"

# Systemd + wifi script vào bundle
sed "s|^ExecStart=.*|ExecStart=$VENV/bin/python -m cozmars --hal pi --web|" \
  "$ROOT/systemd/cozmars.service" > "$BUNDLE/etc/systemd/system/cozmars.service"
# Paths trong unit sẽ được rewrite lúc install-fat sang /opt/cozmars/venv
sed "s|$VENV|/opt/cozmars/venv|g" "$BUNDLE/etc/systemd/system/cozmars.service" > "$BUNDLE/etc/systemd/system/cozmars.service.tmp"
mv "$BUNDLE/etc/systemd/system/cozmars.service.tmp" "$BUNDLE/etc/systemd/system/cozmars.service"

sed "s|^ExecStart=.*|ExecStart=/opt/cozmars/venv/bin/python -m cozmars.bootanim|" \
  "$ROOT/systemd/cozmars-bootanim.service" > "$BUNDLE/etc/systemd/system/cozmars-bootanim.service"
cp "$ROOT/systemd/cozmars-autohotspot.service" "$BUNDLE/etc/systemd/system/"
cp "$ROOT/systemd/cozmars-autohotspot.timer" "$BUNDLE/etc/systemd/system/"
[[ -f "$ROOT/systemd/cozmars.avahi.service" ]] && cp "$ROOT/systemd/cozmars.avahi.service" "$BUNDLE/etc/avahi/services/"
install -m 755 "$ROOT/scripts/wifi/cozmars-autohotspot.sh" "$BUNDLE/usr/local/bin/cozmars-autohotspot"
install -m 755 "$ROOT/scripts/install-fat.sh" "$BUNDLE/opt/cozmars/install-fat.sh"
install -m 755 "$ROOT/scripts/install-wifi.sh" "$OPT/src/scripts/install-wifi.sh"
cp -a "$ROOT/config" "$OPT/config"

# Rewrite shebang / paths in venv to relocatable /opt/cozmars/venv
if [[ -d "$VENV/bin" ]]; then
  find "$VENV/bin" -type f -executable 2>/dev/null | while read -r f; do
    if head -1 "$f" | grep -q "^#!.*venv"; then
      sed -i "1s|^#!.*|#!/opt/cozmars/venv/bin/python|" "$f" || true
    fi
  done
  # pyvenv.cfg
  if [[ -f "$VENV/pyvenv.cfg" ]]; then
    sed -i "s|^home = .*|home = /usr|" "$VENV/pyvenv.cfg" || true
  fi
fi

python3 - <<PY
import hashlib, json, pathlib, platform
root = pathlib.Path("$BUNDLE")
h = hashlib.sha256()
n = 0
for p in sorted(root.rglob("*")):
    if p.is_file():
        h.update(p.read_bytes())
        n += 1
machine = platform.machine()
manifest = {
    "name": "cozmars-os",
    "kind": "arm-bundle",
    "version": "$VER",
    "arch": machine,
    "sha256": h.hexdigest(),
    "files": n,
    "install": "sudo bash /opt/cozmars/install-fat.sh --from-bundle",
}
(root / "MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
(pathlib.Path("$OPT") / "MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print("MANIFEST", manifest["kind"], manifest["sha256"][:12], "files", n, "arch", machine)
PY

# Tag arch in filename
TAG="armhf"
[[ "$ARCH" == "aarch64" || "$ARCH" == "arm64" ]] && TAG="aarch64"
TGZ="$OUT/cozmars-$VER-${TAG}-bundle.tgz"
# Also symlink-friendly name armhf-bundle for Zero 2W 32-bit
tar -C "$STAGE" -czf "$TGZ" cozmars-bundle
ln -sfn "$(basename "$TGZ")" "$OUT/cozmars-$VER-armhf-bundle.tgz" 2>/dev/null || cp -f "$TGZ" "$OUT/cozmars-$VER-armhf-bundle.tgz"
echo "packed $TGZ ($(wc -c < "$TGZ") bytes)"
echo "[pack-fat] trên robot đích: sudo bash scripts/install-fat.sh $TGZ"
