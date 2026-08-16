# Cozmars OS

Phần mềm robot **Cozmars V2** trên Raspberry Pi Zero 2W — một process, tám engine.

| Repo | Vai trò |
|------|---------|
| **[cozmars-os](https://github.com/haryken/cozmars-os)** (repo này) | Não robot: HAL Pi / sim, wired web, Xiaozhi, OTA, WiFi, boot splash |
| **[cozmars-sim](https://github.com/haryken/cozmars-sim)** | Máy ảo trên laptop — giả motor/servo/cảm biến; **nạp** OS từ repo này |

Clone cạnh nhau (path mặc định sim đang trỏ):

```text
~/Projects/cozmars-os
~/Projects/cozmars-sim
```

Version: `cozmars/version.py` → **1.6.0**

---

## Liên kết với Cozmars Sim (máy ảo)

```text
Laptop
  cozmars-sim  :8088  ← dashboard 3D / mic / cam
       │ spawn
       ▼
  cozmars-os   --hal sim --web :8099
       │ HTTP
       ▼
  sim HAL API  :8088/api/cmd
```

### Chạy nhanh

```bash
# Terminal 1 — sim
cd ~/Projects/cozmars-sim
PYTHONPATH=.deps python3 -m cozmars_sim --host 127.0.0.1 --port 8088
# → http://127.0.0.1:8088/

# Trên dashboard: «1 · Nạp source» (hoặc fat nếu đã build) → OS tự spawn
# Wired UI: http://127.0.0.1:8099/
```

Chi tiết nạp (source / fat / image SD): [cozmars-sim/docs/LOAD_SOFTWARE.md](https://github.com/haryken/cozmars-sim/blob/main/docs/LOAD_SOFTWARE.md) · [docs/SIM.md](docs/SIM.md)

---

## Build release — Pi thật vs Docker

Chi tiết đầy đủ: **[docs/BUILD_RELEASE.md](docs/BUILD_RELEASE.md)**

| Artifact | Lệnh | Máy | File ra (`dist/`) |
|----------|------|-----|-------------------|
| Source OTA | `./scripts/pack.sh` | Laptop | `cozmars-<ver>.tgz` |
| **Fat ARM** | `sudo bash scripts/pack-fat.sh` | **Pi ARM** | `cozmars-<ver>-armhf-bundle.tgz` |
| **Fat ARM** | `./scripts/pack-fat-docker.sh` | **Laptop + Docker** (không cần Pi) | cùng tên bundle |
| **SD image** | `./scripts/build-sd-image.sh dist/…-bundle.tgz` | Laptop + Docker (cần fat trước) | `cozmars-<ver>-pi-zero2w.img.xz` |

### A. Có Pi Zero 2W

```bash
# Đưa code lên Pi rồi SSH:
cd /path/to/cozmars-os
sudo bash scripts/pack-fat.sh
# → dist/cozmars-1.6.0-armhf-bundle.tgz

# Cài robot (không pip):
sudo bash scripts/install-fat.sh dist/cozmars-*-bundle.tgz
```

Dev lần đầu (apt + pip trên Pi): `./scripts/bootstrap-pi.sh pi@<IP>` — [docs/INSTALL.md](docs/INSTALL.md)

### B. Không có Pi — Docker trên laptop

```bash
docker info   # phải OK
cd ~/Projects/cozmars-os
./scripts/pack-fat-docker.sh
# → dist/cozmars-1.6.0-armhf-bundle.tgz
# (armhf Bullseye userspace ≈ Zero 2W 32-bit; không giả GPIO)

# Tuỳ chọn — image flash thẻ:
./scripts/build-sd-image.sh dist/cozmars-*-bundle.tgz
# → dist/cozmars-1.6.0-pi-zero2w.img.xz
```

Thứ tự: **fat trước → image sau**. Không có file bundle thì `build-sd-image.sh` báo lỗi.

---

## Engines

| Engine | Việc |
|--------|------|
| robot | Motor, đầu, lift, IR, sonar, nút, cliff |
| anim | Mắt, SFX |
| engine | Brain idle / explore / intent |
| cloud | Wake, Xiaozhi |
| switchboard | RPC |
| wired | Web :80/:8080 (sim :8099), WiFi :8077 |
| camera | CSI |
| update | OTA `.tgz` / arm-bundle |

## Kiểm tra deps

```bash
PYTHONPATH=. python3 -m cozmars.bootcheck
```

WiFi hotspot / portal: [docs/WIFI.md](docs/WIFI.md)
