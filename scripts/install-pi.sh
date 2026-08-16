#!/usr/bin/env bash
# Chạy trên Pi Zero 2W (một lần): sudo bash scripts/install-pi.sh
# Apt lấy gpiozero / numpy / opencv (không pip biên dịch trên 512MB).
# Pip chỉ gói nhẹ vào venv /opt/cozmars/venv.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ "$(id -u)" -ne 0 ]]; then
  exec sudo bash "$0" "$@"
fi
export DEBIAN_FRONTEND=noninteractive
VENV=/opt/cozmars/venv
HOME_PI=/home/pi

echo "[install] apt…"
apt-get update -y
apt-get install -y \
  python3 python3-pip python3-venv python3-dev python3-cffi \
  python3-gpiozero python3-numpy python3-pil python3-spidev \
  libportaudio2 libsndfile1 ffmpeg \
  libjpeg-dev zlib1g-dev libatlas-base-dev \
  git avahi-daemon i2c-tools
apt-get install -y python3-rpi.gpio || apt-get install -y python3-rpi-lgpio || true
apt-get install -y python3-opencv || true
apt-get install -y python3-picamera python3-picamera2 || true
apt-get install -y portaudio19-dev || true

if command -v raspi-config >/dev/null; then
  raspi-config nonint do_i2c 0 || true
  raspi-config nonint do_spi 0 || true
  raspi-config nonint do_camera 0 || true
fi

echo "[install] venv $VENV (system-site-packages → dùng apt opencv/gpiozero)"
mkdir -p /opt/cozmars
python3 -m venv --system-site-packages "$VENV"
"$VENV/bin/pip" install -U pip setuptools wheel
PIP_ARGS=(install -e "${ROOT}[pi,audio,web]")
WHEELS="$ROOT/dist/wheels"
if [[ -d "$WHEELS" ]] && compgen -G "$WHEELS/*.whl" >/dev/null; then
  echo "[install] pip từ dist/wheels (offline)"
  PIP_ARGS+=(--find-links "$WHEELS" --prefer-binary)
fi
"$VENV/bin/pip" "${PIP_ARGS[@]}"

mkdir -p "$HOME_PI/.cozmars"
cp -n "$ROOT/config/conf.json" "$HOME_PI/.cozmars/conf.json" || true
cp -n "$ROOT/config/env.json" "$HOME_PI/.cozmars/env.json" || true
if id pi >/dev/null 2>&1; then
  chown -R pi:pi "$HOME_PI/.cozmars"
fi

sed "s|^ExecStart=.*|ExecStart=$VENV/bin/python -m cozmars --hal pi --web|" \
  "$ROOT/systemd/cozmars.service" > /tmp/cozmars.service
cp /tmp/cozmars.service /etc/systemd/system/cozmars.service
sed "s|^ExecStart=.*|ExecStart=$VENV/bin/python -m cozmars.bootanim|" \
  "$ROOT/systemd/cozmars-bootanim.service" > /tmp/cozmars-bootanim.service
cp /tmp/cozmars-bootanim.service /etc/systemd/system/cozmars-bootanim.service
if [[ -f "$ROOT/systemd/cozmars.avahi.service" ]]; then
  mkdir -p /etc/avahi/services
  cp "$ROOT/systemd/cozmars.avahi.service" /etc/avahi/services/ || true
fi
systemctl daemon-reload
systemctl enable cozmars-bootanim.service
systemctl enable --now cozmars.service

echo "[install] WiFi hotspot / portal :8077…"
bash "$ROOT/scripts/install-wifi.sh" || echo "[install] WARN install-wifi — chạy lại sau: sudo bash $ROOT/scripts/install-wifi.sh"

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
echo "[install] xong. Web: http://${IP:-<ip-pi>}/"
echo "[install] WiFi: http://${IP:-<ip-pi>}:8077/  (mất mạng → hotspot 10.3.141.1:8077)"
echo "[install] log: journalctl -u cozmars -f"
