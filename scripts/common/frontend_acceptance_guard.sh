#!/usr/bin/env bash
set -euo pipefail

resolve_frontend_acceptance_db_name() {
  local root="${ROOT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
  local resolver="$root/scripts/dev/frontend_acceptance_runtime_profile.py"
  python3 "$resolver" --profile "${SC_ACCEPTANCE_RUNTIME_PROFILE:-local}" --get DB_NAME \
    2>/dev/null || echo "sc_frontend_acceptance"
}

FRONTEND_ACCEPTANCE_DB_NAME="$(resolve_frontend_acceptance_db_name)"

guard_frontend_acceptance_scope() {
  if [[ "${DB_NAME:-}" != "$FRONTEND_ACCEPTANCE_DB_NAME" ]]; then
    echo "[DENY] frontend acceptance fixture requires DB_NAME=${FRONTEND_ACCEPTANCE_DB_NAME} (got ${DB_NAME:-<empty>})" >&2
    return 20
  fi
  if [[ "${SC_ENVIRONMENT:-}" != "acceptance" ]]; then
    echo "[DENY] frontend acceptance fixture requires SC_ENVIRONMENT=acceptance" >&2
    return 21
  fi
  if [[ "${SC_ALLOW_DEMO_DATA:-}" != "1" ]]; then
    echo "[DENY] frontend acceptance fixture requires SC_ALLOW_DEMO_DATA=1" >&2
    return 22
  fi
}

acquire_frontend_acceptance_lock() {
  local operation="${1:?operation required}"
  local lock_dir="${ROOT_DIR:-$(pwd)}/.runtime/frontend-acceptance"
  mkdir -p "$lock_dir"
  local lock_file="$lock_dir/${FRONTEND_ACCEPTANCE_DB_NAME}-${operation}.lock"
  exec 9>"$lock_file"
  if ! flock -n 9; then
    echo "[DENY] frontend acceptance ${operation} already running for database=${FRONTEND_ACCEPTANCE_DB_NAME}" >&2
    return 23
  fi
}
