#!/usr/bin/env bash
# Extract Vector Robot_Vic_Sfx from WireOS victor-audio-assets → assets/sfx/*.wav
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${1:-/home/linh/Projects/wire-os/anki/victor/EXTERNALS/victor-audio-assets}"
exec python3 "$ROOT/scripts/extract_vector_sfx.py" "$SRC"
