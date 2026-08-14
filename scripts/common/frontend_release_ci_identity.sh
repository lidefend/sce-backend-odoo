#!/usr/bin/env bash

_frontend_release_ci_require_owned_regular_0600() {
  local path="${1:?path required}"
  [[ -f "$path" && ! -L "$path" ]] || {
    echo "DENY: frontend release identity input must be a regular non-symlink file: $path" >&2; return 2;
  }
  [[ "$(stat -c '%u' "$path")" == "$(id -u)" && "$(stat -c '%a' "$path")" == "600" ]] || {
    echo "DENY: frontend release identity input owner or mode mismatch: $path" >&2; return 2;
  }
}

_frontend_release_ci_expected_project() {
  printf 'sc-fe-release-%s-%s' "${GITHUB_RUN_ID:?}" "${GITHUB_RUN_ATTEMPT:?}"
}

validate_frontend_release_ci_identity() {
  local root="${1:?repository root required}"
  local expected_project resolved_env resolved_temp expected_env expected_head line key value route_variable
  local safe_line_re='^[A-Z][A-Z0-9_]*=[A-Za-z0-9_./:^-]+$'
  local -A allowed_keys seen_keys file_values
  for key in ENV ENV_FILE COMPOSE_PROJECT_NAME DB_USER DB_PASSWORD DB_NAME ADMIN_PASSWD \
    JWT_SECRET SC_BOOTSTRAP_SECRET SC_BOOTSTRAP_LOGIN SCENE_CHANNEL SCENE_USE_PINNED \
    SCENE_ROLLBACK ODOO_DBFILTER ODOO_PORT SC_SOURCE_REVISION DB_DATA REDIS_DATA ODOO_DATA \
    SC_ENVIRONMENT SC_ALLOW_DEMO_DATA; do
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
  [[ "${GITHUB_RUN_ID:-}" =~ ^[0-9]+$ && "${GITHUB_RUN_ATTEMPT:-}" =~ ^[1-9][0-9]*$ ]] || {
    echo "DENY: missing GitHub run or attempt identity" >&2; return 2;
  }
  expected_project="$(_frontend_release_ci_expected_project)"
  [[ "${CI_PROJECT_NAME:-}" == "$expected_project" && "${COMPOSE_PROJECT_NAME:-}" == "$expected_project" ]] || {
    echo "DENY: isolated frontend release project identity mismatch" >&2; return 2;
  }
  [[ "${ENV:-}" == "test" && -n "${ENV_FILE:-}" && -n "${RUNNER_TEMP:-}" ]] || {
    echo "DENY: isolated frontend release env file is missing" >&2; return 2;
  }
  resolved_temp="$(readlink -f "$RUNNER_TEMP")"
  [[ -d "$resolved_temp" && "$resolved_temp" != "/" && "$resolved_temp" != "${HOME:-}" ]] || {
    echo "DENY: isolated frontend release runner temp identity mismatch" >&2; return 2;
  }
  expected_env="$resolved_temp/sce-ci-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}-frontend-release.env"
  resolved_env="$(readlink -f "$ENV_FILE")"
  [[ "$resolved_env" == "$expected_env" && "$ENV_FILE" == "$expected_env" ]] || {
    echo "DENY: isolated frontend release env file path mismatch" >&2; return 2;
  }
  _frontend_release_ci_require_owned_regular_0600 "$resolved_env" || return 2
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
  for route_variable in SC_CUSTOMER_ADDONS_ROOT COMPOSE_FILE COMPOSE_FILES COMPOSE_FILE_BASE \
    COMPOSE_TEST_FILES COMPOSE_CI_FILES CI_FILES COMPOSE_PROFILES COMPOSE_ENV_FILES DOCKER_HOST DOCKER_CONTEXT; do
    [[ -z "${!route_variable:-}" ]] || {
      echo "DENY: isolated frontend release route override: $route_variable" >&2; return 2;
    }
  done
  [[ -z "${PROJECT:-}" || "${PROJECT}" == "$expected_project" ]] || {
    echo "DENY: isolated frontend release project alias mismatch" >&2; return 2;
  }
  expected_head="$(git -C "$root" rev-parse HEAD)"
  [[ "${CHECKOUT_SHA:-}" == "$expected_head" && "${SC_SOURCE_REVISION:-}" == "$expected_head" ]] || {
    echo "DENY: isolated frontend release checkout identity mismatch" >&2; return 2;
  }
  [[ "${DB_NAME:-}" == "sc_frontend_acceptance" \
    && "${ODOO_DBFILTER:-}" == '^sc_frontend_acceptance$' \
    && "${ODOO_PORT:-}" == "18082" \
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

freeze_frontend_release_ci_identity() {
  local root="${1:?repository root required}" identity expected_identity temporary
  validate_frontend_release_ci_identity "$root" || return 2
  expected_identity="$(readlink -f "$RUNNER_TEMP")/sce-ci-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}-frontend-release.identity"
  identity="${SC_FRONTEND_RELEASE_IDENTITY_FILE:-}"
  [[ "$identity" == "$expected_identity" && ! -e "$identity" && ! -L "$identity" ]] || {
    echo "DENY: isolated frontend release frozen identity path is invalid or already exists" >&2; return 2;
  }
  temporary="${identity}.tmp.$$"
  umask 077
  {
    printf 'SCHEMA=frontend_release_ci_identity_v1\n'
    printf 'GITHUB_RUN_ID=%s\n' "$GITHUB_RUN_ID"
    printf 'GITHUB_RUN_ATTEMPT=%s\n' "$GITHUB_RUN_ATTEMPT"
    printf 'COMPOSE_PROJECT_NAME=%s\n' "$COMPOSE_PROJECT_NAME"
    printf 'CHECKOUT_SHA=%s\n' "$CHECKOUT_SHA"
    printf 'GITHUB_WORKSPACE=%s\n' "$(readlink -f "$root")"
    printf 'ENV_FILE=%s\n' "$ENV_FILE"
    printf 'ENV_SHA256=%s\n' "$(sha256sum "$ENV_FILE" | awk '{print $1}')"
    printf 'DB_NAME=%s\n' "$DB_NAME"
    printf 'ODOO_DBFILTER=%s\n' "$ODOO_DBFILTER"
    printf 'DB_DATA=%s\n' "$DB_DATA"
    printf 'REDIS_DATA=%s\n' "$REDIS_DATA"
    printf 'ODOO_DATA=%s\n' "$ODOO_DATA"
  } > "$temporary"
  chmod 600 "$temporary"
  mv "$temporary" "$identity"
  _frontend_release_ci_require_owned_regular_0600 "$identity" || return 2
  echo "[frontend_release_ci_identity] FROZEN project=$COMPOSE_PROJECT_NAME sha=$CHECKOUT_SHA"
}

verify_frozen_frontend_release_ci_identity() {
  local root="${1:?repository root required}" identity expected_identity line key value
  local -A expected seen actual
  validate_frontend_release_ci_identity "$root" || return 2
  expected_identity="$(readlink -f "$RUNNER_TEMP")/sce-ci-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}-frontend-release.identity"
  identity="${SC_FRONTEND_RELEASE_IDENTITY_FILE:-}"
  [[ "$identity" == "$expected_identity" ]] || {
    echo "DENY: isolated frontend release frozen identity path mismatch" >&2; return 2;
  }
  _frontend_release_ci_require_owned_regular_0600 "$identity" || return 2
  for key in SCHEMA GITHUB_RUN_ID GITHUB_RUN_ATTEMPT COMPOSE_PROJECT_NAME CHECKOUT_SHA \
    GITHUB_WORKSPACE ENV_FILE ENV_SHA256 DB_NAME ODOO_DBFILTER DB_DATA REDIS_DATA ODOO_DATA; do
    expected["$key"]=1
  done
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[A-Z][A-Z0-9_]*=[A-Za-z0-9_./:^-]+$ || "$line" == 'ODOO_DBFILTER=^sc_frontend_acceptance$' ]] || {
      echo "DENY: frozen frontend release identity contains unsafe content" >&2; return 2;
    }
    key="${line%%=*}"
    value="${line#*=}"
    [[ -n "${expected[$key]:-}" && -z "${seen[$key]:-}" ]] || {
      echo "DENY: frozen frontend release identity contains unknown or duplicate keys" >&2; return 2;
    }
    seen["$key"]=1
    actual["$key"]="$value"
  done < "$identity"
  for key in "${!expected[@]}"; do
    [[ -n "${seen[$key]:-}" ]] || { echo "DENY: frozen identity missing key=$key" >&2; return 2; }
  done
  [[ "${actual[SCHEMA]}" == "frontend_release_ci_identity_v1" \
    && "${actual[GITHUB_RUN_ID]}" == "$GITHUB_RUN_ID" \
    && "${actual[GITHUB_RUN_ATTEMPT]}" == "$GITHUB_RUN_ATTEMPT" \
    && "${actual[COMPOSE_PROJECT_NAME]}" == "$COMPOSE_PROJECT_NAME" \
    && "${actual[CHECKOUT_SHA]}" == "$CHECKOUT_SHA" \
    && "${actual[GITHUB_WORKSPACE]}" == "$(readlink -f "$root")" \
    && "${actual[ENV_FILE]}" == "$ENV_FILE" \
    && "${actual[ENV_SHA256]}" == "$(sha256sum "$ENV_FILE" | awk '{print $1}')" \
    && "${actual[DB_NAME]}" == "$DB_NAME" \
    && "${actual[ODOO_DBFILTER]}" == "$ODOO_DBFILTER" \
    && "${actual[DB_DATA]}" == "$DB_DATA" \
    && "${actual[REDIS_DATA]}" == "$REDIS_DATA" \
    && "${actual[ODOO_DATA]}" == "$ODOO_DATA" ]] || {
    echo "DENY: current frontend release identity differs from frozen identity" >&2; return 2;
  }
}

validate_frozen_frontend_release_ci_resources() {
  local root="${1:?repository root required}" mode="${2:-optional}"
  local volume logical container service container_env mounted expected count network expected_env source_mount
  local -A seen_services
  verify_frozen_frontend_release_ci_identity "$root" || return 2
  command -v docker >/dev/null 2>&1 || {
    [[ "$mode" == "optional" ]] && return 0
    echo "DENY: Docker is required for frozen frontend release resources" >&2; return 2;
  }
  for volume in "$DB_DATA" "$REDIS_DATA" "$ODOO_DATA"; do
    if docker volume inspect "$volume" >/dev/null 2>&1; then
      [[ "$(docker volume inspect "$volume" --format '{{index .Labels "com.docker.compose.project"}}')" == "$COMPOSE_PROJECT_NAME" ]] || {
        echo "DENY: frontend release volume belongs to another project: $volume" >&2; return 2;
      }
      case "$volume" in
        "$DB_DATA") logical=db_data ;;
        "$REDIS_DATA") logical=redis_data ;;
        "$ODOO_DATA") logical=odoo_data ;;
      esac
      [[ "$(docker volume inspect "$volume" --format '{{index .Labels "com.docker.compose.volume"}}')" == "$logical" ]] || {
        echo "DENY: frontend release volume logical identity mismatch: $volume" >&2; return 2;
      }
    elif [[ "$mode" == "required" ]]; then
      echo "DENY: required frontend release volume is absent: $volume" >&2; return 2
    fi
  done
  while IFS= read -r volume; do
    [[ -z "$volume" || "$volume" == "$DB_DATA" || "$volume" == "$REDIS_DATA" || "$volume" == "$ODOO_DATA" ]] || {
      echo "DENY: unexpected volume in frontend release project: $volume" >&2; return 2;
    }
  done < <(docker volume ls -q --filter "label=com.docker.compose.project=${COMPOSE_PROJECT_NAME}")
  while IFS= read -r network; do
    [[ -z "$network" || "$network" == "${COMPOSE_PROJECT_NAME}_default" ]] || {
      echo "DENY: unexpected network in frontend release project: $network" >&2; return 2;
    }
  done < <(docker network ls --format '{{.Name}}' --filter "label=com.docker.compose.project=${COMPOSE_PROJECT_NAME}")
  count=0
  while IFS= read -r container; do
    [[ -n "$container" ]] || continue
    count=$((count + 1))
    service="$(docker inspect "$container" --format '{{index .Config.Labels "com.docker.compose.service"}}')"
    [[ -z "${seen_services[$service]:-}" ]] || {
      echo "DENY: duplicate service in frontend release project: $service" >&2; return 2;
    }
    seen_services["$service"]=1
    container_env="$(docker inspect "$container" --format '{{range .Config.Env}}{{println .}}{{end}}')"
    case "$service" in
      db)
        grep -Fxq "POSTGRES_DB=$DB_NAME" <<< "$container_env" || {
          echo "DENY: frontend release database container identity mismatch" >&2; return 2;
        }
        mounted="$(docker inspect "$container" --format '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}{{end}}{{end}}')"
        expected="$DB_DATA"
        ;;
      redis)
        mounted="$(docker inspect "$container" --format '{{range .Mounts}}{{if eq .Destination "/data"}}{{.Name}}{{end}}{{end}}')"
        expected="$REDIS_DATA"
        ;;
      odoo)
        for expected_env in "DB_NAME=$DB_NAME" "ODOO_DB=$DB_NAME" "ODOO_DBFILTER=$ODOO_DBFILTER" "SC_SOURCE_REVISION=$CHECKOUT_SHA"; do
          grep -Fxq "$expected_env" <<< "$container_env" || {
            echo "DENY: frontend release Odoo container identity mismatch" >&2; return 2;
          }
        done
        mounted="$(docker inspect "$container" --format '{{range .Mounts}}{{if eq .Destination "/var/lib/odoo"}}{{.Name}}{{end}}{{end}}')"
        expected="$ODOO_DATA"
        source_mount="$(docker inspect "$container" --format '{{range .Mounts}}{{if eq .Destination "/mnt/source-addons"}}{{.Source}}{{end}}{{end}}')"
        [[ "$(readlink -f "$source_mount")" == "$(readlink -f "$root/addons")" ]] || {
          echo "DENY: frontend release Odoo source mount identity mismatch" >&2; return 2;
        }
        ;;
      *)
        echo "DENY: unexpected service in frontend release project: $service" >&2; return 2
        ;;
    esac
    [[ "$mounted" == "$expected" ]] || {
      echo "DENY: frontend release service volume identity mismatch: $service" >&2; return 2;
    }
  done < <(docker ps -aq --filter "label=com.docker.compose.project=${COMPOSE_PROJECT_NAME}")
  if [[ "$mode" == "required" && ( "$count" -ne 3 \
    || -z "${seen_services[db]:-}" || -z "${seen_services[redis]:-}" || -z "${seen_services[odoo]:-}" ) ]]; then
    echo "DENY: frontend release project must contain exactly db, redis, and odoo" >&2; return 2
  fi
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  command="${1:-}"
  root="${2:-}"
  case "$command" in
    freeze) freeze_frontend_release_ci_identity "$root" ;;
    verify) verify_frozen_frontend_release_ci_identity "$root" ;;
    resources) validate_frozen_frontend_release_ci_resources "$root" "${3:-optional}" ;;
    *) echo "usage: $0 freeze|verify|resources <repository-root> [optional|required]" >&2; exit 2 ;;
  esac
fi
