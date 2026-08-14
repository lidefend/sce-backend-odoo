#!/usr/bin/env bash
set -euo pipefail
: "${SC_GOVERNED_FRONTEND_ACCEPTANCE_OPERATION_ENTRY:?DENY: use a governed frontend/backend acceptance Make target; direct operation execution is forbidden}"

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
export ROOT_DIR
operation="${1:?acceptance operation required}"
source "$ROOT_DIR/scripts/common/governed_make_entry.sh"
require_governed_make_ancestor "frontend_acceptance_operation_entry.sh" "$ROOT_DIR" "acceptance.frontend.fixture,acceptance.frontend.release_snapshot,backend.acceptance.up,backend.acceptance.down,frontend.acceptance.up,frontend.acceptance.down"

if [[ "${GITHUB_ACTIONS:-}" != "true" ]]; then
  SC_GOVERNED_ACCEPTANCE_ENTRY=1 SC_ACCEPTANCE_RUNTIME_PROFILE="${SC_ACCEPTANCE_RUNTIME_PROFILE:-local}" bash "$ROOT_DIR/scripts/dev/frontend_acceptance_runtime.sh" "$operation"
  exit $?
fi

source "$ROOT_DIR/scripts/common/frontend_release_ci_identity.sh"
validate_frontend_release_ci_identity "$ROOT_DIR"
case "$operation" in
  fixture)
    SC_GOVERNED_FRONTEND_FIXTURE_LOWER_ENTRY=1 bash "$ROOT_DIR/scripts/test/frontend_productization_fixture.sh"
    ;;
  release-snapshot)
    bash "$ROOT_DIR/scripts/ops/odoo_shell_exec.sh" < "$ROOT_DIR/scripts/test/frontend_acceptance_release_snapshot.py"
    ;;
  backend-up)
    source "$ROOT_DIR/scripts/common/compose.sh"
    container_id="$(compose_dev ps -q odoo)"
    [[ -n "$container_id" && "$(docker inspect "$container_id" --format '{{.State.Running}}')" == "true" ]] || {
      echo "DENY: isolated CI Odoo container is not running" >&2; exit 2;
    }
    [[ "$(docker inspect "$container_id" --format '{{index .Config.Labels "com.docker.compose.project"}}')" == "$COMPOSE_PROJECT_NAME" ]] || {
      echo "DENY: isolated CI Odoo compose project identity mismatch" >&2; exit 2;
    }
    [[ "$(docker inspect "$container_id" --format '{{(index (index .HostConfig.PortBindings "8069/tcp") 0).HostPort}}')" == "$ODOO_PORT" ]] || {
      echo "DENY: isolated CI Odoo published port identity mismatch" >&2; exit 2;
    }
    container_env="$(docker inspect "$container_id" --format '{{range .Config.Env}}{{println .}}{{end}}')"
    grep -Fxq "DB_NAME=$DB_NAME" <<< "$container_env"
    grep -Fxq "ODOO_DB=$DB_NAME" <<< "$container_env"
    grep -Fxq "ODOO_DBFILTER=$ODOO_DBFILTER" <<< "$container_env"
    grep -Fxq "SC_SOURCE_REVISION=$SC_SOURCE_REVISION" <<< "$container_env"
    expected_addons="$(readlink -f "$ROOT_DIR/addons")"
    mounted_addons="$(docker inspect "$container_id" --format '{{range .Mounts}}{{if eq .Destination "/mnt/source-addons"}}{{.Source}}{{end}}{{end}}')"
    mounted_odoo_data="$(docker inspect "$container_id" --format '{{range .Mounts}}{{if eq .Destination "/var/lib/odoo"}}{{.Name}}{{end}}{{end}}')"
    [[ "$(readlink -f "$mounted_addons")" == "$expected_addons" && "$mounted_odoo_data" == "$ODOO_DATA" ]] || {
      echo "DENY: isolated CI Odoo source or data mount identity mismatch" >&2; exit 2;
    }
    curl -fsS "http://127.0.0.1:${ODOO_PORT}/web/login" >/dev/null
    echo "[backend.acceptance.up] REUSED isolated_ci project=$COMPOSE_PROJECT_NAME port=$ODOO_PORT"
    ;;
  backend-down)
    echo "[backend.acceptance.down] RETAINED isolated_ci project=$COMPOSE_PROJECT_NAME for workflow cleanup"
    ;;
  frontend-up)
    SC_GOVERNED_ACCEPTANCE_LOWER_ENTRY=1 bash "$ROOT_DIR/scripts/dev/frontend_acceptance_up.sh"
    ;;
  frontend-down)
    SC_GOVERNED_ACCEPTANCE_LOWER_ENTRY=1 bash "$ROOT_DIR/scripts/dev/frontend_acceptance_down.sh"
    ;;
  *)
    echo "DENY: unsupported frontend acceptance operation=$operation" >&2
    exit 2
    ;;
esac
