# Nạp Cozmars OS lên máy ảo (Cozmars Sim)

Sim **không** QEMU cả Raspberry Pi. Nó giả HAL (motor, servo, cảm biến). OS là process Python thật: `python3 -m cozmars --hal sim`.

Dashboard: http://127.0.0.1:8088/

## Chạy sim

```bash
cd /home/linh/Projects/cozmars-sim
PYTHONPATH=.deps python3 -m cozmars_sim --host 127.0.0.1 --port 8088
```

Mặc định **Test mô hình**: mắt + Wander/gật/lift, không cần OS.

## Nạp phần mềm

Ba cách — UI đã có nút:

### A. Thư mục trên đĩa (tự nhận)

Sim nhìn đúng path:

| Nút | Thư mục phải có |
|-----|-----------------|
| **Nạp cozmars-os** | `/home/linh/Projects/cozmars-os/cozmars/__main__.py` |
| **Nạp rcute-cozmars** | `/home/linh/Projects/rcute-cozmars/rcute_cozmars/robot.py` |

Không được chỉ để README. Clone/đặt repo đúng path trên máy dev.

Sau khi nạp: pill **Phần mềm · đã nạp**. Vẫn đang **test** cho đến khi bấm **Chạy thực tế**.

### B. File `.tgz` (build)

```bash
cd /home/linh/Projects/cozmars-os
chmod +x scripts/pack.sh
./scripts/pack.sh
# → dist/cozmars-1.0.0.tgz
```

Trên dashboard: **Nạp .tgz** → chọn file đó.

Cây trong tar phải có `cozmars/__main__.py` (thường bọc thư mục `cozmars-os/`).

### C. Agent / API

```bash
# nạp thư mục
curl -s -X POST http://127.0.0.1:8088/api/cmd \
  -H 'Content-Type: application/json' \
  -d '{"op":"software_load","source":"cozmars-os"}'

# chạy OS
curl -s -X POST http://127.0.0.1:8088/api/cmd \
  -H 'Content-Type: application/json' \
  -d '{"op":"run_mode","mode":"live"}'
```

Hoặc `POST /api/os/build` — sim gọi `scripts/pack.sh` rồi nạp tarball.

OS live còn mở **http://127.0.0.1:8099/** (wired: About / OTA / Xiaozhi / Games / intent).

## Gỡ phần mềm

Nút **Gỡ** trên panel ST7789. OS process bị kill, về **test mô hình**.

```json
{"op":"software_unload"}
```

## Log thực tế

Panel **OS console** = stdout/stderr của `python3 -m cozmars` (giống terminal).

- `[DEPS] MISS vosk` — thiếu thư viện, OS vẫn chạy
- `[CLOUD] Xiaozhi WSS session=` — đã nối cloud; nói sau wake để chat
- `[ENGINE] boot xong` — não đang idle

## Giọng (sim)

STT trên dashboard là **Chrome Web Speech** (ô ASR), không phải Xiaozhi.

1. Nạp OS → **Chạy thực tế**
2. Bấm **Mở camera + mic**
3. Nói **hey cozmars** (hoặc hey vector / thức dậy)
4. Nói câu hỏi — OS gửi chữ lên Xiaozhi, loa máy phát câu trả lời

Tab OS: http://127.0.0.1:8099/#xiaozhi (radio Xiaozhi mặc định, preset pool tiếng Việt).

Nếu OTA trả mã 6 số: ghép trên https://xiaozhi.me rồi nói lại.
- `[DEPS] OK json` — stdlib ok
- `[ENGINE] boot xong` — não đang idle
- Traceback import — lỗi code

Hardware log bên cạnh vẫn là GPIO ảo (DRIVE/HEAD/SONAR).

## Gỡ rối

| Hiện tượng | Việc |
|------------|------|
| Nạp fail «chỉ README» | Chưa có `cozmars/__main__.py` |
| Live nhưng 3D không nhúc | Xem OS console: `sim POST fail` → sim chưa :8088 |
| Thiếu gpiozero trên laptop | Bình thường — sim không cần GPIO |
| Nút Wander không làm gì | Đang **chạy thực tế** — Wander = intent OS; về **Test mô hình** nếu muốn demo HAL |
