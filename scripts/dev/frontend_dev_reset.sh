#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
PORT="${VITE_DEV_PORT:-5174}"
HOST="${VITE_DEV_HOST:-127.0.0.1}"
FRONTEND_PROFILE="${FRONTEND_PROFILE:-local-dev}"
PROXY_TARGET_DEFAULT="${VITE_API_PROXY_TARGET:-}"
PIDFILE="${FRONTEND_DEV_PIDFILE:-/tmp/sc-frontend-dev.pid}"
LOGFILE="${FRONTEND_DEV_LOGFILE:-/tmp/sc-frontend-dev.log}"
READY_URL="${FRONTEND_DEV_READY_URL:-http://${HOST}:${PORT}/}"
REAL_HOME="${SNAP_REAL_HOME:-$HOME}"
NVM_ROOT="${NVM_DIR:-${REAL_HOME}/.nvm}"
NVM_SH="${NVM_SH:-${NVM_ROOT}/nvm.sh}"
TMUX_SESSION="${FRONTEND_DEV_TMUX_SESSION:-sc-frontend-dev}"
ENV_NAME="${ENV:-dev}"
ENV_FILE="${ENV_FILE:-}"
if [[ -z "${ENV_FILE}" && -f "${ROOT_DIR}/.env.${ENV_NAME}" ]]; then
  ENV_FILE="${ROOT_DIR}/.env.${ENV_NAME}"
fi
if [[ -n "${ENV_FILE}" && -f "${ENV_FILE}" ]]; then
  _pre_DB_NAME="${DB_NAME:-}"
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
  [[ -n "${_pre_DB_NAME}" ]] && DB_NAME="${_pre_DB_NAME}"
fi

if [[ -s "${NVM_SH}" ]]; then
  # shellcheck disable=SC1090
  . "${NVM_SH}"
fi
if [[ -d "${NVM_ROOT}/versions/node" ]]; then
  latest_node_bin="$(find "${NVM_ROOT}/versions/node" -maxdepth 2 -type d -name bin | sort | tail -n 1)"
  if [[ -n "${latest_node_bin:-}" ]]; then
    export PATH="${latest_node_bin}:$PATH"
  fi
fi

resolve_profile_defaults() {
  case "${FRONTEND_PROFILE}" in
    local-dev|daily)
      PROFILE_DB="${FRONTEND_DAILY_DB:-${DB_NAME:-sc_dev_demo}}"
      PROFILE_PROXY_TARGET="http://127.0.0.1:${ODOO_PORT:-8070}"
      ;;
    test)
      PROFILE_DB="sc_test"
      PROFILE_PROXY_TARGET="http://127.0.0.1:8071"
      ;;
    uat|prod-sim)
      PROFILE_DB="sc_prod_sim"
      PROFILE_PROXY_TARGET="http://127.0.0.1:18069"
      ;;
    partner-acceptance)
      PROFILE_DB="sc_partner_acceptance"
      PROFILE_PROXY_TARGET="http://127.0.0.1:18079"
      ;;
    *)
      log "unknown FRONTEND_PROFILE=${FRONTEND_PROFILE}, fallback to local-dev"
      FRONTEND_PROFILE="local-dev"
      PROFILE_DB="${DB_NAME:-sc_dev_demo}"
      PROFILE_PROXY_TARGET="http://127.0.0.1:${ODOO_PORT:-8070}"
      ;;
  esac

  if [[ -n "${PROXY_TARGET_DEFAULT}" ]]; then
    PROFILE_PROXY_TARGET="${PROXY_TARGET_DEFAULT}"
  fi
}

log() { printf '[%s] %s\n' "$(date +'%H:%M:%S')" "$*"; }

is_ready_url() {
  local url="$1"
  if command -v curl >/dev/null 2>&1; then
    curl -fsI --max-time 2 "${url}" >/dev/null 2>&1
    return $?
  fi
  if command -v python3 >/dev/null 2>&1; then
    python3 - "${url}" <<'PY' >/dev/null 2>&1
import sys
import urllib.request

url = sys.argv[1]
request = urllib.request.Request(url, method="GET")
with urllib.request.urlopen(request, timeout=2) as response:
    if response.status >= 400:
        raise SystemExit(1)
PY
    return $?
  fi
  node -e '
const http = require("node:http");
const https = require("node:https");
const target = process.argv[1];
const client = target.startsWith("https:") ? https : http;
const req = client.request(target, { method: "GET", timeout: 2000 }, (res) => {
  process.exit(res.statusCode && res.statusCode < 400 ? 0 : 1);
});
req.on("timeout", () => { req.destroy(new Error("timeout")); });
req.on("error", () => process.exit(1));
req.end();
' "${url}" >/dev/null 2>&1
}

kill_pid_if_alive() {
  local pid="$1"
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    for _ in $(seq 1 20); do
      if ! kill -0 "$pid" 2>/dev/null; then
        return 0
      fi
      sleep 0.2
    done
    kill -9 "$pid" 2>/dev/null || true
  fi
}

kill_existing_port_listener() {
  local port="$1"
  local pids=""
  if command -v lsof >/dev/null 2>&1; then
    pids="$(lsof -tiTCP:"${port}" -sTCP:LISTEN 2>/dev/null || true)"
  elif command -v ss >/dev/null 2>&1; then
    pids="$(ss -ltnp 2>/dev/null | awk -v target=":${port}" '$4 ~ target {print $NF}' | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' | sort -u)"
  fi
  [[ -z "$pids" ]] && return 0
  for pid in $pids; do
    local cmdline=""
    cmdline="$(ps -p "$pid" -o args= 2>/dev/null || true)"
    if [[ "$cmdline" == *"vite"* ]] || [[ "$cmdline" == *"/frontend/apps/web"* ]]; then
      log "stop existing frontend dev listener pid=${pid} port=${port}"
      kill_pid_if_alive "$pid"
    fi
  done
}

stop_tmux_session_if_exists() {
  if ! command -v tmux >/dev/null 2>&1; then
    return 0
  fi
  if tmux has-session -t "${TMUX_SESSION}" 2>/dev/null; then
    log "stop previous frontend dev tmux session=${TMUX_SESSION}"
    tmux kill-session -t "${TMUX_SESSION}" 2>/dev/null || true
  fi
}

if [[ -f "${PIDFILE}" ]]; then
  old_pid="$(cat "${PIDFILE}" 2>/dev/null || true)"
  [[ -n "${old_pid:-}" ]] && log "stop previous frontend dev pid=${old_pid}"
  kill_pid_if_alive "${old_pid:-}"
fi

stop_tmux_session_if_exists
kill_existing_port_listener "${PORT}"

resolve_profile_defaults
log "start frontend dev host=${HOST} port=${PORT} profile=${FRONTEND_PROFILE} db=${PROFILE_DB} proxy=${PROFILE_PROXY_TARGET}"
cd "${ROOT_DIR}"
rm -f "${LOGFILE}"
START_CMD="cd \"${ROOT_DIR}\" && export VITE_API_PROXY_TARGET=\"${PROFILE_PROXY_TARGET}\" VITE_ODOO_DB=\"${PROFILE_DB}\" VITE_ODOO_DB_LOCKED=\"${VITE_ODOO_DB_LOCKED:-1}\" VITE_PLATFORM_ADMIN_DB=\"${VITE_PLATFORM_ADMIN_DB:-}\" VITE_APP_ENV=\"${VITE_APP_ENV:-development}\" VITE_DEV_HOST=\"${HOST}\" VITE_DEV_PORT=\"${PORT}\" VITE_HMR_HOST=\"${VITE_HMR_HOST:-${HOST}}\" VITE_HMR_CLIENT_PORT=\"${VITE_HMR_CLIENT_PORT:-${PORT}}\" && exec \"${ROOT_DIR}/scripts/dev/pnpm_exec.sh\" -C frontend/apps/web dev > \"${LOGFILE}\" 2>&1"

new_pid=""
if command -v setsid >/dev/null 2>&1; then
  setsid bash -lc "${START_CMD}" >/dev/null 2>&1 < /dev/null &
  new_pid="$!"
else
  nohup bash -lc "${START_CMD}" >/dev/null 2>&1 &
  new_pid="$!"
fi

echo "${new_pid}" > "${PIDFILE}"

for _ in $(seq 1 60); do
  if is_ready_url "${READY_URL}"; then
    log "frontend dev ready pid=${new_pid:-unknown} url=http://${HOST}:${PORT}/"
    exit 0
  fi
  sleep 1
done

log "frontend dev did not become ready in time"
tail -n 120 "${LOGFILE}" 2>/dev/null || true
exit 1
