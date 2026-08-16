<!-- Languages: [Tiếng Việt](README.md) · [English](README.en.md) · [中文](README.zh.md) -->

**Language / Ngôn ngữ / 语言:** [Tiếng Việt](README.md) · [English](README.en.md) · [中文](README.zh.md)

# Cozmars OS

Robot software for **Cozmars V2** on a Raspberry Pi Zero 2W — one process, eight engines.

| Repo | Role |
|------|------|
| **[cozmars-os](https://github.com/haryken/cozmars-os)** (this repo) | Robot brain: Pi / sim HAL, wired web, Xiaozhi, OTA, WiFi, boot splash |
| **[cozmars-sim](https://github.com/haryken/cozmars-sim)** | Laptop virtual robot — fake motors/servos/sensors; **loads** this OS |

Clone them side by side (paths the sim expects by default):

```text
~/Projects/cozmars-os
~/Projects/cozmars-sim
```

Version: `cozmars/version.py` → **1.6.0**

---

## Link with Cozmars Sim (virtual robot)

```text
Laptop
  cozmars-sim  :8088  ← 3D dashboard / mic / cam
       │ spawn
       ▼
  cozmars-os   --hal sim --web :8099
       │ HTTP
       ▼
  sim HAL API  :8088/api/cmd
```

### Quick start

```bash
# Terminal 1 — sim
cd ~/Projects/cozmars-sim
PYTHONPATH=.deps python3 -m cozmars_sim --host 127.0.0.1 --port 8088
# → http://127.0.0.1:8088/

# On the dashboard: «1 · Load source» (or fat if built) → OS spawns
# Wired UI: http://127.0.0.1:8099/
```

Load details (source / fat / SD image): [cozmars-sim/docs/LOAD_SOFTWARE.md](https://github.com/haryken/cozmars-sim/blob/main/docs/LOAD_SOFTWARE.md) · [docs/SIM.md](docs/SIM.md)

---

## Release builds — real Pi vs Docker

Full guide: **[docs/BUILD_RELEASE.md](docs/BUILD_RELEASE.md)**

| Artifact | Command | Machine | Output (`dist/`) |
|----------|---------|---------|------------------|
| Source OTA | `./scripts/pack.sh` | Laptop | `cozmars-<ver>.tgz` |
| **Fat ARM** | `sudo bash scripts/pack-fat.sh` | **Pi ARM** | `cozmars-<ver>-armhf-bundle.tgz` |
| **Fat ARM** | `./scripts/pack-fat-docker.sh` | **Laptop + Docker** (no Pi needed) | same bundle name |
| **SD image** | `./scripts/build-sd-image.sh dist/…-bundle.tgz` | Laptop + Docker (fat required first) | `cozmars-<ver>-pi-zero2w.img.xz` |

### Remote OTA (web) — WireOS-style

Full guide: **[docs/UPDATE.md](docs/UPDATE.md)**

1. Build **Fat ARM** → use **`dist/cozmars-<ver>-armhf-bundle.tgz`** only (not `.img.xz` on the web UI).
2. Host the file over http/https.
3. Robot web → **OS update** → paste URL → wait for progress + log to **100%**.
4. A/B slots: writes inactive slot; power loss mid-install keeps the running slot; boot failure rolls back.

### A. You have a Pi Zero 2W

```bash
# Push code to the Pi, then SSH in:
cd /path/to/cozmars-os
sudo bash scripts/pack-fat.sh
# → dist/cozmars-1.6.0-armhf-bundle.tgz

# Install on a robot (no pip):
sudo bash scripts/install-fat.sh dist/cozmars-*-bundle.tgz
```

First-time dev install (apt + pip on Pi): `./scripts/bootstrap-pi.sh pi@<IP>` — [docs/INSTALL.md](docs/INSTALL.md)

### B. No Pi — Docker on a laptop

```bash
docker info   # must work
cd ~/Projects/cozmars-os
./scripts/pack-fat-docker.sh
# → dist/cozmars-1.6.0-armhf-bundle.tgz
# (armhf Bullseye userspace ≈ Zero 2W 32-bit; does not emulate GPIO)

# Optional — flashable SD image:
./scripts/build-sd-image.sh dist/cozmars-*-bundle.tgz
# → dist/cozmars-1.6.0-pi-zero2w.img.xz
```

Order: **fat first → then image**. Without a bundle file, `build-sd-image.sh` fails clearly.

---

## Engines

| Engine | Role |
|--------|------|
| robot | Motors, head, lift, IR, sonar, button, cliff |
| anim | Eyes, SFX |
| engine | Brain idle / explore / intent |
| cloud | Wake, Xiaozhi |
| switchboard | RPC |
| wired | Web :80/:8080 (sim :8099), WiFi :8077 |
| camera | CSI |
| update | OTA A/B arm-bundle (progress %, rollback) |

## Dependency check

```bash
PYTHONPATH=. python3 -m cozmars.bootcheck
```

WiFi hotspot / portal: [docs/WIFI.md](docs/WIFI.md) · Remote OTA: [docs/UPDATE.md](docs/UPDATE.md)
