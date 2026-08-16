# Cập nhật OS từ xa (OTA)

Giống WireOS `:8080`: dán **link http/https** trên web → thanh tiến trình + log → **100%**. Có **slot A/B** an toàn (ghi slot nghỉ, không xoá bản đang chạy; boot lỗi 3 lần → rollback).

## Lấy file nào từ build?

| File trong `dist/` | Cập nhật từ xa (web)? | Khi nào dùng |
|--------------------|------------------------|--------------|
| **`cozmars-<ver>-armhf-bundle.tgz`** | **Có — chỉ file này** | OTA trên web / `install-fat.sh` |
| `cozmars-<ver>-pi-zero2w.img.xz` | **Không** | Flash thẻ SD máy mới |
| `cozmars-<ver>.tgz` (source `pack.sh`) | **Không** (không đủ A/B fat) | Dev / legacy |

Build fat:

```bash
cd ~/Projects/cozmars-os
./scripts/pack-fat-docker.sh          # laptop + Docker
# hoặc trên Pi: sudo bash scripts/pack-fat.sh
# → dist/cozmars-1.6.0-armhf-bundle.tgz
```

## Cách cập nhật từ xa

1. Đưa file bundle lên chỗ tải được bằng URL (GitHub Release, Cloudflare, hoặc LAN):
   ```bash
   # ví dụ LAN từ máy build:
   cd dist && python3 -m http.server 8000
   # URL: http://<IP-laptop>:8000/cozmars-1.6.0-armhf-bundle.tgz
   ```
2. Mở web robot (cùng WiFi):
   - Pi thật: `http://<IP-robot>/` hoặc `:8080`
   - Sim: `http://127.0.0.1:8099/` (chỉ verify, không ghi `/opt`)
3. Menu **Cập nhật OS** → dán URL đầy đủ → **Cập nhật từ URL**.
4. Đợi thanh tiến trình tới **100%** và log báo xong. Giữ nguồn ổn định.
5. Robot restart service → F5 sau vài giây. Tab About / `/about` có `slots.active`.

## Slot A/B (an toàn)

- `/opt/cozmars-a` · `/opt/cozmars-b` · symlink `/opt/cozmars` → slot đang chạy  
- Cài vào **slot nghỉ** → verify → mới đảo active  
- Cúp điện lúc cài slot nghỉ → bật lại vẫn chạy bản cũ  
- Boot slot mới fail ≥ 3 lần → `cozmars-boot-guard` rollback  

Chi tiết kỹ thuật: layout `/etc/cozmars/*`, API — xem phần dưới và [BUILD_RELEASE.md](BUILD_RELEASE.md).

## API (nếu cần)

- `POST /api/update` body `{"url":"https://…/cozmars-…-armhf-bundle.tgz"}`
- `GET /api/update/status` → `percent`, `phase`, `done`, `error`, `slots`

## Layout kỹ thuật

| Đường dẫn | Vai trò |
|-----------|---------|
| `/opt/cozmars-a` / `-b` | Hai slot |
| `/opt/cozmars` | Symlink active |
| `/etc/cozmars/active-slot` | `a` hoặc `b` |
| `/etc/cozmars/previous-slot` | Rollback |
| `/etc/cozmars/boot-state` | `ok` / `pending` |

> Khác WireOS: Vector flip phân vùng disk Android; Cozmars trên Pi OS flip **app** dưới `/opt` (cùng ý an toàn cho phần mềm robot).
