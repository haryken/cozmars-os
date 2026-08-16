<!-- Languages: [Tiếng Việt](README.md) · [English](README.en.md) · [中文](README.zh.md) -->

**Language / Ngôn ngữ / 语言:** [Tiếng Việt](README.md) · [English](README.en.md) · [中文](README.zh.md)

# Cozmars OS

运行在 **Raspberry Pi Zero 2W** 上的 **Cozmars V2** 机器人软件 — 单进程、八个引擎。

| 仓库 | 作用 |
|------|------|
| **[cozmars-os](https://github.com/haryken/cozmars-os)**（本仓库） | 机器人大脑：Pi / sim HAL、wired 网页、Xiaozhi、OTA、WiFi、开机动画 |
| **[cozmars-sim](https://github.com/haryken/cozmars-sim)** | 笔记本上的虚拟机器人 — 模拟电机/舵机/传感器；从本仓库**加载** OS |

请并排放置两个仓库（sim 默认路径）：

```text
~/Projects/cozmars-os
~/Projects/cozmars-sim
```

版本：`cozmars/version.py` → **1.6.0**

---

## 与 Cozmars Sim（虚拟机）的关系

```text
Laptop
  cozmars-sim  :8088  ← 3D 控制台 / 麦克风 / 摄像头
       │ spawn
       ▼
  cozmars-os   --hal sim --web :8099
       │ HTTP
       ▼
  sim HAL API  :8088/api/cmd
```

### 快速运行

```bash
# 终端 1 — sim
cd ~/Projects/cozmars-sim
PYTHONPATH=.deps python3 -m cozmars_sim --host 127.0.0.1 --port 8088
# → http://127.0.0.1:8088/

# 在面板点 «1 · 加载 source»（或已构建的 fat）→ 自动启动 OS
# Wired 界面: http://127.0.0.1:8099/
```

加载说明（source / fat / SD 镜像）：[cozmars-sim/docs/LOAD_SOFTWARE.md](https://github.com/haryken/cozmars-sim/blob/main/docs/LOAD_SOFTWARE.md) · [docs/SIM.md](docs/SIM.md)

---

## 发布构建 — 真机 Pi vs Docker

完整文档：**[docs/BUILD_RELEASE.md](docs/BUILD_RELEASE.md)**

| 产物 | 命令 | 机器 | 输出（`dist/`） |
|------|------|------|-----------------|
| Source OTA | `./scripts/pack.sh` | 笔记本 | `cozmars-<ver>.tgz` |
| **Fat ARM** | `sudo bash scripts/pack-fat.sh` | **Pi ARM** | `cozmars-<ver>-armhf-bundle.tgz` |
| **Fat ARM** | `./scripts/pack-fat-docker.sh` | **笔记本 + Docker**（无需 Pi） | 同名 bundle |
| **SD 镜像** | `./scripts/build-sd-image.sh dist/…-bundle.tgz` | 笔记本 + Docker（必须先有 fat） | `cozmars-<ver>-pi-zero2w.img.xz` |

### 远程 OTA（网页）— 类似 WireOS

完整说明：**[docs/UPDATE.md](docs/UPDATE.md)**

1. 构建 **Fat ARM** → 只用 **`dist/cozmars-<ver>-armhf-bundle.tgz`**（网页不要用 `.img.xz`）。
2. 把文件放到可 http/https 下载的地址。
3. 打开机器人网页 → **更新 OS** → 粘贴 URL → 等进度条 + 日志到 **100%**。
4. A/B 槽：写入空闲槽；中途断电不删当前槽；启动失败自动回滚。

### A. 有 Pi Zero 2W

```bash
# 把代码放到 Pi 后 SSH：
cd /path/to/cozmars-os
sudo bash scripts/pack-fat.sh
# → dist/cozmars-1.6.0-armhf-bundle.tgz

# 安装到机器人（不再 pip）：
sudo bash scripts/install-fat.sh dist/cozmars-*-bundle.tgz
```

首次开发安装（Pi 上 apt + pip）：`./scripts/bootstrap-pi.sh pi@<IP>` — [docs/INSTALL.md](docs/INSTALL.md)

### B. 没有 Pi — 笔记本 Docker

```bash
docker info   # 必须正常
cd ~/Projects/cozmars-os
./scripts/pack-fat-docker.sh
# → dist/cozmars-1.6.0-armhf-bundle.tgz
# （armhf Bullseye 用户态 ≈ Zero 2W 32 位；不模拟 GPIO）

# 可选 — 可刷写的 SD 镜像：
./scripts/build-sd-image.sh dist/cozmars-*-bundle.tgz
# → dist/cozmars-1.6.0-pi-zero2w.img.xz
```

顺序：**先 fat → 再 image**。没有 bundle 时 `build-sd-image.sh` 会明确报错。

---

## 引擎

| 引擎 | 作用 |
|------|------|
| robot | 电机、头部、抬升、IR、超声、按键、悬崖 |
| anim | 眼睛、音效 |
| engine | 大脑 idle / 探索 / 意图 |
| cloud | 唤醒、Xiaozhi |
| switchboard | RPC |
| wired | Web :80/:8080（sim :8099）、WiFi :8077 |
| camera | CSI |
| update | OTA A/B arm-bundle（进度条、回滚） |

## 依赖检查

```bash
PYTHONPATH=. python3 -m cozmars.bootcheck
```

WiFi 热点 / 配置页：[docs/WIFI.md](docs/WIFI.md) · 远程 OTA：[docs/UPDATE.md](docs/UPDATE.md)
