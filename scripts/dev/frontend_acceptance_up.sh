#!/usr/bin/env bash
set -euo pipefail
: "${SC_GOVERNED_ACCEPTANCE_LOWER_ENTRY:?DENY: use make frontend.acceptance.up; direct frontend acceptance startup is forbidden}"
ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
source "$ROOT_DIR/scripts/common/governed_make_entry.sh"
require_governed_make_ancestor "frontend_acceptance_up.sh" "$ROOT_DIR" "frontend.acceptance.up"
PIDFILE="${FRONTEND_ACCEPTANCE_PIDFILE:-/tmp/sc-frontend-acceptance.pid}"
LOGFILE="${FRONTEND_ACCEPTANCE_LOGFILE:-/tmp/sc-frontend-acceptance.log}"
PORT="${FRONTEND_ACCEPTANCE_PORT:-5175}"
MODE="${FRONTEND_ACCEPTANCE_MODE:-development}"
DATABASE="${FRONTEND_ACCEPTANCE_DB:-sc_frontend_acceptance}"
[[ "$MODE" == "development" || "$MODE" == "production" ]] || { echo "[frontend.acceptance.up] DENY unsupported mode=$MODE" >&2; exit 2; }
CANONICAL_DIST="$ROOT_DIR/frontend/apps/web/dist-release"
DIST="${FRONTEND_ACCEPTANCE_STATIC_DIST:-$CANONICAL_DIST}"
if [[ "$MODE" == "production" ]]; then
  [[ "$(readlink -f "$DIST")" == "$(readlink -f "$CANONICAL_DIST")" ]] || { echo "[frontend.acceptance.up] DENY non-canonical production dist=$DIST" >&2; exit 2; }
  [[ -f "$DIST/index.html" ]] || { echo "[frontend.acceptance.up] missing production build: $DIST/index.html" >&2; exit 2; }
fi
[[ "$PIDFILE" == "/tmp/sc-frontend-acceptance.pid" ]] || { echo "[frontend.acceptance.up] DENY non-canonical pidfile=$PIDFILE" >&2; exit 2; }
[[ "$LOGFILE" == "/tmp/sc-frontend-acceptance.log" ]] || { echo "[frontend.acceptance.up] DENY non-canonical logfile=$LOGFILE" >&2; exit 2; }
[[ "$PORT" == "5175" ]] || { echo "[frontend.acceptance.up] DENY non-canonical port=$PORT" >&2; exit 2; }
[[ "$DATABASE" == "sc_frontend_acceptance" ]] || { echo "[frontend.acceptance.up] DENY non-canonical database=$DATABASE" >&2; exit 2; }
[[ "${VITE_API_PROXY_TARGET:-http://127.0.0.1:18082}" == "http://127.0.0.1:18082" ]] || { echo "[frontend.acceptance.up] DENY non-canonical backend target" >&2; exit 2; }
if [[ ! "$DATABASE" =~ ^[a-zA-Z0-9_]+$ ]]; then
  echo "[frontend.acceptance.up] invalid database identifier" >&2
  exit 2
fi

port_open() {
  (exec 3<>"/dev/tcp/127.0.0.1/${PORT}") >/dev/null 2>&1
}

if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  existing_pid="$(cat "$PIDFILE")"
  echo "[frontend.acceptance.up] DENY live pid requires identity validation by the managed runtime wrapper pid=$existing_pid" >&2
  exit 2
fi
rm -f "$PIDFILE"
if port_open; then
  echo "[frontend.acceptance.up] FAIL untracked service already owns port=$PORT" >&2
  exit 2
fi
if [[ "$MODE" == "production" ]]; then
  setsid env STATIC_ROOT="$DIST" STATIC_PORT="$PORT" API_PROXY_TARGET="${VITE_API_PROXY_TARGET:-http://127.0.0.1:18082}" VITE_API_PROXY_TARGET="${VITE_API_PROXY_TARGET:-http://127.0.0.1:18082}" VITE_ODOO_DB="$DATABASE" VITE_ODOO_DB_LOCKED=1 VITE_APP_ENV=acceptance node "$ROOT_DIR/scripts/release/release_static_server.mjs" >"$LOGFILE" 2>&1 &
else
  setsid bash -c 'cd "$1"; export VITE_API_PROXY_TARGET="${VITE_API_PROXY_TARGET:-http://127.0.0.1:18082}" VITE_ODOO_DB="$3" VITE_ODOO_DB_LOCKED=1 VITE_APP_ENV=acceptance; exec scripts/dev/pnpm_exec.sh -C frontend/apps/web dev --host 127.0.0.1 --port "$2" --strictPort' _ "$ROOT_DIR" "$PORT" "$DATABASE" >"$LOGFILE" 2>&1 &
fi
echo $! >"$PIDFILE"
for _ in $(seq 1 30); do
  service_pid="$(cat "$PIDFILE")"
  if ! kill -0 "$service_pid" 2>/dev/null; then
    echo "[frontend.acceptance.up] FAIL service exited during startup; see $LOGFILE" >&2
    rm -f "$PIDFILE"
    exit 1
  fi
  if curl -fsS "http://127.0.0.1:${PORT}/login" >/dev/null 2>&1; then
    sleep 0.25
    if ! kill -0 "$service_pid" 2>/dev/null || ! curl -fsS "http://127.0.0.1:${PORT}/login" >/dev/null 2>&1; then
      echo "[frontend.acceptance.up] FAIL service did not survive the startup stability window; see $LOGFILE" >&2
      rm -f "$PIDFILE"
      exit 1
    fi
    echo "[frontend.acceptance.up] PASS mode=$MODE url=http://127.0.0.1:${PORT} db=$DATABASE"
    exit 0
  fi
  sleep 1
done
echo "[frontend.acceptance.up] FAIL; see $LOGFILE" >&2
exit 1
