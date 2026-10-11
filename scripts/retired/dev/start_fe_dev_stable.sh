#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT_DIR}/.env.dev}"
REAL_HOME="${SNAP_REAL_HOME:-$HOME}"

export ENV="${ENV:-dev}"
export FRONTEND_PROFILE="${FRONTEND_PROFILE:-local-dev}"
export VITE_DEV_HOST="${VITE_DEV_HOST:-127.0.0.1}"
export VITE_DEV_PORT="${VITE_DEV_PORT:-5174}"
export FRONTEND_DEV_PIDFILE="${FRONTEND_DEV_PIDFILE:-/tmp/sc-frontend-dev.pid}"
export FRONTEND_DEV_LOGFILE="${FRONTEND_DEV_LOGFILE:-/tmp/sc-frontend-dev.log}"
export NVM_DIR="${NVM_DIR:-${REAL_HOME}/.nvm}"
export ENV_FILE

exec "${ROOT_DIR}/scripts/dev/frontend_dev_reset.sh"
