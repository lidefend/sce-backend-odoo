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

probe_output="$(DB_NAME="${DB_NAME}" bash "${ROOT_DIR}/scripts/ops/odoo_shell_exec.sh" \
  < "${ROOT_DIR}/scripts/verify/local_dev_project_create_contract_action_scope.py")"
printf '%s\n' "${probe_output}"
probe_json="$(printf '%s\n' "${probe_output}" | sed -n 's/^LOCAL_DEV_PROJECT_CREATE_ACTION_SCOPE_JSON=//p' | tail -1)"
[[ -n "${probe_json}" ]] || { echo "project create Contract V2 scope probe returned no identity" >&2; exit 1; }

LOCAL_DEV_PROJECT_CREATE_SCOPE_JSON="${probe_json}" \
FRONTEND_URL="http://127.0.0.1:${NGINX_PORT}" \
E2E_PASSWORD="${SC_DEMO_USER_PASSWORD:?SC_DEMO_USER_PASSWORD is required}" \
node "${ROOT_DIR}/scripts/verify/local_dev_project_create_contract_driver_probe.mjs"
