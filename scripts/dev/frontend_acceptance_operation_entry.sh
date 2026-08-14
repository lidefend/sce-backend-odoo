#!/usr/bin/env bash
set -euo pipefail
: "${SC_FRONTEND_RELEASE_CI_ENTRY:?DENY: use a governed frontend acceptance Make target}"

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
export ROOT_DIR
operation="${1:?acceptance operation required}"

if [[ "${GITHUB_ACTIONS:-}" != "true" ]]; then
  SC_ACCEPTANCE_RUNTIME_PROFILE="${SC_ACCEPTANCE_RUNTIME_PROFILE:-local}" \
    bash "$ROOT_DIR/scripts/dev/frontend_acceptance_runtime.sh" "$operation"
  exit $?
fi

source "$ROOT_DIR/scripts/common/frontend_release_ci_identity.sh"
verify_frozen_frontend_release_ci_identity "$ROOT_DIR"

validate_ci_frontend_process_identity() {
  local expected_dist
  expected_dist="$(readlink -f "$ROOT_DIR/frontend/apps/web/dist-release")"
  [[ "${FRONTEND_ACCEPTANCE_MODE:-development}" == "production" ]] || {
    echo "DENY: isolated CI frontend must use production mode" >&2; return 2;
  }
  [[ "$(readlink -f "${FRONTEND_ACCEPTANCE_STATIC_DIST:-/nonexistent}")" == "$expected_dist" ]] || {
    echo "DENY: isolated CI frontend dist identity mismatch" >&2; return 2;
  }
  [[ "${FRONTEND_ACCEPTANCE_PORT:-5175}" == "5175" \
    && "${FRONTEND_ACCEPTANCE_PIDFILE:-/tmp/sc-frontend-acceptance.pid}" == "/tmp/sc-frontend-acceptance.pid" \
    && "${FRONTEND_ACCEPTANCE_LOGFILE:-/tmp/sc-frontend-acceptance.log}" == "/tmp/sc-frontend-acceptance.log" \
    && "${VITE_API_PROXY_TARGET:-http://127.0.0.1:18082}" == "http://127.0.0.1:18082" \
    && "${FRONTEND_ACCEPTANCE_DB:-sc_frontend_acceptance}" == "sc_frontend_acceptance" ]] || {
    echo "DENY: isolated CI frontend process identity mismatch" >&2; return 2;
  }
}

case "$operation" in
  db-ensure)
    validate_frozen_frontend_release_ci_resources "$ROOT_DIR" optional
    source "$ROOT_DIR/scripts/common/compose.sh"
    compose_dev up -d --wait db redis odoo
    validate_frozen_frontend_release_ci_resources "$ROOT_DIR" required
    bash "$ROOT_DIR/scripts/test/frontend_acceptance_db_ensure.sh"
    ;;
  fixture)
    [[ -n "${SC_ACCEPTANCE_FIXTURE_PASSWORD:-}" ]] || {
      echo "DENY: frontend acceptance fixture password is required" >&2; exit 2;
    }
    bash "$ROOT_DIR/scripts/test/frontend_productization_fixture.sh"
    ;;
  release-snapshot)
    bash "$ROOT_DIR/scripts/ops/odoo_shell_exec.sh" \
      < "$ROOT_DIR/scripts/test/frontend_acceptance_release_snapshot.py"
    ;;
  backend-up)
    validate_frozen_frontend_release_ci_resources "$ROOT_DIR" required
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
    curl -fsS "http://127.0.0.1:${ODOO_PORT}/web/login" >/dev/null
    echo "[backend.acceptance.up] REUSED isolated_ci project=$COMPOSE_PROJECT_NAME port=$ODOO_PORT"
    ;;
  backend-down)
    echo "[backend.acceptance.down] RETAINED isolated_ci project=$COMPOSE_PROJECT_NAME for workflow cleanup"
    ;;
  frontend-up)
    validate_ci_frontend_process_identity
    bash "$ROOT_DIR/scripts/dev/frontend_acceptance_up.sh"
    ;;
  frontend-down)
    validate_ci_frontend_process_identity
    bash "$ROOT_DIR/scripts/dev/frontend_acceptance_down.sh"
    ;;
  *)
    echo "DENY: unsupported frontend acceptance operation=$operation" >&2
    exit 2
    ;;
esac
