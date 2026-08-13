#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
export ROOT_DIR
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
    bash "$ROOT_DIR/scripts/dev/backend_acceptance_up.sh"
    ;;
  backend-down)
    bash "$ROOT_DIR/scripts/dev/backend_acceptance_down.sh"
    ;;
  backend-health)
    preflight
    curl -fsS "http://127.0.0.1:${BACKEND_ACCEPTANCE_PORT}/web/login" >/dev/null
    echo "[backend.acceptance.health] PASS db=$BACKEND_ACCEPTANCE_DB url=http://127.0.0.1:$BACKEND_ACCEPTANCE_PORT"
    ;;
  frontend-up)
    preflight
    bash "$ROOT_DIR/scripts/dev/frontend_acceptance_up.sh"
    ;;
  frontend-down)
    bash "$ROOT_DIR/scripts/dev/frontend_acceptance_down.sh"
    ;;
  frontend-health)
    preflight
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
  *)
    echo "[acceptance.runtime] DENY unknown command: $command" >&2
    exit 2
    ;;
esac
