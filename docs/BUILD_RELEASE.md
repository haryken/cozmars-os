# Build release Cozmars — gói fat ARM + image SD

Hai artifact “nạp là chạy, không pip trên robot”. Làm trong repo **`cozmars-os`**.

| Artifact | File | Máy build | Robot làm gì |
|----------|------|-----------|--------------|
| **Fat ARM** | `dist/cozmars-<ver>-armhf-bundle.tgz` | **Pi ARM** (Zero 2W / Pi 4) | `install-fat.sh` giải nén → `/opt/cozmars` |
| **SD image** | `dist/cozmars-<ver>-pi-zero2w.img.xz` | **PC + Docker** (cần fat trước) | Flash thẻ microSD |

So sánh:

- **Fat** — Pi đã có Raspberry Pi OS (flash Imager bình thường), SSH được, rồi nạp một file bundle.
- **SD image** — giống ý WireOS `.ota`: cả OS trên thẻ; flash xong bật nguồn là robot (splash + hotspot WiFi mở nếu chưa cấu hình).

OTA web (`.tgz` source cũ) vẫn còn; gói `kind=arm-bundle` thì `UpdateEngine` gọi `install-fat` (không pip).

---

## 1) Build gói fat ARM (trên Pi)

```bash
# SSH vào Pi Zero 2W (hoặc Pi ARM), clone/rsync cozmars-os
cd /path/to/cozmars-os
sudo bash scripts/pack-fat.sh
# → dist/cozmars-1.6.0-armhf-bundle.tgz  (hoặc aarch64)
```

Script từ chối chạy trên x86. Bên trong: apt + venv + pip **một lần trên máy build**, rồi đóng tar.

### Cài fat lên robot khác (không pip)

```bash
# Copy .tgz sang robot đích
sudo bash scripts/install-fat.sh /path/to/cozmars-*-bundle.tgz
```

Hoặc OTA URL trỏ tới file `*-bundle.tgz` (MANIFEST `kind: arm-bundle`).

---

## 2) Build image SD (trên laptop/PC)

**Điều kiện:** đã có file fat bundle từ bước 1; Docker đang chạy.

```bash
cd /path/to/cozmars-os
# Copy bundle từ Pi vào dist/ rồi:
./scripts/build-sd-image.sh dist/cozmars-1.6.0-armhf-bundle.tgz
# hoặc:
./scripts/build-sd-image.sh /path/to/cozmars-*-bundle.tgz
```

- Clone `pi-gen` vào `scripts/image/pi-gen/` (gitignored)
- Stage `stage-cozmars` nhét bundle vào rootfs
- Output: `dist/cozmars-<ver>-pi-zero2w.img.xz` + `.sha256`

Build thường **30–90 phút**. Thiếu Docker / thiếu bundle → script **thoát lỗi rõ**, không tạo file giả.

### Flash thẻ

1. Raspberry Pi Imager → **Use custom** → chọn `.img.xz`
2. Hoặc: `xzcat dist/cozmars-*-pi-zero2w.img.xz | sudo dd of=/dev/sdX bs=4M status=progress`

User mặc định image: `pi` / `cozmars` (đổi sau khi vào được). SSH bật. Hostname `cozmars`.

Bật nguồn → splash ST7789 → nếu chưa WiFi nhà thì **hotspot mở** (không mật khẩu) → phone captive portal `http://10.3.141.1/wifi`. Chi tiết: [WIFI.md](WIFI.md).

---

## 3) Dev nhanh (không phải release)

```bash
./scripts/bootstrap-pi.sh pi@<IP>   # apt+pip một lần trên Pi
./scripts/pack.sh                   # .tgz source (OTA cũ)
./scripts/deploy.sh <IP> all        # hot-deploy code
```

Xem [INSTALL.md](INSTALL.md).

---

## Checklist release

1. Bump `cozmars/version.py`
2. `pack-fat.sh` trên Pi → copy bundle về PC
3. `build-sd-image.sh` → publish `.img.xz` + `.sha256` + bundle
4. Ghi chú WiFi 2.4 GHz only (Pi Zero 2W)
