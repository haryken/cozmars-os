#!/usr/bin/env bash
# Cài gói fat ARM lên robot — KHÔNG apt/pip. Chỉ giải nén + systemd.
# Usage:
#   sudo bash scripts/install-fat.sh /path/to/cozmars-*-bundle.tgz
#   sudo bash /opt/cozmars/install-fat.sh --from-bundle   # đã giải nén sẵn
set -euo pipefail
if [[ "$(id -u)" -ne 0 ]]; then
  exec sudo bash "$0" "$@"
fi

OPT=/opt/cozmars
HOME_PI=/home/pi
TGZ="${1:-}"

if [[ "$TGZ" == "--from-bundle" ]]; then
  if [[ ! -d "$OPT/venv" || ! -d "$OPT/src/cozmars" ]]; then
    echo "[install-fat] thiếu $OPT/venv hoặc $OPT/src — giải nén bundle trước" >&2
    exit 1
  fi
else
  [[ -n "$TGZ" && -f "$TGZ" ]] || {
    echo "usage: install-fat.sh <cozmars-*-bundle.tgz>" >&2
    exit 1
  }
  STAGE="$(mktemp -d)"
  trap 'rm -rf "$STAGE"' EXIT
  echo "[install-fat] untar $TGZ"
  tar -C "$STAGE" -xzf "$TGZ"
  BUNDLE="$(find "$STAGE" -maxdepth 2 -type d -name 'cozmars-bundle' | head -1)"
  [[ -n "$BUNDLE" ]] || BUNDLE="$STAGE"
  if [[ -d "$BUNDLE/opt/cozmars" ]]; then
    mkdir -p /opt
    rm -rf "$OPT"
    cp -a "$BUNDLE/opt/cozmars" "$OPT"
  else
    echo "[install-fat] bundle thiếu opt/cozmars" >&2
    exit 1
  fi
  if [[ -d "$BUNDLE/etc/systemd/system" ]]; then
    cp -a "$BUNDLE/etc/systemd/system/"*.service /etc/systemd/system/ 2>/dev/null || true
    cp -a "$BUNDLE/etc/systemd/system/"*.timer /etc/systemd/system/ 2>/dev/null || true
  fi
  if [[ -d "$BUNDLE/etc/avahi/services" ]]; then
    mkdir -p /etc/avahi/services
    cp -a "$BUNDLE/etc/avahi/services/"* /etc/avahi/services/ 2>/dev/null || true
  fi
  if [[ -f "$BUNDLE/usr/local/bin/cozmars-autohotspot" ]]; then
    install -m 755 "$BUNDLE/usr/local/bin/cozmars-autohotspot" /usr/local/bin/cozmars-autohotspot
  fi
fi

# Đảm bảo unit trỏ /opt/cozmars/venv
VENV="$OPT/venv"
if [[ ! -x "$VENV/bin/python" ]]; then
  echo "[install-fat] không có $VENV/bin/python — bundle hỏng hoặc sai arch" >&2
  exit 1
fi

cat > /etc/systemd/system/cozmars.service <<EOF
[Unit]
Description=Cozmars OS
After=local-fs.target sound.target cozmars-bootanim.service network-pre.target
Wants=cozmars-bootanim.service cozmars-autohotspot.service

[Service]
User=root
WorkingDirectory=/home/pi
Environment=PYTHONUNBUFFERED=1
Environment=COZMARS_HAL=pi
Environment=PYTHONPATH=$OPT/src
ExecStart=$VENV/bin/python -m cozmars --hal pi --web
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/cozmars-bootanim.service <<EOF
[Unit]
Description=Cozmars boot splash ST7789
DefaultDependencies=no
After=local-fs.target
Before=cozmars.service

[Service]
Type=simple
Environment=PYTHONPATH=$OPT/src
ExecStart=$VENV/bin/python -m cozmars.bootanim
Restart=no

[Install]
WantedBy=multi-user.target
EOF

mkdir -p "$HOME_PI/.cozmars"
if [[ -d "$OPT/config" ]]; then
  cp -n "$OPT/config/conf.json" "$HOME_PI/.cozmars/conf.json" 2>/dev/null || true
  cp -n "$OPT/config/env.json" "$HOME_PI/.cozmars/env.json" 2>/dev/null || true
elif [[ -d "$OPT/src/config" ]]; then
  cp -n "$OPT/src/config/conf.json" "$HOME_PI/.cozmars/conf.json" 2>/dev/null || true
  cp -n "$OPT/src/config/env.json" "$HOME_PI/.cozmars/env.json" 2>/dev/null || true
fi
if id pi >/dev/null 2>&1; then
  chown -R pi:pi "$HOME_PI/.cozmars"
fi

# hostapd/dnsmasq đã có trong image hoặc apt sẵn — chỉ enable units
if [[ -f /usr/local/bin/cozmars-autohotspot ]]; then
  systemctl enable cozmars-autohotspot.service 2>/dev/null || true
  systemctl enable cozmars-autohotspot.timer 2>/dev/null || true
fi

systemctl daemon-reload
systemctl enable cozmars-bootanim.service
systemctl enable --now cozmars.service
systemctl start cozmars-autohotspot.service 2>/dev/null || true
systemctl start cozmars-autohotspot.timer 2>/dev/null || true

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
echo "[install-fat] xong (không pip). Web: http://${IP:-<ip>}/"
echo "[install-fat] WiFi portal: http://${IP:-<ip>}:8077/"
