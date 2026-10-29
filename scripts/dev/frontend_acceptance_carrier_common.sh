#!/usr/bin/env bash
# Shared identity declaration and guards for the managed local acceptance
# carrier lifecycle entries (discard / provision).
#
# This file is sourced, never executed. The authoritative identity for each
# managed profile comes from scripts/dev/frontend_acceptance_runtime_profile.py
# (config/frontend/acceptance_environments_v1.json), so the lifecycle entries
# cannot drift from the declared profile contract.

readonly CARRIER_LOG_PREFIX="[acceptance.carrier]"

carrier_deny() {
  echo "$CARRIER_LOG_PREFIX DENY $*" >&2
  exit 2
}

carrier_fail() {
  echo "$CARRIER_LOG_PREFIX FAIL $*" >&2
  exit 1
}

carrier_resolve_profile_identity() {
  local resolver="$ROOT_DIR/scripts/dev/frontend_acceptance_runtime_profile.py"
  [[ -f "$resolver" ]] || carrier_deny "missing profile resolver"

  local profile="${SC_ACCEPTANCE_RUNTIME_PROFILE:-local}"
  case "$profile" in
    local|candidate) ;;
    *) carrier_deny "unsupported managed carrier profile: $profile" ;;
  esac

  local base_env
  base_env="$(python3 "$resolver" --profile "$profile" --get SC_ACCEPTANCE_BASE_ENV_FILE)"
  [[ -f "$base_env" ]] || carrier_deny "missing profile env file: $base_env"

  set -a
  # shellcheck disable=SC1090
  source "$base_env"
  set +a
  while IFS='=' read -r key value; do
    printf -v "$key" '%s' "$value"
    export "$key"
  done < <(python3 "$resolver" --profile "$profile")
}

carrier_require_exact_identity() {
  local resolver="$ROOT_DIR/scripts/dev/frontend_acceptance_runtime_profile.py"
  local profile="${SC_ACCEPTANCE_RUNTIME_PROFILE:-local}"
  local expected
  expected="$(python3 "$resolver" --profile "$profile" --get COMPOSE_PROJECT_NAME)"
  [[ "${COMPOSE_PROJECT_NAME:-}" == "$expected" ]] || carrier_deny "compose project mismatch: ${COMPOSE_PROJECT_NAME:-<empty>}"
  expected="$(python3 "$resolver" --profile "$profile" --get DB_NAME)"
  [[ "${DB_NAME:-}" == "$expected" ]] || carrier_deny "database mismatch: ${DB_NAME:-<empty>}"
  expected="$(python3 "$resolver" --profile "$profile" --get ODOO_DBFILTER)"
  [[ "${ODOO_DBFILTER:-}" == "$expected" ]] || carrier_deny "dbfilter mismatch: ${ODOO_DBFILTER:-<empty>}"
  expected="$(python3 "$resolver" --profile "$profile" --get DB_DATA)"
  [[ "${DB_DATA:-}" == "$expected" ]] || carrier_deny "database volume mismatch: ${DB_DATA:-<empty>}"
  expected="$(python3 "$resolver" --profile "$profile" --get REDIS_DATA)"
  [[ "${REDIS_DATA:-}" == "$expected" ]] || carrier_deny "session volume mismatch: ${REDIS_DATA:-<empty>}"
  expected="$(python3 "$resolver" --profile "$profile" --get ODOO_DATA)"
  [[ "${ODOO_DATA:-}" == "$expected" ]] || carrier_deny "filestore volume mismatch: ${ODOO_DATA:-<empty>}"
  [[ "${SC_ENVIRONMENT:-}" == "acceptance" ]] || carrier_deny "SC_ENVIRONMENT must be acceptance"
  [[ "${SC_ALLOW_DEMO_DATA:-}" == "1" ]] || carrier_deny "SC_ALLOW_DEMO_DATA must be 1"
}

carrier_source_compose() {
  # shellcheck source=../common/compose.sh
  source "$ROOT_DIR/scripts/common/compose.sh"
}

carrier_require_confirmation() {
  local variable="$1" phrase="$2" actual="${!1:-}"
  [[ "$actual" == "$phrase" ]] || {
    echo "$CARRIER_LOG_PREFIX confirmation required: $variable=$phrase" >&2
    return 2
  }
}

carrier_carriers_stopped() {
  local pidfile="${FRONTEND_ACCEPTANCE_PIDFILE:-/tmp/sc-frontend-acceptance.pid}"
  local port="${FRONTEND_ACCEPTANCE_PORT:-5175}"
  [[ ! -e "$pidfile" && ! -L "$pidfile" ]] || carrier_deny "frontend carrier pidfile present; run make frontend.acceptance.down first"
  if (exec 3<>"/dev/tcp/127.0.0.1/${port}") >/dev/null 2>&1; then
    carrier_deny "frontend carrier port $port is serving; run make frontend.acceptance.down first"
  fi
  docker inspect "${BACKEND_ACCEPTANCE_NAME:-sc-backend-odoo-acceptance}" >/dev/null 2>&1 && {
    carrier_deny "managed backend container present; run make backend.acceptance.down first"
  }
  return 0
}

carrier_all_volumes_present() {
  local volume
  for volume in "$DB_DATA" "$REDIS_DATA" "$ODOO_DATA"; do
    docker volume inspect "$volume" >/dev/null 2>&1 || return 1
  done
  return 0
}

carrier_all_containers_present() {
  local service
  for service in db redis odoo; do
    docker inspect "${COMPOSE_PROJECT_NAME}-${service}-1" >/dev/null 2>&1 || return 1
  done
  return 0
}
