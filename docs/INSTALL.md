# Cài Cozmars OS lên Pi Zero 2W (device thật)

Board: Raspberry Pi Zero 2 W. OS: Raspberry Pi OS Lite **32-bit** (Bullseye ưu tiên vì `picamera`).

Laptop không chạy não. Sau khi cài, rút cáp — robot tự `systemd`.

## 1. raspi-config

SSH, I2C, SPI, Camera (legacy trên Bullseye), hostname, GPU 128 MB.

## 2. Apt

```bash
sudo apt update
sudo apt install -y python3-pip python3-dev python3-cffi \
  libportaudio2 portaudio19-dev libsndfile1 ffmpeg \
  libjpeg-dev zlib1g-dev libatlas-base-dev \
  git avahi-daemon
```

I2S mic INMP441 + loa MAX98357: `arecord -l` / `aplay -l` phải thấy card.

## 3. Copy source + install

Từ laptop (`/home/linh/Projects/cozmars-os`):

```bash
rsync -a --exclude .git --exclude dist cozmars-os/ pi@<IP>:/home/pi/src/cozmars-os/
ssh pi@<IP> 'bash /home/pi/src/cozmars-os/scripts/install-pi.sh'
```

`install-pi.sh` làm:

- `pip install -e /home/pi/src/cozmars-os`
- copy `config/conf.json` + `env.json` vào `/home/pi/.cozmars/` (**không ghi đè** nếu đã cal)
- `systemd enable --now cozmars.service` → `python3 -m cozmars --hal pi --web`

Mở `http://<IP>/`. JSON version: `http://<IP>/about`.

## 4. Dev — sửa từng engine

```bash
cd /home/linh/Projects/cozmars-os
./scripts/deploy.sh 192.168.x.x robot
./scripts/deploy.sh 192.168.x.x anim
./scripts/deploy.sh 192.168.x.x all
```

SCP đúng thư mục rồi `systemctl restart cozmars`. Không đụng `~/.cozmars` trừ `deploy.sh <IP> conf`.

## 5. OTA file `.tgz`

Trên laptop:

```bash
./scripts/pack.sh
# dist/cozmars-1.0.0.tgz + MANIFEST.json bên trong
```

Host file bằng HTTP rồi trên web Pi dán URL `http(s)://…/cozmars-1.0.0.tgz`.

Không đóng `conf.json` đã cal vào tarball. OTA không được ghi `~/.cozmars`.

## 6. Log trên Pi

```bash
journalctl -u cozmars -f
```

Dòng `[DEPS] MISS gpiozero` = thiếu apt/pip. Cài extra:

```bash
sudo python3 -m pip install 'cozmars-os[pi,vision,audio,web]'
```

(từ cây source: `pip install -e '.[pi,vision,audio,web]'`)
