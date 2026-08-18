#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
export ROOT_DIR
[[ "${SC_FRONTEND_ACCEPTANCE_RUNTIME_ENTRY:-}" == "operation_entry_v1" ]] || {
  echo "[acceptance.runtime] DENY use a governed frontend acceptance Make target" >&2
  exit 2
}
PROFILE="${SC_ACCEPTANCE_RUNTIME_PROFILE:-local}"
PROFILE_RESOLVER="$ROOT_DIR/scripts/dev/frontend_acceptance_runtime_profile.py"

container_env_value() {
  local container="$1"
  local key="$2"
  docker inspect "$container" --format '{{range .Config.Env}}{{println .}}{{end}}' \
    | awk -F= -v expected="$key" '$1 == expected {sub(/^[^=]*=/, ""); print; exit}'
}

load_profile() {
  local base_env
  base_env="$(python3 "$PROFILE_RESOLVER" --profile "$PROFILE" --get SC_ACCEPTANCE_BASE_ENV_FILE)"
  if [[ ! -f "$base_env" ]]; then
    echo "[acceptance.runtime] DENY missing primary-worktree credential env: $base_env" >&2
    exit 2
  fi
  set -a
  # shellcheck disable=SC1090
  source "$base_env"
  set +a
  while IFS='=' read -r key value; do
    printf -v "$key" '%s' "$value"
    export "$key"
  done < <(python3 "$PROFILE_RESOLVER" --profile "$PROFILE")
  docker inspect "$SC_ACCEPTANCE_CREDENTIAL_CONTAINER" >/dev/null 2>&1 || {
    echo "[acceptance.runtime] DENY missing credential authority container: $SC_ACCEPTANCE_CREDENTIAL_CONTAINER" >&2
    exit 2
  }
  DB_USER="$(container_env_value "$SC_ACCEPTANCE_CREDENTIAL_CONTAINER" DB_USER)"
  DB_PASSWORD="$(container_env_value "$SC_ACCEPTANCE_CREDENTIAL_CONTAINER" DB_PASSWORD)"
  [[ -n "$DB_USER" && -n "$DB_PASSWORD" ]] || {
    echo "[acceptance.runtime] DENY credential authority is incomplete" >&2
    exit 2
  }
  export DB_USER DB_PASSWORD
  ENV=dev
  ENV_FILE="$base_env"
  LIST_DB=false
  export ENV ENV_FILE LIST_DB
}

volume_of() {
  docker inspect "$1" --format '{{range .Mounts}}{{if eq .Destination "'"$2"'"}}{{.Name}}{{end}}{{end}}'
}

mount_source_of() {
  docker inspect "$1" --format '{{range .Mounts}}{{if eq .Destination "'"$2"'"}}{{.Source}}{{end}}{{end}}'
}

require_container_env() {
  local container="$1"
  local key="$2"
  local expected="$3"
  [[ "$(container_env_value "$container" "$key")" == "$expected" ]] || {
    echo "[acceptance.runtime] DENY container=$container environment identity mismatch: $key" >&2
    return 1
  }
}

validate_backend_resource_identity() {
  local container="$BACKEND_ACCEPTANCE_NAME"
  local expected_product_version expected_source published_port
  docker inspect "$container" >/dev/null 2>&1 || {
    echo "[acceptance.runtime] DENY missing managed backend container: $container" >&2
    return 1
  }
  expected_source="$(readlink -f "$ROOT_DIR/addons")"
  expected_product_version="$(tr -d '[:space:]' < "$ROOT_DIR/VERSION")"
  published_port="$(docker port "$container" 8069/tcp 2>/dev/null || true)"
  [[ "$(mount_source_of "$container" /mnt/source-addons)" == "$expected_source" ]] || {
    echo "[acceptance.runtime] DENY managed backend source mount differs from current worktree" >&2
    return 1
  }
  [[ "$(volume_of "$container" /var/lib/odoo)" == "$ODOO_DATA" ]] || {
    echo "[acceptance.runtime] DENY managed backend filestore differs from profile" >&2
    return 1
  }
  [[ "$published_port" == "127.0.0.1:${BACKEND_ACCEPTANCE_PORT}" ]] || {
    echo "[acceptance.runtime] DENY managed backend port mapping differs from profile" >&2
    return 1
  }
  require_container_env "$container" SC_PRODUCT_VERSION "$expected_product_version" || return 1
  require_container_env "$container" ODOO_DB "$BACKEND_ACCEPTANCE_DB" || return 1
  require_container_env "$container" DB_NAME "$BACKEND_ACCEPTANCE_DB" || return 1
  require_container_env "$container" ODOO_DBFILTER "^${BACKEND_ACCEPTANCE_DB}$" || return 1
  require_container_env "$container" LIST_DB false || return 1
}

validate_backend_identity() {
  local container="$BACKEND_ACCEPTANCE_NAME"
  local expected_fingerprint expected_revision
  validate_backend_resource_identity || return 1
  expected_revision="$(git -C "$ROOT_DIR" rev-parse HEAD)"
  expected_fingerprint="$(ROOT_DIR="$ROOT_DIR" bash "$ROOT_DIR/scripts/dev/acceptance_source_fingerprint.sh")"
  require_container_env "$container" SC_SOURCE_REVISION "$expected_revision" || return 1
  require_container_env "$container" SC_SOURCE_FINGERPRINT "$expected_fingerprint" || return 1
}

validate_backend_runtime() {
  validate_backend_identity || return 1
  [[ "$(docker inspect "$BACKEND_ACCEPTANCE_NAME" --format '{{.State.Running}}')" == "true" ]] || {
    echo "[acceptance.runtime] DENY managed backend is not running: $BACKEND_ACCEPTANCE_NAME" >&2
    return 1
  }
}

validate_frontend_runtime() {
  local pid process_cmd process_env process_root listener listener_pid listener_group
  [[ -f "$FRONTEND_ACCEPTANCE_PIDFILE" && ! -L "$FRONTEND_ACCEPTANCE_PIDFILE" \
    && "$(stat -c %u "$FRONTEND_ACCEPTANCE_PIDFILE")" == "$(id -u)" ]] || {
    echo "[acceptance.runtime] DENY missing managed frontend pidfile" >&2
    return 1
  }
  pid="$(<"$FRONTEND_ACCEPTANCE_PIDFILE")"
  [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null || {
    echo "[acceptance.runtime] DENY managed frontend pid is not live" >&2
    return 1
  }
  [[ -r "/proc/$pid/environ" && "$(stat -c %u "/proc/$pid")" == "$(id -u)" ]] || {
    echo "[acceptance.runtime] DENY managed frontend environment is unreadable" >&2
    return 1
  }
  process_root="$(readlink -f "/proc/$pid/cwd")"
  [[ "$process_root" == "$(readlink -f "$ROOT_DIR")" ]] || {
    echo "[acceptance.runtime] DENY managed frontend belongs to another worktree" >&2
    return 1
  }
  process_env="$(tr '\0' '\n' < "/proc/$pid/environ")"
  process_cmd="$(tr '\0' ' ' < "/proc/$pid/cmdline")"
  if [[ "$process_cmd" == *"scripts/release/release_static_server.mjs"* ]]; then
    validated_frontend_mode=production
    for expected in \
      "STATIC_ROOT=$(readlink -f "$ROOT_DIR/frontend/apps/web/dist-release")" \
      "STATIC_PORT=$FRONTEND_ACCEPTANCE_PORT" \
      "API_PROXY_TARGET=$VITE_API_PROXY_TARGET"; do
      grep -Fqx "$expected" <<<"$process_env" || {
        echo "[acceptance.runtime] DENY managed production frontend environment identity mismatch" >&2
        return 1
      }
    done
  elif [[ "$process_cmd" == *"frontend/apps/web"* && "$process_cmd" == *"--port $FRONTEND_ACCEPTANCE_PORT"* ]]; then
    validated_frontend_mode=development
    for expected in \
      "VITE_API_PROXY_TARGET=$VITE_API_PROXY_TARGET" \
      "VITE_ODOO_DB=$FRONTEND_ACCEPTANCE_DB" \
      "VITE_ODOO_DB_LOCKED=1" \
      "VITE_APP_ENV=acceptance"; do
      grep -Fqx "$expected" <<<"$process_env" || {
        echo "[acceptance.runtime] DENY managed development frontend environment identity mismatch" >&2
        return 1
      }
    done
  else
    echo "[acceptance.runtime] DENY managed frontend command identity mismatch" >&2
    return 1
  fi
  listener="$(ss -H -ltnp "sport = :$FRONTEND_ACCEPTANCE_PORT" 2>/dev/null || true)"
  listener_pid="$(sed -nE 's/.*pid=([0-9]+).*/\1/p' <<<"$listener" | head -n 1)"
  [[ "$listener_pid" =~ ^[0-9]+$ && -d "/proc/$listener_pid" \
    && "$(stat -c %u "/proc/$listener_pid")" == "$(id -u)" ]] || {
    echo "[acceptance.runtime] DENY managed frontend listener identity is missing" >&2
    return 1
  }
  listener_group="$(ps -o pgid= -p "$listener_pid" | tr -d '[:space:]')"
  [[ "$listener_group" == "$pid" ]] || {
    echo "[acceptance.runtime] DENY managed frontend process group does not own port=$FRONTEND_ACCEPTANCE_PORT" >&2
    return 1
  }
}

validate_frontend_launch_contract() {
  local requested_mode="${FRONTEND_ACCEPTANCE_MODE:-development}"
  case "$requested_mode" in
    development)
      ;;
    production)
      local expected_dist requested_dist
      expected_dist="$(readlink -f "$ROOT_DIR/frontend/apps/web/dist-release")"
      requested_dist="$(readlink -f "${FRONTEND_ACCEPTANCE_STATIC_DIST:-$expected_dist}")"
      [[ "$requested_dist" == "$expected_dist" && -f "$expected_dist/index.html" ]] || {
        echo "[acceptance.runtime] DENY production frontend dist identity mismatch" >&2
        return 2
      }
      export FRONTEND_ACCEPTANCE_STATIC_DIST="$expected_dist"
      ;;
    *)
      echo "[acceptance.runtime] DENY unsupported frontend mode=$requested_mode" >&2
      return 2
      ;;
  esac
}

preflight() {
  local db_container="${COMPOSE_PROJECT_NAME}-db-1"
  local redis_container="${COMPOSE_PROJECT_NAME}-redis-1"
  [[ "$DB_NAME" == "sc_frontend_acceptance" ]] || { echo "[acceptance.runtime] DENY database=$DB_NAME" >&2; exit 2; }
  [[ "$ODOO_DBFILTER" == '^sc_frontend_acceptance$' ]] || { echo "[acceptance.runtime] DENY dbfilter=$ODOO_DBFILTER" >&2; exit 2; }
  [[ "$DB_DATA" != "$REDIS_DATA" && "$DB_DATA" != "$ODOO_DATA" && "$REDIS_DATA" != "$ODOO_DATA" ]] || {
    echo "[acceptance.runtime] DENY volume identities overlap" >&2; exit 2;
  }
  for volume in "$DB_DATA" "$REDIS_DATA" "$ODOO_DATA"; do
    docker volume inspect "$volume" >/dev/null 2>&1 || {
      echo "[acceptance.runtime] DENY required managed volume is absent: $volume" >&2; exit 2;
    }
  done
  docker inspect "$db_container" >/dev/null 2>&1 || { echo "[acceptance.runtime] DENY missing db container: $db_container" >&2; exit 2; }
  docker inspect "$redis_container" >/dev/null 2>&1 || { echo "[acceptance.runtime] DENY missing redis container: $redis_container" >&2; exit 2; }
  [[ "$(container_env_value "$db_container" POSTGRES_USER)" == "$DB_USER" ]] || {
    echo "[acceptance.runtime] DENY database credential user differs from authority" >&2; exit 2;
  }
  [[ "$(container_env_value "$db_container" POSTGRES_PASSWORD)" == "$DB_PASSWORD" ]] || {
    echo "[acceptance.runtime] DENY database credential secret differs from authority" >&2; exit 2;
  }
  [[ "$(volume_of "$db_container" /var/lib/postgresql/data)" == "$DB_DATA" ]] || {
    echo "[acceptance.runtime] DENY db container is attached to a non-profile volume" >&2; exit 2;
  }
  [[ "$(volume_of "$redis_container" /data)" == "$REDIS_DATA" ]] || {
    echo "[acceptance.runtime] DENY redis container is attached to a non-profile volume" >&2; exit 2;
  }
  [[ "$(volume_of "$SC_ACCEPTANCE_CREDENTIAL_CONTAINER" /var/lib/odoo)" == "$ODOO_DATA" ]] || {
    echo "[acceptance.runtime] DENY credential authority is attached to a non-profile filestore" >&2; exit 2;
  }
  docker exec "$db_container" psql -U "$DB_USER" -d postgres -Atc \
    "select 1 from pg_database where datname = 'sc_frontend_acceptance'" | grep -qx 1 || {
      echo "[acceptance.runtime] DENY managed database is absent" >&2; exit 2;
    }
  echo "[acceptance.runtime.preflight] PASS profile=$PROFILE project=$COMPOSE_PROJECT_NAME db=$DB_NAME dbfilter=$ODOO_DBFILTER"
  echo "[acceptance.runtime.preflight] volumes db=$DB_DATA redis=$REDIS_DATA odoo=$ODOO_DATA"
}

load_profile
command="${1:-preflight}"
case "$command" in
  preflight)
    preflight
    ;;
  backend-up)
    preflight
    if docker inspect "$BACKEND_ACCEPTANCE_NAME" >/dev/null 2>&1; then
      validate_backend_identity || {
        echo "[backend.acceptance.up] DENY existing backend identity mismatch" >&2
        exit 2
      }
    fi
    bash "$ROOT_DIR/scripts/dev/backend_acceptance_up.sh"
    validate_backend_runtime
    ;;
  backend-down)
    preflight
    if docker inspect "$BACKEND_ACCEPTANCE_NAME" >/dev/null 2>&1; then
      validate_backend_identity || {
        echo "[backend.acceptance.down] DENY existing backend identity mismatch" >&2
        exit 2
      }
      bash "$ROOT_DIR/scripts/dev/backend_acceptance_down.sh"
    else
      echo "[backend.acceptance.down] PASS already absent"
    fi
    ;;
  backend-replace-stale)
    preflight
    if docker inspect "$BACKEND_ACCEPTANCE_NAME" >/dev/null 2>&1; then
      validate_backend_resource_identity || {
        echo "[backend.acceptance.replace-stale] DENY existing backend resource identity mismatch" >&2
        exit 2
      }
      bash "$ROOT_DIR/scripts/dev/backend_acceptance_down.sh"
    fi
    bash "$ROOT_DIR/scripts/dev/backend_acceptance_up.sh"
    validate_backend_runtime
    echo "[backend.acceptance.replace-stale] PASS backend=$BACKEND_ACCEPTANCE_NAME revision=$(git -C "$ROOT_DIR" rev-parse HEAD)"
    ;;
  backend-health)
    preflight
    validate_backend_runtime
    curl -fsS "http://127.0.0.1:${BACKEND_ACCEPTANCE_PORT}/web/login" >/dev/null
    echo "[backend.acceptance.health] PASS db=$BACKEND_ACCEPTANCE_DB url=http://127.0.0.1:$BACKEND_ACCEPTANCE_PORT"
    ;;
  frontend-up)
    validate_frontend_launch_contract
    preflight
    if [[ -e "$FRONTEND_ACCEPTANCE_PIDFILE" || -L "$FRONTEND_ACCEPTANCE_PIDFILE" ]]; then
      validate_frontend_runtime || {
        echo "[frontend.acceptance.up] DENY existing frontend identity mismatch" >&2
        exit 2
      }
      [[ "$validated_frontend_mode" == "${FRONTEND_ACCEPTANCE_MODE:-development}" ]] || {
        echo "[frontend.acceptance.up] DENY existing frontend mode mismatch" >&2
        exit 2
      }
      frontend_pid="$(<"$FRONTEND_ACCEPTANCE_PIDFILE")"
      if curl -fsS "http://127.0.0.1:${FRONTEND_ACCEPTANCE_PORT}/login" >/dev/null 2>&1; then
        echo "[frontend.acceptance.up] REUSED governed pid=$frontend_pid port=$FRONTEND_ACCEPTANCE_PORT db=$FRONTEND_ACCEPTANCE_DB"
      else
        bash "$ROOT_DIR/scripts/dev/frontend_acceptance_up.sh"
        validate_frontend_runtime
      fi
    else
      bash "$ROOT_DIR/scripts/dev/frontend_acceptance_up.sh"
      validate_frontend_runtime
    fi
    ;;
  frontend-down)
    preflight
    if [[ -e "$FRONTEND_ACCEPTANCE_PIDFILE" || -L "$FRONTEND_ACCEPTANCE_PIDFILE" ]]; then
      validate_frontend_runtime || {
        echo "[frontend.acceptance.down] DENY existing frontend identity mismatch" >&2
        exit 2
      }
      bash "$ROOT_DIR/scripts/dev/frontend_acceptance_down.sh"
    else
      listener="$(ss -H -ltnp "sport = :$FRONTEND_ACCEPTANCE_PORT" 2>/dev/null || true)"
      [[ -z "$listener" ]] || {
        echo "[frontend.acceptance.down] DENY untracked listener owns port=$FRONTEND_ACCEPTANCE_PORT" >&2
        exit 2
      }
      echo "[frontend.acceptance.down] PASS already absent"
    fi
    ;;
  frontend-health)
    preflight
    validate_frontend_runtime
    curl -fsS "http://127.0.0.1:${FRONTEND_ACCEPTANCE_PORT}/login" >/dev/null
    echo "[frontend.acceptance.health] PASS url=http://127.0.0.1:$FRONTEND_ACCEPTANCE_PORT db=$FRONTEND_ACCEPTANCE_DB"
    ;;
  fixture)
    preflight
    bash "$ROOT_DIR/scripts/test/frontend_productization_fixture.sh"
    ;;
  db-ensure)
    preflight
    # shellcheck source=../common/compose.sh
    source "$ROOT_DIR/scripts/common/compose.sh"
    compose_dev up -d --wait db redis odoo
    bash "$ROOT_DIR/scripts/test/frontend_acceptance_db_ensure.sh"
    ;;
  infrastructure-restore)
    for volume in "$DB_DATA" "$REDIS_DATA" "$ODOO_DATA"; do
      docker volume inspect "$volume" >/dev/null 2>&1 || {
        echo "[acceptance.runtime] DENY required managed volume is absent: $volume" >&2; exit 2;
      }
    done
    # shellcheck source=../common/compose.sh
    source "$ROOT_DIR/scripts/common/compose.sh"
    compose_dev up -d db redis
    preflight
    ;;
  module-upgrade)
    preflight
    : "${MODULE:?MODULE is required}"
    bash "$ROOT_DIR/scripts/mod/upgrade.sh"
    ;;
  baseline-upgrade)
    preflight
    MODULE=smart_core bash "$ROOT_DIR/scripts/mod/upgrade.sh"
    MODULE=smart_construction_core bash "$ROOT_DIR/scripts/mod/upgrade.sh"
    ;;
  release-snapshot)
    preflight
    bash "$ROOT_DIR/scripts/ops/odoo_shell_exec.sh" < "$ROOT_DIR/scripts/test/frontend_acceptance_release_snapshot.py"
    ;;
  release-preflight)
    preflight
    if [[ -e "$FRONTEND_ACCEPTANCE_PIDFILE" || -L "$FRONTEND_ACCEPTANCE_PIDFILE" ]]; then
      [[ -f "$FRONTEND_ACCEPTANCE_PIDFILE" && ! -L "$FRONTEND_ACCEPTANCE_PIDFILE" ]] || {
        echo "[acceptance.release.preflight] DENY invalid frontend pidfile" >&2; exit 2;
      }
      frontend_pid="$(<"$FRONTEND_ACCEPTANCE_PIDFILE")"
      [[ "$frontend_pid" =~ ^[0-9]+$ ]] || {
        echo "[acceptance.release.preflight] DENY invalid frontend pid" >&2; exit 2;
      }
      if kill -0 "$frontend_pid" 2>/dev/null; then
        frontend_owner="$(readlink -f "/proc/$frontend_pid/cwd")"
        echo "[acceptance.release.preflight] DENY frontend lifecycle is active owner=$frontend_owner pid=$frontend_pid" >&2
        exit 2
      fi
      echo "[acceptance.release.preflight] DENY stale frontend pidfile must be closed by its owner" >&2
      exit 2
    fi
    if (exec 3<>"/dev/tcp/127.0.0.1/${FRONTEND_ACCEPTANCE_PORT}") >/dev/null 2>&1; then
      echo "[acceptance.release.preflight] DENY untracked frontend listener port=$FRONTEND_ACCEPTANCE_PORT" >&2
      exit 2
    fi
    echo "[acceptance.release.preflight] PASS frontend_port=$FRONTEND_ACCEPTANCE_PORT"
    ;;
  release-audit)
    preflight
    # shellcheck source=../common/frontend_acceptance_make_identity.sh
    source "$ROOT_DIR/scripts/common/frontend_acceptance_make_identity.sh"
    frontend_acceptance_make verify.frontend.release.audit
    ;;
  *)
    echo "[acceptance.runtime] DENY unknown command: $command" >&2
    exit 2
    ;;
esac
