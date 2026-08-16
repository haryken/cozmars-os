# SFX Vector

Lấy từ WireOS `anki/victor/EXTERNALS/victor-audio-assets` (Wwise `.wem`, codec IMA trong WAV).

```bash
python3 scripts/extract_vector_sfx.py
# hoặc
python3 scripts/extract_vector_sfx.py /path/to/victor-audio-assets
```

Ghi `assets/sfx/Play__Robot_Vic_Sfx__*.wav` 22050 Hz mono s16. Biến thể `_01/_02` → `.2.wav`, `.3.wav` (OS chọn ngẫu nhiên).

Log `[ANIM] SFX … (file …B)` = wav Vector. `(synth …B)` = chưa có file.
