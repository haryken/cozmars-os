#!/usr/bin/env bash
# Thư viện slot A/B cho Cozmars (ý WireOS: cập nhật slot nghỉ, đảo active, rollback nếu boot hỏng).
# Không phải phân vùng kernel Android — Pi OS một rootfs; app sống ở /opt/cozmars-{a,b}.
#
# Layout:
#   /opt/cozmars-a|b/     nội dung fat (venv, src, …)
#   /opt/cozmars -> cozmars-{a|b}   symlink active
#   /etc/cozmars/active-slot        a|b
#   /etc/cozmars/previous-slot      a|b (để rollback)
#   /etc/cozmars/boot-state         ok|pending
#   /etc/cozmars/boot-tries         số lần thử boot slot pending

COZMARS_ETC="${COZMARS_ETC:-/etc/cozmars}"
COZMARS_OPT_ROOT="${COZMARS_OPT_ROOT:-/opt}"
COZMARS_LINK="${COZMARS_LINK:-$COZMARS_OPT_ROOT/cozmars}"
COZMARS_MAX_BOOT_TRIES="${COZMARS_MAX_BOOT_TRIES:-3}"

slot_path() {
  local s="${1:?}"
  echo "$COZMARS_OPT_ROOT/cozmars-$s"
}

slot_ensure_etc() {
  mkdir -p "$COZMARS_ETC"
}

slot_read() {
  local f="$COZMARS_ETC/$1"
  [[ -f "$f" ]] && tr -d '[:space:]' < "$f" || true
}

slot_write() {
  local key="$1" val="$2"
  slot_ensure_etc
  printf '%s\n' "$val" > "$COZMARS_ETC/$key"
}

slot_active() {
  local s
  s="$(slot_read active-slot)"
  if [[ "$s" == "a" || "$s" == "b" ]]; then
    echo "$s"
    return
  fi
  if [[ -L "$COZMARS_LINK" ]]; then
    local t
    t="$(readlink "$COZMARS_LINK" || true)"
    case "$t" in
      *cozmars-a) echo a; return ;;
      *cozmars-b) echo b; return ;;
    esac
  fi
  echo a
}

slot_other() {
  case "$(slot_active)" in
    a) echo b ;;
    *) echo a ;;
  esac
}

# Lần đầu: /opt/cozmars là thư mục thật → chuyển thành slot a + symlink.
slot_migrate_legacy() {
  slot_ensure_etc
  if [[ -L "$COZMARS_LINK" ]]; then
    return 0
  fi
  if [[ -d "$COZMARS_LINK" ]]; then
    echo "[slot] migrate legacy $COZMARS_LINK → $(slot_path a)"
    rm -rf "$(slot_path a)"
    mv "$COZMARS_LINK" "$(slot_path a)"
    ln -sfn "cozmars-a" "$COZMARS_LINK"
    slot_write active-slot a
    slot_write previous-slot a
    slot_write boot-state ok
    slot_write boot-tries 0
    return 0
  fi
  # Chưa có gì: tạo khung
  mkdir -p "$(slot_path a)" "$(slot_path b)"
  if [[ ! -e "$COZMARS_LINK" ]]; then
    ln -sfn "cozmars-a" "$COZMARS_LINK"
  fi
  [[ -f "$COZMARS_ETC/active-slot" ]] || slot_write active-slot a
  [[ -f "$COZMARS_ETC/boot-state" ]] || slot_write boot-state ok
  [[ -f "$COZMARS_ETC/boot-tries" ]] || slot_write boot-tries 0
}

slot_set_active() {
  local new="${1:?}"
  local prev
  prev="$(slot_active)"
  [[ "$new" == "a" || "$new" == "b" ]] || return 1
  [[ -d "$(slot_path "$new")" ]] || return 1
  slot_write previous-slot "$prev"
  # Atomic-ish: symlink mới rồi rename đè (ln -sfn)
  ln -sfn "cozmars-$new" "$COZMARS_LINK"
  slot_write active-slot "$new"
  slot_write boot-state pending
  slot_write boot-tries 0
  echo "[slot] active=$new (was $prev) boot-state=pending"
}

slot_mark_boot_ok() {
  slot_write boot-state ok
  slot_write boot-tries 0
  echo "[slot] boot-ok active=$(slot_active)"
}

slot_rollback() {
  local prev
  prev="$(slot_read previous-slot)"
  if [[ "$prev" != "a" && "$prev" != "b" ]]; then
    echo "[slot] rollback: không có previous-slot" >&2
    return 1
  fi
  if [[ ! -d "$(slot_path "$prev")" ]]; then
    echo "[slot] rollback: thiếu $(slot_path "$prev")" >&2
    return 1
  fi
  echo "[slot] ROLLBACK → $prev"
  ln -sfn "cozmars-$prev" "$COZMARS_LINK"
  slot_write active-slot "$prev"
  slot_write boot-state ok
  slot_write boot-tries 0
}

slot_verify() {
  local s="${1:?}"
  local root
  root="$(slot_path "$s")"
  [[ -x "$root/venv/bin/python" ]] || return 1
  [[ -d "$root/src/cozmars" ]] || return 1
  return 0
}
