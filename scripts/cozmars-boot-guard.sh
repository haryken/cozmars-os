#!/usr/bin/env bash
# ExecStartPre: nếu slot mới (pending) boot fail quá N lần → rollback slot cũ.
set -euo pipefail
# shellcheck disable=SC1091
if [[ -f /usr/local/lib/cozmars/slot-lib.sh ]]; then
  source /usr/local/lib/cozmars/slot-lib.sh
elif [[ -f /opt/cozmars/src/scripts/slot-lib.sh ]]; then
  source /opt/cozmars/src/scripts/slot-lib.sh
elif [[ -f /opt/cozmars/slot-lib.sh ]]; then
  source /opt/cozmars/slot-lib.sh
else
  exit 0
fi

slot_migrate_legacy || true
STATE="$(slot_read boot-state)"
if [[ "$STATE" != "pending" ]]; then
  exit 0
fi

TRIES="$(slot_read boot-tries)"
TRIES="${TRIES:-0}"
if ! [[ "$TRIES" =~ ^[0-9]+$ ]]; then
  TRIES=0
fi
TRIES=$((TRIES + 1))
slot_write boot-tries "$TRIES"
echo "[boot-guard] pending slot=$(slot_active) try=$TRIES/$COZMARS_MAX_BOOT_TRIES"

if [[ "$TRIES" -ge "$COZMARS_MAX_BOOT_TRIES" ]]; then
  echo "[boot-guard] quá số lần thử — rollback"
  slot_rollback || true
  systemctl daemon-reload || true
fi
exit 0
