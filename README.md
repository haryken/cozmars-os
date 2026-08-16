# Cozmars OS

Phần mềm robot **Cozmars V2** trên Raspberry Pi Zero 2W — một process, tám engine (như Vector/WireOS).

Repo này là nơi viết OS. Không viết trong `wire-os`. Hai repo `rcute-cozmars*` chỉ là nguyên liệu.

| Engine | Việc |
|--------|------|
| robot | Motor, đầu, lift, IR, sonar, nút, cliff flag |
| anim | Mắt, SFX catalog |
| engine | Brain idle / explore / intent / show |
| cloud | Wake, matcher, Xiaozhi/Vosk stub |
| switchboard | RPC |
| wired | Web :80/:8080 |
| camera | CSI |
| update | OTA `.tgz` |

Version: `cozmars/version.py` → **1.6.0** (Xiaozhi: STT sim/Chrome → OS `/api/wake` → WS tenclass).

## Chạy trên máy ảo (Cozmars Sim)

Xem **[docs/SIM.md](docs/SIM.md)** — nạp thư mục hoặc file `.tgz`, nút Gỡ, log OS.

## Cài lên Pi thật

Một lệnh từ laptop (Pi đã có Raspberry Pi OS + SSH):

```bash
./scripts/bootstrap-pi.sh pi@<IP>
```

Chi tiết: **[docs/INSTALL.md](docs/INSTALL.md)**.

Release **fat ARM** (không pip trên robot) + **image SD**: **[docs/BUILD_RELEASE.md](docs/BUILD_RELEASE.md)**.

## Pack OTA

```bash
chmod +x scripts/*.sh
./scripts/pack.sh                 # source .tgz
# trên Pi ARM: sudo bash scripts/pack-fat.sh   → *-bundle.tgz
# trên PC:     ./scripts/build-sd-image.sh …   → *.img.xz
```

## Kiểm tra thư viện

```bash
python3 scripts/check-deps.py
# hoặc
PYTHONPATH=. python3 -m cozmars.bootcheck
```

Thiếu `gpiozero` / `vosk` / `cv2` **không chặn boot** — in `[DEPS] MISS …` rồi chạy tiếp.
