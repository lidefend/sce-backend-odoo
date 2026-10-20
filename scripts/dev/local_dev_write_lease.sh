#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
DEFAULT_LOCK_FILE="/tmp/sc-local-dev-sc_dev_demo.write.lock"

if [[ -n "${SC_LOCAL_DEV_WRITE_LOCK_FILE:-}" && "${SC_LOCAL_DEV_WRITE_LOCK_TEST:-}" != "1" ]]; then
  echo "LOCAL_DEV_WRITE_LOCK_OVERRIDE_FORBIDDEN" >&2
  exit 2
fi

LOCK_FILE="${SC_LOCAL_DEV_WRITE_LOCK_FILE:-$DEFAULT_LOCK_FILE}"
OWNER_FILE="${LOCK_FILE}.owner.json"
TIMEOUT="${SC_LOCAL_DEV_WRITE_LOCK_TIMEOUT:-1800}"

usage() {
  cat >&2 <<'EOF'
usage:
  local_dev_write_lease.sh <operation> -- <command...>
  local_dev_write_lease.sh --status
  local_dev_write_lease.sh --require

The fixed local.dev write lease is shared by every worktree using
sc-local-dev / sc_dev_demo. Override the lock file only in tests with
SC_LOCAL_DEV_WRITE_LOCK_TEST=1.
EOF
}

status() {
  exec 9>"$LOCK_FILE"
  if flock -n 9; then
    echo "LOCAL_DEV_WRITE_LEASE_FREE"
    flock -u 9 || true
    return 0
  fi
  echo "LOCAL_DEV_WRITE_LEASE_BUSY"
  if [[ -f "$OWNER_FILE" ]]; then
    cat "$OWNER_FILE"
  fi
  return 1
}

require_lease() {
  if [[ -z "${SC_LOCAL_DEV_WRITE_LEASE_TOKEN:-}" ]]; then
    echo "LOCAL_DEV_WRITE_LEASE_REQUIRED: use the serialized local.dev target, not the internal .run target" >&2
    return 75
  fi
}

write_owner() {
  python3 - "$OWNER_FILE" "$1" "$$" "$ROOT_DIR" <<'PY'
import datetime
import json
import os
import subprocess
import sys

owner_file, operation, pid, root = sys.argv[1:5]

def git(*args):
    try:
        return subprocess.check_output(
            ["git", "-C", root, *args], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return ""

payload = {
    "operation": operation,
    "pid": int(pid),
    "worktree": root,
    "branch": git("branch", "--show-current"),
    "head": git("rev-parse", "HEAD"),
    "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
}
with open(owner_file, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, ensure_ascii=False, indent=2)
    handle.write("\n")
PY
}

case "${1:-}" in
  --status)
    status
    exit $?
    ;;
  --require)
    require_lease
    exit $?
    ;;
  --help|-h)
    usage
    exit 0
    ;;
esac

operation="${1:?operation is required}"
shift
[[ "${1:-}" == "--" ]] && shift
if [[ $# -eq 0 ]]; then
  usage
  exit 2
fi

exec 9>"$LOCK_FILE"
if ! flock -w "$TIMEOUT" 9; then
  echo "LOCAL_DEV_WRITE_LEASE_BUSY after ${TIMEOUT}s" >&2
  if [[ -f "$OWNER_FILE" ]]; then
    cat "$OWNER_FILE" >&2
  fi
  exit 75
fi

token="$(python3 -c 'import uuid; print(uuid.uuid4().hex)')"
export SC_LOCAL_DEV_WRITE_LEASE_TOKEN="$token"
write_owner "$operation"

cleanup() {
  rm -f "$OWNER_FILE"
  flock -u 9 || true
}
trap cleanup EXIT INT TERM

"$@"
