#!/usr/bin/env bash
# Cài gói fat ARM vào SLOT NGHỈ (A/B) — không đụng slot đang chạy cho đến khi verify xong.
# Usage:
#   sudo bash scripts/install-fat.sh /path/to/cozmars-*-bundle.tgz
#   sudo bash /opt/cozmars/install-fat.sh --from-bundle   # (hiếm) cài lại từ tree hiện tại
set -euo pipefail
if [[ "$(id -u)" -ne 0 ]]; then
  exec sudo bash "$0" "$@"
fi

HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
if [[ -f "$HERE/slot-lib.sh" ]]; then
  # shellcheck disable=SC1091
  source "$HERE/slot-lib.sh"
elif [[ -f /usr/local/lib/cozmars/slot-lib.sh ]]; then
  # shellcheck disable=SC1091
  source /usr/local/lib/cozmars/slot-lib.sh
elif [[ -f /opt/cozmars/src/scripts/slot-lib.sh ]]; then
  # shellcheck disable=SC1091
  source /opt/cozmars/src/scripts/slot-lib.sh
else
  echo "[install-fat] thiếu slot-lib.sh" >&2
  exit 1
fi

STATE_DIR="${COZMARS_UPDATE_STATE:-/run/cozmars-update}"
mkdir -p "$STATE_DIR"
progress() {
  local pct="$1" phase="$2"
  echo "$pct" > "$STATE_DIR/percent"
  echo "$phase" > "$STATE_DIR/phase"
  echo "[install-fat] $pct% $phase"
}

HOME_PI=/home/pi
TGZ="${1:-}"

slot_migrate_legacy
ACTIVE="$(slot_active)"
TARGET="$(slot_other)"
TARGET_ROOT="$(slot_path "$TARGET")"

progress 52 "slot-prepare target=$TARGET (active=$ACTIVE)"

write_units() {
  local link_root="$COZMARS_LINK"
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
Environment=PYTHONPATH=$link_root/src
ExecStartPre=/usr/local/bin/cozmars-boot-guard
ExecStart=$link_root/venv/bin/python -m cozmars --hal pi --web
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
Environment=PYTHONPATH=$link_root/src
ExecStart=$link_root/venv/bin/python -m cozmars.bootanim
Restart=no

[Install]
WantedBy=multi-user.target
EOF
}

install_helpers() {
  mkdir -p /usr/local/lib/cozmars /usr/local/bin
  if [[ -f "$HERE/slot-lib.sh" ]]; then
    install -m 644 "$HERE/slot-lib.sh" /usr/local/lib/cozmars/slot-lib.sh
  elif [[ -f /opt/cozmars/src/scripts/slot-lib.sh ]]; then
    install -m 644 /opt/cozmars/src/scripts/slot-lib.sh /usr/local/lib/cozmars/slot-lib.sh
  fi
  if [[ -f "$HERE/cozmars-boot-guard.sh" ]]; then
    install -m 755 "$HERE/cozmars-boot-guard.sh" /usr/local/bin/cozmars-boot-guard
  elif [[ -f /opt/cozmars/src/scripts/cozmars-boot-guard.sh ]]; then
    install -m 755 /opt/cozmars/src/scripts/cozmars-boot-guard.sh /usr/local/bin/cozmars-boot-guard
  fi
  # Giữ bản install trên cả hai slot + link
  if [[ -f "$0" ]]; then
    install -m 755 "$0" "$TARGET_ROOT/install-fat.sh" 2>/dev/null || true
  fi
}

if [[ "$TGZ" == "--from-bundle" ]]; then
  progress 60 "from-bundle (không khuyến nghị OTA)"
  if ! slot_verify "$ACTIVE"; then
    echo "[install-fat] slot active chưa đủ venv/src" >&2
    exit 1
  fi
  write_units
  install_helpers
  systemctl daemon-reload
  systemctl enable cozmars-bootanim.service
  systemctl enable --now cozmars.service
  exit 0
fi

[[ -n "$TGZ" && -f "$TGZ" ]] || {
  echo "usage: install-fat.sh <cozmars-*-bundle.tgz>" >&2
  exit 1
}

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
progress 58 "untar"
tar -C "$STAGE" -xzf "$TGZ"
BUNDLE="$(find "$STAGE" -maxdepth 2 -type d -name 'cozmars-bundle' | head -1)"
[[ -n "$BUNDLE" ]] || BUNDLE="$STAGE"
SRC_OPT="$BUNDLE/opt/cozmars"
[[ -d "$SRC_OPT" ]] || {
  echo "[install-fat] bundle thiếu opt/cozmars" >&2
  exit 1
}

progress 70 "install-inactive-slot $TARGET"
# Xóa slot nghỉ rồi copy — slot active không bị đụng
rm -rf "$TARGET_ROOT"
mkdir -p "$COZMARS_OPT_ROOT"
cp -a "$SRC_OPT" "$TARGET_ROOT"

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
# Bundle có thể kèm slot-lib / boot-guard trong src
if [[ -f "$TARGET_ROOT/src/scripts/slot-lib.sh" ]]; then
  install -m 644 "$TARGET_ROOT/src/scripts/slot-lib.sh" /usr/local/lib/cozmars/slot-lib.sh 2>/dev/null || {
    mkdir -p /usr/local/lib/cozmars
    install -m 644 "$TARGET_ROOT/src/scripts/slot-lib.sh" /usr/local/lib/cozmars/slot-lib.sh
  }
fi
if [[ -f "$TARGET_ROOT/src/scripts/cozmars-boot-guard.sh" ]]; then
  install -m 755 "$TARGET_ROOT/src/scripts/cozmars-boot-guard.sh" /usr/local/bin/cozmars-boot-guard
fi
if [[ -f "$TARGET_ROOT/src/scripts/install-fat.sh" ]]; then
  install -m 755 "$TARGET_ROOT/src/scripts/install-fat.sh" "$TARGET_ROOT/install-fat.sh"
fi
if [[ -f "$TARGET_ROOT/src/scripts/slot-lib.sh" ]]; then
  # giữ cạnh install-fat trong slot
  cp -a "$TARGET_ROOT/src/scripts/slot-lib.sh" "$TARGET_ROOT/slot-lib.sh" 2>/dev/null || true
fi

progress 85 "verify-slot $TARGET"
if ! slot_verify "$TARGET"; then
  echo "[install-fat] slot $TARGET hỏng (thiếu venv/python hoặc src) — giữ nguyên slot $ACTIVE" >&2
  rm -rf "$TARGET_ROOT"
  progress 0 "verify-failed"
  exit 1
fi

# Config user: chỉ tạo nếu chưa có (không ghi đè)
mkdir -p "$HOME_PI/.cozmars"
if [[ -d "$TARGET_ROOT/config" ]]; then
  cp -n "$TARGET_ROOT/config/conf.json" "$HOME_PI/.cozmars/conf.json" 2>/dev/null || true
  cp -n "$TARGET_ROOT/config/env.json" "$HOME_PI/.cozmars/env.json" 2>/dev/null || true
elif [[ -d "$TARGET_ROOT/src/config" ]]; then
  cp -n "$TARGET_ROOT/src/config/conf.json" "$HOME_PI/.cozmars/conf.json" 2>/dev/null || true
  cp -n "$TARGET_ROOT/src/config/env.json" "$HOME_PI/.cozmars/env.json" 2>/dev/null || true
fi
if id pi >/dev/null 2>&1; then
  chown -R pi:pi "$HOME_PI/.cozmars"
fi

progress 92 "switch-slot $ACTIVE → $TARGET"
write_units
install_helpers
slot_set_active "$TARGET"

if [[ -f /usr/local/bin/cozmars-autohotspot ]]; then
  systemctl enable cozmars-autohotspot.service 2>/dev/null || true
  systemctl enable cozmars-autohotspot.timer 2>/dev/null || true
fi

systemctl daemon-reload
systemctl enable cozmars-bootanim.service
systemctl enable cozmars.service
systemctl start cozmars-autohotspot.service 2>/dev/null || true
systemctl start cozmars-autohotspot.timer 2>/dev/null || true

progress 98 "restart-service"
systemctl restart cozmars.service 2>/dev/null || systemctl start cozmars.service

progress 100 "done active=$(slot_active)"
IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
echo "[install-fat] A/B xong. active=$(slot_active) previous=$(slot_read previous-slot)"
echo "[install-fat] Web: http://${IP:-<ip>}/  WiFi portal: http://${IP:-<ip>}:8077/"
echo "{\"ok\":true,\"active\":\"$(slot_active)\",\"previous\":\"$(slot_read previous-slot)\",\"boot_state\":\"$(slot_read boot-state)\"}" > "$STATE_DIR/result.json"
