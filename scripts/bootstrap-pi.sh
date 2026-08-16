#!/usr/bin/env bash
# Từ laptop: ./scripts/bootstrap-pi.sh pi@192.168.x.x
# Copy source + chạy install-pi.sh trên robot.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${1:?usage: bootstrap-pi.sh pi@<IP>}"
REMOTE="${2:-/home/pi/src/cozmars-os}"

echo "[bootstrap] rsync → $DEST:$REMOTE"
ssh "$DEST" "mkdir -p $REMOTE"
rsync -az --delete \
  --exclude .git --exclude dist --exclude __pycache__ --exclude .venv \
  --exclude '*.pyc' \
  "$ROOT/" "$DEST:$REMOTE/"
# Wheel offline nếu đã fetch trên laptop
if [[ -d "$ROOT/dist/wheels" ]] && compgen -G "$ROOT/dist/wheels/*.whl" >/dev/null; then
  echo "[bootstrap] copy dist/wheels"
  rsync -az "$ROOT/dist/wheels/" "$DEST:$REMOTE/dist/wheels/"
fi
echo "[bootstrap] install trên Pi (apt + venv)…"
ssh -t "$DEST" "bash $REMOTE/scripts/install-pi.sh"
echo "[bootstrap] xong"
