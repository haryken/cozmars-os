#!/usr/bin/env bash
# Extract Vector Robot_Vic_Sfx from a robot (or local dump) → assets/sfx/*.wav 22050 mono s16.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${1:-/tmp/vector-sound}"
OUT="$ROOT/assets/sfx"
mkdir -p "$OUT"
if [[ ! -d "$SRC" ]]; then
  echo "usage: $0 /path/to/cozmo_resources/sound"
  echo "example: scp -r root@VECTOR:/anki/data/assets/cozmo_resources/sound /tmp/vector-sound"
  exit 1
fi
shopt -s globstar nullglob
n=0
for wem in "$SRC"/**/*.wem "$SRC"/**/*.wav; do
  base="$(basename "$wem")"
  stem="${base%.*}"
  dst="$OUT/${stem}.wav"
  ffmpeg -y -loglevel error -i "$wem" -ac 1 -ar 22050 -sample_fmt s16 "$dst" && n=$((n+1)) || true
done
echo "extracted $n files → $OUT"
