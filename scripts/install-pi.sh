#!/usr/bin/env bash
# Chạy trên Pi: bash scripts/install-pi.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
sudo python3 -m pip install -e "$ROOT"
mkdir -p /home/pi/.cozmars
cp -n "$ROOT/config/conf.json" /home/pi/.cozmars/conf.json || true
cp -n "$ROOT/config/env.json" /home/pi/.cozmars/env.json || true
sudo cp "$ROOT/systemd/cozmars.service" /etc/systemd/system/cozmars.service
if [[ -f "$ROOT/systemd/cozmars.avahi.service" ]]; then
  sudo mkdir -p /etc/avahi/services
  sudo cp "$ROOT/systemd/cozmars.avahi.service" /etc/avahi/services/ || true
fi
sudo systemctl daemon-reload
sudo systemctl enable --now cozmars.service
echo "Cozmars OS installed. Open http://$(hostname -I | awk '{print $1}')/"
