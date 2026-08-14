#!/usr/bin/env bash

validate_frontend_release_ci_identity() {
  local root="${1:?repository root required}"
  local expected_project resolved_env resolved_temp expected_head line key value route_variable
  local safe_line_re='^[A-Z][A-Z0-9_]*=[A-Za-z0-9_./:^-]+$'
  local -A allowed_keys seen_keys file_values
  for key in ENV ENV_FILE COMPOSE_PROJECT_NAME DB_USER DB_PASSWORD DB_NAME ADMIN_PASSWD \
    JWT_SECRET SC_BOOTSTRAP_SECRET SC_BOOTSTRAP_LOGIN SCENE_CHANNEL SCENE_USE_PINNED \
    SCENE_ROLLBACK ODOO_DBFILTER DB_DATA REDIS_DATA ODOO_DATA SC_ENVIRONMENT \
    SC_ALLOW_DEMO_DATA; do
    allowed_keys["$key"]=1
  done
  [[ "${GITHUB_ACTIONS:-}" == "true" && "${CI:-}" == "true" ]] || {
    echo "DENY: isolated frontend release route requires GitHub Actions" >&2; return 2;
  }
  [[ "${GITHUB_REPOSITORY:-}" == "lidefend/sce-backend-odoo" ]] || {
    echo "DENY: unexpected GitHub repository identity" >&2; return 2;
  }
  [[ "$(readlink -f "${GITHUB_WORKSPACE:-/nonexistent}")" == "$(readlink -f "$root")" ]] || {
    echo "DENY: GitHub workspace differs from the checked-out repository" >&2; return 2;
  }
  [[ "${GITHUB_RUN_ID:-}" =~ ^[0-9]+$ ]] || {
    echo "DENY: missing GitHub run identity" >&2; return 2;
  }
  expected_project="sc-fe-release-${GITHUB_RUN_ID}"
  [[ "${CI_PROJECT_NAME:-}" == "$expected_project" && "${COMPOSE_PROJECT_NAME:-}" == "$expected_project" ]] || {
    echo "DENY: isolated frontend release project identity mismatch" >&2; return 2;
  }
  [[ "${ENV:-}" == "test" && -n "${ENV_FILE:-}" && -f "$ENV_FILE" && -n "${RUNNER_TEMP:-}" ]] || {
    echo "DENY: isolated frontend release env file is missing" >&2; return 2;
  }
  resolved_env="$(readlink -f "$ENV_FILE")"
  resolved_temp="$(readlink -f "$RUNNER_TEMP")"
  [[ "$resolved_env" == "$resolved_temp"/* ]] || {
    echo "DENY: isolated frontend release env file is outside RUNNER_TEMP" >&2; return 2;
  }
  [[ "$(stat -c '%a' "$resolved_env")" == "600" ]] || {
    echo "DENY: isolated frontend release env file permissions must be 600" >&2; return 2;
  }
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ $safe_line_re || "$line" == 'ODOO_DBFILTER=^sc_frontend_acceptance$' ]] || {
      echo "DENY: isolated frontend release env file contains shell syntax" >&2; return 2;
    }
    key="${line%%=*}"
    value="${line#*=}"
    [[ -n "${allowed_keys[$key]:-}" && -z "${seen_keys[$key]:-}" ]] || {
      echo "DENY: isolated frontend release env file contains unknown or duplicate keys" >&2; return 2;
    }
    seen_keys["$key"]=1
    file_values["$key"]="$value"
  done < "$resolved_env"
  for key in "${!allowed_keys[@]}"; do
    [[ -n "${seen_keys[$key]:-}" && "${file_values[$key]}" == "${!key-}" ]] || {
      echo "DENY: isolated frontend release env file differs from workflow environment key=$key" >&2; return 2;
    }
  done
  for key in DB_PASSWORD ADMIN_PASSWD JWT_SECRET SC_BOOTSTRAP_SECRET; do
    [[ "${file_values[$key]}" =~ ^[0-9a-f]{64}$ ]] || {
      echo "DENY: isolated frontend release secret format mismatch key=$key" >&2; return 2;
    }
  done
  [[ "${file_values[DB_USER]}" == "odoo" \
    && "${file_values[SC_BOOTSTRAP_LOGIN]}" == "frontend_release_ci" \
    && "${file_values[SCENE_CHANNEL]}" == "stable" \
    && "${file_values[SCENE_USE_PINNED]}" == "0" \
    && "${file_values[SCENE_ROLLBACK]}" == "0" ]] || {
    echo "DENY: isolated frontend release fixed workflow value mismatch" >&2; return 2;
  }
  [[ "${COMPOSE_BIN:-docker compose}" == "docker compose" ]] || {
    echo "DENY: isolated frontend release compose command override" >&2; return 2;
  }
  for route_variable in SC_CUSTOMER_ADDONS_ROOT COMPOSE_FILE COMPOSE_PROFILES \
    COMPOSE_ENV_FILES DOCKER_HOST DOCKER_CONTEXT; do
    [[ -z "${!route_variable:-}" ]] || {
      echo "DENY: isolated frontend release route override: $route_variable" >&2; return 2;
    }
  done
  [[ -z "${PROJECT:-}" || "${PROJECT}" == "$expected_project" ]] || {
    echo "DENY: isolated frontend release project alias mismatch" >&2; return 2;
  }
  expected_head="$(git -C "$root" rev-parse HEAD)"
  [[ "${CHECKOUT_SHA:-}" == "$expected_head" ]] || {
    echo "DENY: isolated frontend release checkout identity mismatch" >&2; return 2;
  }
  [[ "${DB_NAME:-}" == "sc_frontend_acceptance" \
    && "${ODOO_DBFILTER:-}" == '^sc_frontend_acceptance$' \
    && "${SC_ENVIRONMENT:-}" == "acceptance" \
    && "${SC_ALLOW_DEMO_DATA:-}" == "1" ]] || {
    echo "DENY: isolated frontend release database identity mismatch" >&2; return 2;
  }
  [[ "${DB_DATA:-}" == "${expected_project}-db-data" \
    && "${REDIS_DATA:-}" == "${expected_project}-redis-data" \
    && "${ODOO_DATA:-}" == "${expected_project}-odoo-data" ]] || {
    echo "DENY: isolated frontend release volume identity mismatch" >&2; return 2;
  }
}
