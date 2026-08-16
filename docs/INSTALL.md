# Cài Cozmars OS lên Pi Zero 2W

Board: Raspberry Pi Zero 2 W + Raspberry Pi OS Lite **32-bit** (Bullseye ưu tiên vì `picamera`).

**Không** copy source rồi `python3` chạy tay. Một lệnh từ laptop:

```bash
cd /home/linh/Projects/cozmars-os
chmod +x scripts/*.sh
./scripts/bootstrap-pi.sh pi@<IP>
```

Script copy source sang Pi rồi chạy `install-pi.sh`. Trên Pi nó:

1. `apt` — `gpiozero`, `numpy`, `opencv`, PIL, portaudio (không pip compile trên 512 MB)
2. Venv `/opt/cozmars/venv` (`--system-site-packages` để dùng gói apt)
3. `pip install -e '.[pi,audio,web]'` — Adafruit ST7789/servo, `aiohttp`, `sounddevice`
4. Bật I2C / SPI / Camera nếu có `raspi-config`
5. Bật splash ST7789 + `systemd` Cozmars (bật nguồn → logo → robot, không chờ mạng)
6. WiFi: autohotspot + portal `:8077`

Mở `http://<IP>/`. Log: `journalctl -u cozmars -f`.

Bật nguồn: LCD ST7789 hiện **Cozmars + serial + chấm nhấp** (`cozmars-bootanim`) trong lúc kernel/Python lên; khi OS sẵn sàng thì tắt splash (giữ frame, rồi mắt chiếm màn). Log splash: `journalctl -u cozmars-bootanim -f`.

## Test splash trên máy ảo (không cần Pi)

Sim **không** có SPI/ST7789. Logo hiện trên canvas LCD + mặt 3D tại http://127.0.0.1:8088/

1. Chạy sim, hard-refresh dashboard (`Ctrl+Shift+R`).
2. **Xem splash** — logo ~5 giây (không cần nạp OS).
3. Hoặc **Nạp cozmars-os** → **Chạy thực tế**: splash trong lúc spawn, tắt khi OS in `[BOOT] sim splash off`.

Xuất GIF (cùng `render_frame` như trên Pi):

```bash
cd /home/linh/Projects/cozmars-os
PYTHONPATH=. python3 -m cozmars.bootanim --preview
# → /tmp/cozmars-bootanim.gif
```

Cần SSH được `pi@<IP>` (mật khẩu hoặc key) và Pi đã flash Raspberry Pi OS, có mạng.

## (Tuỳ chọn) wheel offline — ít phụ thuộc pip lúc cài

Trên laptop có mạng:

```bash
./scripts/fetch-pi-wheels.sh 39    # Bullseye Python 3.9
# hoặc: ./scripts/fetch-pi-wheels.sh 311   # Bookworm 3.11
./scripts/bootstrap-pi.sh pi@<IP>
```

OpenCV/NumPy **không** nằm trong wheel pip — luôn lấy từ apt trên Pi.

## Dev — sửa code rồi đẩy lại

```bash
./scripts/deploy.sh 192.168.x.x all
```

Không ghi đè `~/.cozmars` (calib) trừ `./scripts/deploy.sh <IP> conf`.

## WiFi (lần đầu / đổi mạng)

Pi Zero 2W chỉ **WiFi 2.4 GHz** (+ Bluetooth sẵn trên board).

| Tình trạng | Cách vào trang cấu hình |
|------------|-------------------------|
| **Mất / chưa có WiFi nhà** | Robot phát **hotspot mở** (SSID = hostname, không mật khẩu). Phone nối → tự mở trang cấu hình. Hoặc `http://10.3.141.1/wifi` |
| **Đã vào LAN** | `http://<ip-robot>:8077/` hoặc `http://<hostname>.local:8077/` — hoặc link WiFi trên trang About |

Luồng: nối hotspot → gõ SSID nhà → **Áp dụng mạng** → chờ ~30–60s → robot vào WiFi nhà.

Service: `cozmars-autohotspot.service` + timer 2 phút. Log: `journalctl -u cozmars-autohotspot -n 50`.

Cài lại riêng: `sudo bash scripts/install-wifi.sh`.

## OTA `.tgz`

```bash
./scripts/pack.sh                    # source (OTA cũ)
# Trên Pi ARM: sudo bash scripts/pack-fat.sh   → *-armhf-bundle.tgz (không pip trên robot)
```

Dán URL file trên web Pi. Bundle `kind=arm-bundle` → `install-fat` (không pip). Không đóng `conf.json` đã cal vào tarball.

## Release fat + image SD

Hướng dẫn build đầy đủ: **[BUILD_RELEASE.md](BUILD_RELEASE.md)**

- Fat ARM: `scripts/pack-fat.sh` (trên Pi) → `install-fat.sh` trên robot
- SD image: `scripts/build-sd-image.sh` (PC + Docker, cần fat trước) → flash `.img.xz`
