#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
PIDFILE="${FRONTEND_ACCEPTANCE_PIDFILE:-/tmp/sc-frontend-acceptance.pid}"
LOGFILE="${FRONTEND_ACCEPTANCE_LOGFILE:-/tmp/sc-frontend-acceptance.log}"
PORT="${FRONTEND_ACCEPTANCE_PORT:-5175}"
MODE="${FRONTEND_ACCEPTANCE_MODE:-development}"

port_open() {
  (exec 3<>"/dev/tcp/127.0.0.1/${PORT}") >/dev/null 2>&1
}

if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  existing_pid="$(cat "$PIDFILE")"
  if curl -fsS "http://127.0.0.1:${PORT}/login" >/dev/null 2>&1; then
    echo "[frontend.acceptance.up] already healthy pid=$existing_pid port=$PORT db=sc_frontend_acceptance"
    exit 0
  fi
  echo "[frontend.acceptance.up] replacing unhealthy pid=$existing_pid port=$PORT" >&2
  kill -- "-$existing_pid" 2>/dev/null || kill "$existing_pid" 2>/dev/null || true
  wait "$existing_pid" 2>/dev/null || true
  rm -f "$PIDFILE"
fi
rm -f "$PIDFILE"
if port_open; then
  echo "[frontend.acceptance.up] FAIL untracked service already owns port=$PORT" >&2
  exit 2
fi
if [[ "$MODE" == "production" ]]; then
  DIST="${FRONTEND_ACCEPTANCE_STATIC_DIST:-$ROOT_DIR/frontend/apps/web/dist-release}"
  [[ -f "$DIST/index.html" ]] || { echo "[frontend.acceptance.up] missing production build: $DIST/index.html" >&2; exit 2; }
  setsid env STATIC_ROOT="$DIST" STATIC_PORT="$PORT" API_PROXY_TARGET="${VITE_API_PROXY_TARGET:-http://127.0.0.1:18082}" node "$ROOT_DIR/scripts/release/release_static_server.mjs" >"$LOGFILE" 2>&1 &
else
  setsid bash -c 'cd "$1"; export VITE_API_PROXY_TARGET="${VITE_API_PROXY_TARGET:-http://127.0.0.1:18082}" VITE_ODOO_DB=sc_frontend_acceptance VITE_ODOO_DB_LOCKED=1 VITE_APP_ENV=acceptance; exec scripts/dev/pnpm_exec.sh -C frontend/apps/web dev --host 127.0.0.1 --port "$2" --strictPort' _ "$ROOT_DIR" "$PORT" >"$LOGFILE" 2>&1 &
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
    echo "[frontend.acceptance.up] PASS mode=$MODE url=http://127.0.0.1:${PORT} db=sc_frontend_acceptance"
    exit 0
  fi
  sleep 1
done
echo "[frontend.acceptance.up] FAIL; see $LOGFILE" >&2
exit 1
