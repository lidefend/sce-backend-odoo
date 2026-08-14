#!/usr/bin/env bash
set -euo pipefail
: "${SC_GOVERNED_ACCEPTANCE_ENTRY:?DENY: use a governed make acceptance.* or *.acceptance.* entry; direct runtime script execution is forbidden}"

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
export ROOT_DIR
source "$ROOT_DIR/scripts/common/governed_make_entry.sh"
require_governed_make_ancestor "frontend_acceptance_runtime.sh" "$ROOT_DIR" "acceptance.runtime.preflight,acceptance.runtime.infrastructure.restore,frontend.acceptance.up,frontend.acceptance.down,frontend.acceptance.health,backend.acceptance.up,backend.acceptance.down,backend.acceptance.health,acceptance.module.upgrade,acceptance.baseline.upgrade,db.frontend.acceptance.ensure,acceptance.frontend.fixture,acceptance.frontend.release_snapshot"
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

validate_backend_runtime() {
  local container="$BACKEND_ACCEPTANCE_NAME"
  local expected_fingerprint expected_source expected_revision published_port
  docker inspect "$container" >/dev/null 2>&1 || {
    echo "[acceptance.runtime] DENY missing managed backend container: $container" >&2
    return 1
  }
  [[ "$(docker inspect "$container" --format '{{.State.Running}}')" == "true" ]] || {
    echo "[acceptance.runtime] DENY managed backend is not running: $container" >&2
    return 1
  }
  expected_source="$(readlink -f "$ROOT_DIR/addons")"
  expected_revision="$(git -C "$ROOT_DIR" rev-parse HEAD)"
  expected_fingerprint="$(ROOT_DIR="$ROOT_DIR" bash "$ROOT_DIR/scripts/dev/acceptance_source_fingerprint.sh")"
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
  require_container_env "$container" SC_SOURCE_REVISION "$expected_revision" || return 1
  require_container_env "$container" SC_SOURCE_FINGERPRINT "$expected_fingerprint" || return 1
  require_container_env "$container" ODOO_DB "$BACKEND_ACCEPTANCE_DB" || return 1
  require_container_env "$container" DB_NAME "$BACKEND_ACCEPTANCE_DB" || return 1
  require_container_env "$container" ODOO_DBFILTER "^${BACKEND_ACCEPTANCE_DB}$" || return 1
  require_container_env "$container" LIST_DB false || return 1
}

validate_frontend_runtime() {
  local pid process_env process_root process_cmd
  [[ -f "$FRONTEND_ACCEPTANCE_PIDFILE" ]] || {
    echo "[acceptance.runtime] DENY missing managed frontend pidfile" >&2
    return 1
  }
  pid="$(<"$FRONTEND_ACCEPTANCE_PIDFILE")"
  [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null || {
    echo "[acceptance.runtime] DENY managed frontend pid is not live" >&2
    return 1
  }
  [[ -r "/proc/$pid/environ" ]] || {
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
  for expected in \
    "VITE_API_PROXY_TARGET=$VITE_API_PROXY_TARGET" \
    "VITE_ODOO_DB=$FRONTEND_ACCEPTANCE_DB" \
    "VITE_ODOO_DB_LOCKED=1" \
    "VITE_APP_ENV=acceptance"; do
    grep -Fqx "$expected" <<<"$process_env" || {
      echo "[acceptance.runtime] DENY managed frontend environment identity mismatch" >&2
      return 1
    }
  done
  if [[ "$process_cmd" == *"release_static_server.mjs"* ]]; then
    for expected in \
      "STATIC_ROOT=$ROOT_DIR/frontend/apps/web/dist-release" \
      "STATIC_PORT=$FRONTEND_ACCEPTANCE_PORT" \
      "API_PROXY_TARGET=$VITE_API_PROXY_TARGET"; do
      grep -Fqx "$expected" <<<"$process_env" || {
        echo "[acceptance.runtime] DENY managed production frontend identity mismatch" >&2
        return 1
      }
    done
  elif [[ "$process_cmd" == *"frontend/apps/web"* && "$process_cmd" == *"--port $FRONTEND_ACCEPTANCE_PORT"* ]]; then
    :
  else
    echo "[acceptance.runtime] DENY managed frontend command identity mismatch" >&2
    return 1
  fi
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
    if docker inspect "$BACKEND_ACCEPTANCE_NAME" >/dev/null 2>&1 && ! validate_backend_runtime; then
      echo "[backend.acceptance.up] replacing backend with mismatched managed identity" >&2
      docker rm -f "$BACKEND_ACCEPTANCE_NAME" >/dev/null
    fi
    SC_GOVERNED_ACCEPTANCE_LOWER_ENTRY=1 bash "$ROOT_DIR/scripts/dev/backend_acceptance_up.sh"
    validate_backend_runtime
    ;;
  backend-down)
    preflight
    if docker inspect "$BACKEND_ACCEPTANCE_NAME" >/dev/null 2>&1; then
      validate_backend_runtime
    fi
    SC_GOVERNED_ACCEPTANCE_LOWER_ENTRY=1 bash "$ROOT_DIR/scripts/dev/backend_acceptance_down.sh"
    ;;
  backend-health)
    preflight
    validate_backend_runtime
    curl -fsS "http://127.0.0.1:${BACKEND_ACCEPTANCE_PORT}/web/login" >/dev/null
    echo "[backend.acceptance.health] PASS db=$BACKEND_ACCEPTANCE_DB url=http://127.0.0.1:$BACKEND_ACCEPTANCE_PORT"
    ;;
  frontend-up)
    preflight
    frontend_pid=""
    [[ -f "$FRONTEND_ACCEPTANCE_PIDFILE" ]] && frontend_pid="$(<"$FRONTEND_ACCEPTANCE_PIDFILE")"
    if [[ "$frontend_pid" =~ ^[0-9]+$ ]] && kill -0 "$frontend_pid" 2>/dev/null; then
      validate_frontend_runtime
      if curl -fsS "http://127.0.0.1:${FRONTEND_ACCEPTANCE_PORT}/login" >/dev/null 2>&1; then
        echo "[frontend.acceptance.up] REUSED governed pid=$frontend_pid port=$FRONTEND_ACCEPTANCE_PORT db=$FRONTEND_ACCEPTANCE_DB"
      else
        echo "[frontend.acceptance.up] DENY governed pid is live but unhealthy; run make frontend.acceptance.down before restart" >&2
        exit 2
      fi
    else
      SC_GOVERNED_ACCEPTANCE_LOWER_ENTRY=1 bash "$ROOT_DIR/scripts/dev/frontend_acceptance_up.sh"
      validate_frontend_runtime
    fi
    ;;
  frontend-down)
    preflight
    if [[ -f "$FRONTEND_ACCEPTANCE_PIDFILE" ]]; then
      frontend_pid="$(<"$FRONTEND_ACCEPTANCE_PIDFILE")"
      if [[ "$frontend_pid" =~ ^[0-9]+$ ]] && kill -0 "$frontend_pid" 2>/dev/null; then
        validate_frontend_runtime
      fi
    fi
    SC_GOVERNED_ACCEPTANCE_LOWER_ENTRY=1 bash "$ROOT_DIR/scripts/dev/frontend_acceptance_down.sh"
    ;;
  frontend-health)
    preflight
    validate_frontend_runtime
    curl -fsS "http://127.0.0.1:${FRONTEND_ACCEPTANCE_PORT}/login" >/dev/null
    echo "[frontend.acceptance.health] PASS url=http://127.0.0.1:$FRONTEND_ACCEPTANCE_PORT db=$FRONTEND_ACCEPTANCE_DB"
    ;;
  fixture)
    preflight
    SC_GOVERNED_FRONTEND_FIXTURE_LOWER_ENTRY=1 bash "$ROOT_DIR/scripts/test/frontend_productization_fixture.sh"
    ;;
  db-ensure)
    preflight
    # shellcheck source=../common/compose.sh
    source "$ROOT_DIR/scripts/common/compose.sh"
    compose_dev up -d --wait db redis odoo
    SC_GOVERNED_FRONTEND_DB_ENSURE_LOWER_ENTRY=1 bash "$ROOT_DIR/scripts/test/frontend_acceptance_db_ensure.sh"
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
    SC_GOVERNED_MODULE_LIFECYCLE_ENTRY=1 bash "$ROOT_DIR/scripts/mod/upgrade.sh"
    ;;
  baseline-upgrade)
    preflight
    SC_GOVERNED_MODULE_LIFECYCLE_ENTRY=1 MODULE=smart_core bash "$ROOT_DIR/scripts/mod/upgrade.sh"
    SC_GOVERNED_MODULE_LIFECYCLE_ENTRY=1 MODULE=smart_construction_core bash "$ROOT_DIR/scripts/mod/upgrade.sh"
    ;;
  release-snapshot)
    preflight
    bash "$ROOT_DIR/scripts/ops/odoo_shell_exec.sh" < "$ROOT_DIR/scripts/test/frontend_acceptance_release_snapshot.py"
    ;;
  *)
    echo "[acceptance.runtime] DENY unknown command: $command" >&2
    exit 2
    ;;
esac
