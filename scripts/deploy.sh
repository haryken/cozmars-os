#!/usr/bin/env bash
# Dev deploy: ./scripts/deploy.sh <IP> <engine|all|conf>
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IP="${1:?usage: deploy.sh <IP> <robot|anim|engine|cloud|switchboard|wired|camera|update|all|conf>}"
PART="${2:-all}"
DEST="pi@$IP"
REMOTE="/home/pi/src/cozmars-os"

declare -A DIR=(
  [robot]=cozmars/engines/robot/
  [anim]=cozmars/engines/anim/
  [engine]=cozmars/engines/engine/
  [cloud]=cozmars/engines/cloud/
  [switchboard]=cozmars/engines/switchboard/
  [wired]=cozmars/engines/wired/
  [camera]=cozmars/engines/camera/
  [update]=cozmars/engines/update/
)

ssh "$DEST" "mkdir -p $REMOTE"
if [[ "$PART" == "all" ]]; then
  rsync -az --exclude .git --exclude dist --exclude __pycache__ "$ROOT/" "$DEST:$REMOTE/"
elif [[ "$PART" == "conf" ]]; then
  scp "$ROOT/config/conf.json" "$DEST:/home/pi/.cozmars/conf.json"
else
  [[ -n "${DIR[$PART]:-}" ]] || { echo "unknown engine $PART"; exit 1; }
  rsync -az "$ROOT/${DIR[$PART]}" "$DEST:$REMOTE/${DIR[$PART]}"
fi
ssh "$DEST" "sudo systemctl restart cozmars.service || true"
echo "deployed $PART → $IP"
