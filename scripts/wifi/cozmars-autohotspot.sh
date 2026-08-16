#!/usr/bin/env bash
# Cozmars auto-hotspot (Pi Zero 2W / Bullseye dhcpcd).
# Có WiFi nhà → client. Mất mạng → AP mở (không mật khẩu) 10.3.141.1.
# Phone nối → captive portal tự mở trang cấu hình WiFi.
# Cài: scripts/install-wifi.sh (gọi từ install-pi.sh).
set -euo pipefail

IFACE="${COZMARS_WLAN:-wlan0}"
AP_IP="10.3.141.1"
HOSTAPD_CONF="/etc/hostapd/cozmars-hostapd.conf"
DNSMASQ_CONF="/etc/dnsmasq.d/cozmars-hotspot.conf"
WPA_CONF="/etc/wpa_supplicant/wpa_supplicant.conf"

hostname_s() {
  hostname 2>/dev/null || echo cozmars
}

write_ap_conf() {
  local host
  host="$(hostname_s)"
  mkdir -p /etc/hostapd /etc/dnsmasq.d
  # AP mở — không WPA; điện thoại nối là vào được
  cat >"$HOSTAPD_CONF" <<EOF
interface=$IFACE
driver=nl80211
ssid=$host
hw_mode=g
channel=6
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=0
EOF
  # Mọi DNS → AP IP (captive portal)
  cat >"$DNSMASQ_CONF" <<EOF
interface=$IFACE
bind-interfaces
dhcp-range=10.3.141.50,10.3.141.150,255.255.255.0,12h
domain-needed
bogus-priv
address=/#/$AP_IP
EOF
}

stop_ap() {
  systemctl stop hostapd 2>/dev/null || true
  systemctl stop dnsmasq 2>/dev/null || true
  ip addr del "$AP_IP/24" dev "$IFACE" 2>/dev/null || true
}

start_client() {
  stop_ap
  # Trả wlan0 về dhcpcd / wpa
  if systemctl is-enabled dhcpcd >/dev/null 2>&1; then
    systemctl restart dhcpcd || true
  fi
  if systemctl list-unit-files | grep -q wpa_supplicant; then
    systemctl restart wpa_supplicant@"$IFACE" 2>/dev/null || systemctl restart wpa_supplicant 2>/dev/null || true
  fi
  # Bookworm NetworkManager
  if command -v nmcli >/dev/null 2>&1; then
    nmcli device set "$IFACE" managed yes 2>/dev/null || true
    nmcli device connect "$IFACE" 2>/dev/null || true
  fi
  ip link set "$IFACE" up 2>/dev/null || true
}

start_ap() {
  echo "[autohotspot] → AP $AP_IP ssid=$(hostname_s)"
  write_ap_conf
  # Tắt client trước khi hostapd chiếm radio
  if command -v nmcli >/dev/null 2>&1; then
    nmcli device set "$IFACE" managed no 2>/dev/null || true
    nmcli device disconnect "$IFACE" 2>/dev/null || true
  fi
  # dhcpcd: bỏ quản lý wlan khi AP
  if [[ -f /etc/dhcpcd.conf ]] && ! grep -q "denyinterfaces $IFACE" /etc/dhcpcd.conf; then
    echo "denyinterfaces $IFACE" >> /etc/dhcpcd.conf
    systemctl restart dhcpcd 2>/dev/null || true
  fi
  ip link set "$IFACE" down 2>/dev/null || true
  ip addr flush dev "$IFACE" 2>/dev/null || true
  ip link set "$IFACE" up
  ip addr add "$AP_IP/24" broadcast 10.3.141.255 dev "$IFACE" 2>/dev/null || true
  # hostapd unit trỏ file conf
  if [[ -f /etc/default/hostapd ]]; then
    sed -i 's|^#\\?DAEMON_CONF=.*|DAEMON_CONF="'"$HOSTAPD_CONF"'"|' /etc/default/hostapd
  fi
  systemctl unmask hostapd 2>/dev/null || true
  systemctl restart dnsmasq || true
  systemctl restart hostapd || hostapd -B "$HOSTAPD_CONF" || true
}

client_ok() {
  # Có IP khác AP và (tuỳ chọn) ping được gateway
  local ip
  ip="$(ip -4 -o addr show dev "$IFACE" 2>/dev/null | awk '{print $4}' | cut -d/ -f1 | head -1 || true)"
  [[ -n "$ip" ]] || return 1
  [[ "$ip" != "$AP_IP" ]] || return 1
  # Associated?
  if command -v iwgetid >/dev/null 2>&1; then
    iwgetid -r "$IFACE" >/dev/null 2>&1 || return 1
  fi
  return 0
}

ap_running() {
  ip -4 addr show dev "$IFACE" 2>/dev/null | grep -q "$AP_IP"
}

main() {
  if [[ ! -d /sys/class/net/$IFACE ]]; then
    echo "[autohotspot] no $IFACE — skip"
    exit 0
  fi
  write_ap_conf

  # Đảm bảo có network= trong wpa (placeholder)
  if [[ ! -f "$WPA_CONF" ]]; then
    mkdir -p "$(dirname "$WPA_CONF")"
    cat >"$WPA_CONF" <<'EOF'
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=VN

network={
	ssid="wifi_name"
	psk="wifi_password"
}
EOF
    chmod 600 "$WPA_CONF"
  fi

  # Placeholder SSID → thẳng AP (lần đầu)
  if grep -q 'ssid="wifi_name"' "$WPA_CONF" 2>/dev/null; then
    echo "[autohotspot] chưa cấu hình WiFi nhà → AP"
    start_ap
    exit 0
  fi

  # Nếu đang AP → thử về client trước (user vừa lưu WiFi)
  if ap_running; then
    # Gỡ denyinterfaces tạm để dhcpcd lấy IP
    if [[ -f /etc/dhcpcd.conf ]]; then
      sed -i "/denyinterfaces $IFACE/d" /etc/dhcpcd.conf || true
    fi
    start_client
    sleep 12
    if client_ok; then
      echo "[autohotspot] client OK $(iwgetid -r "$IFACE" 2>/dev/null || true)"
      exit 0
    fi
    start_ap
    exit 0
  fi

  # Đang client hoặc chưa gì
  if client_ok; then
    echo "[autohotspot] already client $(iwgetid -r "$IFACE" 2>/dev/null || echo '?')"
    exit 0
  fi

  # Thử client một nhịp
  if [[ -f /etc/dhcpcd.conf ]]; then
    sed -i "/denyinterfaces $IFACE/d" /etc/dhcpcd.conf || true
  fi
  start_client
  sleep 15
  if client_ok; then
    echo "[autohotspot] client OK"
    exit 0
  fi
  start_ap
}

main "$@"
