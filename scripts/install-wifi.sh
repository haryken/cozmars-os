#!/usr/bin/env bash
# Cài hostapd/dnsmasq + autohotspot Cozmars. Chạy trên Pi (root).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ "$(id -u)" -ne 0 ]]; then
  exec sudo bash "$0" "$@"
fi
export DEBIAN_FRONTEND=noninteractive

echo "[wifi] apt hostapd dnsmasq iw…"
apt-get install -y hostapd dnsmasq iw wireless-tools || apt-get install -y hostapd dnsmasq iw

systemctl unmask hostapd 2>/dev/null || true
systemctl disable hostapd 2>/dev/null || true
systemctl stop hostapd 2>/dev/null || true
# dnsmasq bật khi AP; mặc định disable để khỏi xung đột khi client
systemctl disable dnsmasq 2>/dev/null || true
systemctl stop dnsmasq 2>/dev/null || true

install -m 755 "$ROOT/scripts/wifi/cozmars-autohotspot.sh" /usr/local/bin/cozmars-autohotspot
cp "$ROOT/systemd/cozmars-autohotspot.service" /etc/systemd/system/
cp "$ROOT/systemd/cozmars-autohotspot.timer" /etc/systemd/system/

# rfkill unblock
command -v rfkill >/dev/null && rfkill unblock wifi || true

systemctl daemon-reload
systemctl enable cozmars-autohotspot.service
systemctl enable cozmars-autohotspot.timer
systemctl start cozmars-autohotspot.service || true
systemctl start cozmars-autohotspot.timer || true

SER="$(python3 -c 'import uuid; print(hex(uuid.getnode())[2:].zfill(12)[-4:].upper())' 2>/dev/null || echo XXXX)"
HOST="$(hostname)"
echo "[wifi] xong. Mất mạng → hotspot mở SSID=$HOST (không mật khẩu)"
echo "[wifi] phone nối → tự mở trang WiFi · http://10.3.141.1/wifi"
echo "[wifi] đã có LAN: http://<ip-robot>:8077/"
