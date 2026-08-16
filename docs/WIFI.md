# WiFi Cozmars (Pi Zero 2W)

Board có **WiFi 2.4 GHz** + Bluetooth sẵn. Không cần dongle.

## Hai cách vào trang cấu hình

| Khi | Cách |
|-----|------|
| Mất mạng / lần đầu | Robot phát **hotspot mở** (SSID = hostname, **không mật khẩu**). Phone nối → hệ thống tự mở trang WiFi (captive portal). Cũng vào được `http://10.3.141.1/wifi` |
| Đã có LAN | `http://<ip-robot>:8077/` hoặc `http://<hostname>.local:8077/` |

## Luồng user

1. Nối hotspot robot (không cần MK)
2. Trang cấu hình hiện tự động → gõ SSID nhà (2.4 GHz) + mật khẩu ≥ 8 ký tự → **Áp dụng mạng**
3. Chờ ~30–60s → robot tắt hotspot, vào WiFi nhà → `http://<hostname>.local/`

## Service

- `cozmars-autohotspot.service` — oneshot lúc boot
- `cozmars-autohotspot.timer` — retry mỗi 2 phút
- Script: `/usr/local/bin/cozmars-autohotspot`

Cài: `sudo bash scripts/install-wifi.sh` (đã gọi từ `install-pi.sh`).
