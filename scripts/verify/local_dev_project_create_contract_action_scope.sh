#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:?ROOT_DIR is required}"
ENV_FILE="${ENV_FILE:?ENV_FILE is required}"
[[ -f "${ENV_FILE}" ]] || { echo "local.dev env file not found: ${ENV_FILE}" >&2; exit 2; }

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

[[ "${COMPOSE_PROJECT_NAME:-}" == "sc-local-dev" ]] || { echo "expected sc-local-dev" >&2; exit 2; }
[[ "${DB_NAME:-}" == "sc_dev_demo" ]] || { echo "expected sc_dev_demo" >&2; exit 2; }
[[ "${ODOO_DBFILTER:-}" == "^sc_dev_demo$" ]] || { echo "expected local.dev dbfilter" >&2; exit 2; }

cleanup_collaboration_fixtures() {
  local journey_status=$?
  local cleanup_status=0
  local cleanup_output=""
  trap - EXIT
  set +e
  cleanup_output="$(DB_NAME="${DB_NAME}" bash "${ROOT_DIR}/scripts/ops/odoo_shell_exec.sh" \
    < "${ROOT_DIR}/scripts/verify/local_dev_collaboration_fixture_cleanup.py")"
  cleanup_status=$?
  set -e
  printf '%s\n' "${cleanup_output}"
  if [[ "${cleanup_status}" -ne 0 ]]; then
    echo "collaboration fixture cleanup failed" >&2
    exit "${cleanup_status}"
  fi
  exit "${journey_status}"
}
trap cleanup_collaboration_fixtures EXIT

probe_output="$(DB_NAME="${DB_NAME}" bash "${ROOT_DIR}/scripts/ops/odoo_shell_exec.sh" \
  < "${ROOT_DIR}/scripts/verify/local_dev_project_create_contract_action_scope.py")"
printf '%s\n' "${probe_output}"
probe_json="$(printf '%s\n' "${probe_output}" | sed -n 's/^LOCAL_DEV_PROJECT_CREATE_ACTION_SCOPE_JSON=//p' | tail -1)"
[[ -n "${probe_json}" ]] || { echo "project create Contract V2 scope probe returned no identity" >&2; exit 1; }

# Running the fixture probe in the live Odoo carrier can briefly overlap a
# worker recycle. Require three consecutive upstream responses before starting
# the browser so a transient 502 cannot be mistaken for a product regression.
stable_upstream_checks=0
for _attempt in $(seq 1 30); do
  if python3 - "http://127.0.0.1:${NGINX_PORT}/web/login?db=${DB_NAME}" <<'PY'
import sys
import urllib.request

with urllib.request.urlopen(sys.argv[1], timeout=5) as response:
    if response.status != 200:
        raise SystemExit(1)
PY
  then
    stable_upstream_checks=$((stable_upstream_checks + 1))
    [[ "${stable_upstream_checks}" -ge 3 ]] && break
  else
    stable_upstream_checks=0
  fi
  sleep 1
done
[[ "${stable_upstream_checks}" -ge 3 ]] || { echo "local.dev Odoo upstream did not stabilize before browser journey" >&2; exit 1; }

LOCAL_DEV_PROJECT_CREATE_SCOPE_JSON="${probe_json}" \
FRONTEND_URL="http://127.0.0.1:${NGINX_PORT}" \
E2E_PASSWORD="${SC_DEMO_USER_PASSWORD:?SC_DEMO_USER_PASSWORD is required}" \
node "${ROOT_DIR}/scripts/verify/local_dev_project_create_contract_driver_probe.mjs"
