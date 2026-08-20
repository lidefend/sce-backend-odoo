#!/usr/bin/env bash
set -euo pipefail
: "${SC_FRONTEND_RELEASE_CI_ENTRY:?DENY: use a governed frontend acceptance Make target}"

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
export ROOT_DIR
operation="${1:?acceptance operation required}"

if [[ "${GITHUB_ACTIONS:-}" != "true" ]]; then
  export SC_FRONTEND_ACCEPTANCE_RUNTIME_ENTRY=operation_entry_v1
  SC_ACCEPTANCE_RUNTIME_PROFILE="${SC_ACCEPTANCE_RUNTIME_PROFILE:-local}" \
    bash "$ROOT_DIR/scripts/dev/frontend_acceptance_runtime.sh" "$operation"
  exit $?
fi

source "$ROOT_DIR/scripts/common/frontend_release_ci_identity.sh"
verify_frozen_frontend_release_ci_identity "$ROOT_DIR"

ci_frontend_pidfile="$RUNNER_TEMP/sce-ci-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}-frontend-release.pid"
ci_frontend_logfile="$RUNNER_TEMP/sce-ci-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}-frontend-release.log"
ci_frontend_dist="$ROOT_DIR/frontend/apps/web/dist-release"
for requested_pair in \
  "${FRONTEND_ACCEPTANCE_MODE:-}=production" \
  "${FRONTEND_ACCEPTANCE_STATIC_DIST:-}=$ci_frontend_dist" \
  "${FRONTEND_ACCEPTANCE_PORT:-}=5175" \
  "${FRONTEND_ACCEPTANCE_PIDFILE:-}=$ci_frontend_pidfile" \
  "${FRONTEND_ACCEPTANCE_LOGFILE:-}=$ci_frontend_logfile" \
  "${VITE_API_PROXY_TARGET:-}=http://127.0.0.1:18082" \
  "${FRONTEND_ACCEPTANCE_DB:-}=sc_frontend_acceptance"; do
  requested="${requested_pair%%=*}"
  expected="${requested_pair#*=}"
  [[ -z "$requested" || "$requested" == "$expected" ]] || {
    echo "DENY: isolated CI frontend process override mismatch" >&2
    exit 2
  }
done
export FRONTEND_ACCEPTANCE_MODE=production
export FRONTEND_ACCEPTANCE_STATIC_DIST="$ci_frontend_dist"
export FRONTEND_ACCEPTANCE_PORT=5175
export FRONTEND_ACCEPTANCE_PIDFILE="$ci_frontend_pidfile"
export FRONTEND_ACCEPTANCE_LOGFILE="$ci_frontend_logfile"
export VITE_API_PROXY_TARGET=http://127.0.0.1:18082
export FRONTEND_ACCEPTANCE_DB=sc_frontend_acceptance

validate_ci_frontend_process_identity() {
  local expected_dist
  expected_dist="$(readlink -f "$ci_frontend_dist")"
  [[ "${FRONTEND_ACCEPTANCE_MODE:-development}" == "production" ]] || {
    echo "DENY: isolated CI frontend must use production mode" >&2; return 2;
  }
  [[ "$(readlink -f "${FRONTEND_ACCEPTANCE_STATIC_DIST:-/nonexistent}")" == "$expected_dist" ]] || {
    echo "DENY: isolated CI frontend dist identity mismatch" >&2; return 2;
  }
  [[ "${FRONTEND_ACCEPTANCE_PORT:-5175}" == "5175" \
    && "$FRONTEND_ACCEPTANCE_PIDFILE" == "$ci_frontend_pidfile" \
    && "$FRONTEND_ACCEPTANCE_LOGFILE" == "$ci_frontend_logfile" \
    && "${VITE_API_PROXY_TARGET:-http://127.0.0.1:18082}" == "http://127.0.0.1:18082" \
    && "${FRONTEND_ACCEPTANCE_DB:-sc_frontend_acceptance}" == "sc_frontend_acceptance" ]] || {
    echo "DENY: isolated CI frontend process identity mismatch" >&2; return 2;
  }
}

ci_frontend_port_open() {
  (exec 3<>"/dev/tcp/127.0.0.1/${FRONTEND_ACCEPTANCE_PORT}") >/dev/null 2>&1
}

validate_ci_frontend_pidfile() {
  [[ -f "$FRONTEND_ACCEPTANCE_PIDFILE" && ! -L "$FRONTEND_ACCEPTANCE_PIDFILE" \
    && "$(stat -c %u "$FRONTEND_ACCEPTANCE_PIDFILE")" == "$(id -u)" ]] || {
    echo "DENY: isolated CI frontend pidfile identity mismatch" >&2
    return 2
  }
  local pid
  pid="$(<"$FRONTEND_ACCEPTANCE_PIDFILE")"
  [[ "$pid" =~ ^[0-9]+$ ]] || {
    echo "DENY: isolated CI frontend pid is invalid" >&2
    return 2
  }
  printf '%s\n' "$pid"
}

validate_ci_frontend_live_process() {
  local pid="$1" proc_env proc_cmd
  kill -0 "$pid" 2>/dev/null || return 1
  [[ "$(stat -c %u "/proc/$pid")" == "$(id -u)" \
    && "$(readlink -f "/proc/$pid/cwd")" == "$ROOT_DIR" ]] || {
    echo "DENY: isolated CI frontend owner/cwd mismatch" >&2
    return 2
  }
  proc_cmd="$(tr '\0' ' ' < "/proc/$pid/cmdline")"
  [[ "$proc_cmd" == *"$ROOT_DIR/scripts/release/release_static_server.mjs"* ]] || {
    echo "DENY: isolated CI frontend command mismatch" >&2
    return 2
  }
  proc_env="$(tr '\0' '\n' < "/proc/$pid/environ")"
  for expected_env in \
    "GITHUB_RUN_ID=$GITHUB_RUN_ID" \
    "GITHUB_RUN_ATTEMPT=$GITHUB_RUN_ATTEMPT" \
    "COMPOSE_PROJECT_NAME=$COMPOSE_PROJECT_NAME" \
    "SC_SOURCE_REVISION=$SC_SOURCE_REVISION" \
    "SC_FRONTEND_RELEASE_IDENTITY_FILE=$SC_FRONTEND_RELEASE_IDENTITY_FILE" \
    "STATIC_ROOT=$FRONTEND_ACCEPTANCE_STATIC_DIST" \
    "STATIC_PORT=$FRONTEND_ACCEPTANCE_PORT" \
    "API_PROXY_TARGET=$VITE_API_PROXY_TARGET"; do
    grep -Fxq "$expected_env" <<<"$proc_env" || {
      echo "DENY: isolated CI frontend environment mismatch" >&2
      return 2
    }
  done
  curl -fsS "http://127.0.0.1:${FRONTEND_ACCEPTANCE_PORT}/login" >/dev/null || {
    echo "DENY: isolated CI frontend process is unhealthy" >&2
    return 2
  }
}

case "$operation" in
  db-ensure)
    validate_frozen_frontend_release_ci_resources "$ROOT_DIR" optional
    source "$ROOT_DIR/scripts/common/compose.sh"
    compose_dev up -d --wait db redis odoo
    validate_frozen_frontend_release_ci_resources "$ROOT_DIR" required
    bash "$ROOT_DIR/scripts/test/frontend_acceptance_db_ensure.sh"
    validate_frozen_frontend_release_ci_resources "$ROOT_DIR" required
    # Module installation runs in a disposable Odoo process. Recycle the
    # already-running HTTP carrier so its registry reflects the installed
    # modules before any fixture or login request can reach it.
    compose_dev restart odoo
    compose_dev up -d --wait odoo
    validate_frozen_frontend_release_ci_resources "$ROOT_DIR" required
    echo "[frontend.acceptance.registry] RELOADED isolated_ci project=$COMPOSE_PROJECT_NAME sha=$SC_SOURCE_REVISION"
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
  core-record-form-journeys)
    validate_frozen_frontend_release_ci_resources "$ROOT_DIR" required
    # shellcheck source=../common/frontend_acceptance_make_identity.sh
    source "$ROOT_DIR/scripts/common/frontend_acceptance_make_identity.sh"
    frontend_acceptance_make "FE_PRO_03_JOURNEY=${FE_PRO_03_JOURNEY:-ALL}" verify.frontend.core_record_form.journeys
    ;;
  activity-surface-browser)
    validate_frozen_frontend_release_ci_resources "$ROOT_DIR" required
    # shellcheck source=../common/frontend_acceptance_make_identity.sh
    source "$ROOT_DIR/scripts/common/frontend_acceptance_make_identity.sh"
    frontend_acceptance_make verify.frontend.activity_surface.browser.internal
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
    if [[ -e "$FRONTEND_ACCEPTANCE_PIDFILE" || -L "$FRONTEND_ACCEPTANCE_PIDFILE" ]]; then
      frontend_pid="$(validate_ci_frontend_pidfile)"
      if kill -0 "$frontend_pid" 2>/dev/null; then
        validate_ci_frontend_live_process "$frontend_pid"
        export FRONTEND_ACCEPTANCE_ALLOW_REUSE=1
      fi
    fi
    bash "$ROOT_DIR/scripts/dev/frontend_acceptance_up.sh"
    ;;
  frontend-down)
    validate_ci_frontend_process_identity
    if [[ -e "$FRONTEND_ACCEPTANCE_PIDFILE" || -L "$FRONTEND_ACCEPTANCE_PIDFILE" ]]; then
      frontend_pid="$(validate_ci_frontend_pidfile)"
      if kill -0 "$frontend_pid" 2>/dev/null; then
        validate_ci_frontend_live_process "$frontend_pid"
      fi
    elif ci_frontend_port_open; then
      echo "DENY: isolated CI frontend port is owned without this run identity" >&2
      exit 2
    fi
    bash "$ROOT_DIR/scripts/dev/frontend_acceptance_down.sh"
    ;;
  *)
    echo "DENY: unsupported frontend acceptance operation=$operation" >&2
    exit 2
    ;;
esac
