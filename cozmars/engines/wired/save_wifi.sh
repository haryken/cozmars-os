#!/usr/bin/env bash
# Ghi SSID/PSK vào wpa_supplicant.conf — gọi từ wifi_portal (root).
set -euo pipefail
SSID="${1:?ssid}"
PSK="${2:?psk}"
CONF="${WPA_CONF:-/etc/wpa_supplicant/wpa_supplicant.conf}"

if [[ ! -f "$CONF" ]]; then
  mkdir -p "$(dirname "$CONF")"
  cat >"$CONF" <<EOF
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=VN

network={
	ssid="wifi_name"
	psk="wifi_password"
}
EOF
  chmod 600 "$CONF"
fi

# Escape cho sed: chỉ cần tránh & và \
esc() { printf '%s' "$1" | sed -e 's/[&\\]/\\&/g'; }
SSID_E="$(esc "$SSID")"
PSK_E="$(esc "$PSK")"

if grep -q 'ssid=' "$CONF"; then
  sed -i "s/ssid=\".*\"/ssid=\"$SSID_E\"/;s/psk=\".*\"/psk=\"$PSK_E\"/" "$CONF"
else
  cat >>"$CONF" <<EOF

network={
	ssid="$SSID"
	psk="$PSK"
}
EOF
fi
echo "[wifi] saved ssid=$SSID"
