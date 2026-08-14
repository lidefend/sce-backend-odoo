#!/usr/bin/env bash
set -euo pipefail
: "${SC_GOVERNED_ACCEPTANCE_LOWER_ENTRY:?DENY: use make frontend.acceptance.down; direct frontend acceptance shutdown is forbidden}"
PIDFILE="${FRONTEND_ACCEPTANCE_PIDFILE:-/tmp/sc-frontend-acceptance.pid}"
PORT="${FRONTEND_ACCEPTANCE_PORT:-5175}"
ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
source "$ROOT_DIR/scripts/common/governed_make_entry.sh"
require_governed_make_ancestor "frontend_acceptance_down.sh" "$ROOT_DIR" "frontend.acceptance.down"
[[ "$PIDFILE" == "/tmp/sc-frontend-acceptance.pid" ]] || { echo "[frontend.acceptance.down] DENY non-canonical pidfile=$PIDFILE" >&2; exit 2; }
[[ "$PORT" == "5175" ]] || { echo "[frontend.acceptance.down] DENY non-canonical port=$PORT" >&2; exit 2; }

port_open() {
  (exec 3<>"/dev/tcp/127.0.0.1/${PORT}") >/dev/null 2>&1
}

if [[ -f "$PIDFILE" ]]; then
  pid="$(cat "$PIDFILE")"
  if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
    [[ "$(readlink -f "/proc/$pid/cwd")" == "$(readlink -f "$ROOT_DIR")" ]] || { echo "[frontend.acceptance.down] DENY process worktree mismatch" >&2; exit 2; }
    process_env="$(tr '\0' '\n' < "/proc/$pid/environ")"
    cmdline_before="$(tr '\0' ' ' < "/proc/$pid/cmdline")"
    starttime_before="$(awk '{print $22}' "/proc/$pid/stat")"
    grep -Fqx 'VITE_ODOO_DB=sc_frontend_acceptance' <<<"$process_env" || { echo "[frontend.acceptance.down] DENY database identity mismatch" >&2; exit 2; }
    grep -Fqx 'VITE_ODOO_DB_LOCKED=1' <<<"$process_env" || { echo "[frontend.acceptance.down] DENY database lock mismatch" >&2; exit 2; }
    grep -Fqx 'VITE_APP_ENV=acceptance' <<<"$process_env" || { echo "[frontend.acceptance.down] DENY app environment mismatch" >&2; exit 2; }
    if [[ "$cmdline_before" == *"release_static_server.mjs"* ]]; then
      grep -Fqx 'STATIC_PORT=5175' <<<"$process_env" || { echo "[frontend.acceptance.down] DENY static port identity mismatch" >&2; exit 2; }
      grep -Fqx "STATIC_ROOT=$ROOT_DIR/frontend/apps/web/dist-release" <<<"$process_env" || { echo "[frontend.acceptance.down] DENY static root identity mismatch" >&2; exit 2; }
      grep -Fqx 'API_PROXY_TARGET=http://127.0.0.1:18082' <<<"$process_env" || { echo "[frontend.acceptance.down] DENY backend identity mismatch" >&2; exit 2; }
    else
      grep -Fqx 'VITE_API_PROXY_TARGET=http://127.0.0.1:18082' <<<"$process_env" || { echo "[frontend.acceptance.down] DENY backend identity mismatch" >&2; exit 2; }
      [[ "$cmdline_before" == *"frontend/apps/web"* && "$cmdline_before" == *"--port 5175"* ]] || { echo "[frontend.acceptance.down] DENY process command identity mismatch" >&2; exit 2; }
    fi
    port_open || { echo "[frontend.acceptance.down] DENY canonical port is not owned by a live service" >&2; exit 2; }
    [[ "$(awk '{print $22}' "/proc/$pid/stat")" == "$starttime_before" ]] || { echo "[frontend.acceptance.down] DENY process starttime changed" >&2; exit 2; }
    [[ "$(tr '\0' ' ' < "/proc/$pid/cmdline")" == "$cmdline_before" ]] || { echo "[frontend.acceptance.down] DENY process command identity changed" >&2; exit 2; }
    kill -- "-$pid" 2>/dev/null || kill "$pid" 2>/dev/null || true
    for _ in $(seq 1 50); do
      kill -0 "$pid" 2>/dev/null || break
      sleep 0.1
    done
    if kill -0 "$pid" 2>/dev/null; then
      kill -KILL -- "-$pid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null || true
    fi
  fi
  rm -f "$PIDFILE"
fi
for _ in $(seq 1 50); do
  port_open || { echo "[frontend.acceptance.down] PASS"; exit 0; }
  sleep 0.1
done
echo "[frontend.acceptance.down] FAIL port=$PORT remained occupied after shutdown" >&2
exit 2
