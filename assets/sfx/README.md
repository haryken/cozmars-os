# SFX Vector

Extract từ robot Vector (`Play__Robot_Vic_Sfx__*`) → wav 22050 mono, commit vào đây.

Xem `docs/PI_ZERO2W_AUTONOMOUS.md` mục 14 và `cozmars/engines/anim/sfx_catalog.json`.

Thiếu file: OS **synth** SFX (siren / vui / buồn / đập tay) rồi đẩy ra loa sim (cùng đường TTS). Log `[ANIM] SFX … (synth …B)`.

Thay bằng wav thật: `scripts/extract-vector-sfx.sh /path/to/cozmo_resources/sound`.
