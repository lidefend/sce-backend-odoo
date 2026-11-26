#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:?ROOT_DIR is required}"
ENV_FILE="${ENV_FILE:?ENV_FILE is required}"
CANDIDATE_SHA="${CANDIDATE_GIT_HEAD:?CANDIDATE_GIT_HEAD is required}"
TEST_TOOL_GIT_HEAD="${TEST_TOOL_GIT_HEAD:?TEST_TOOL_GIT_HEAD is required}"
: "${CONFIG_ADMIN_LOGIN:?CONFIG_ADMIN_LOGIN is required}"
: "${CONFIG_ADMIN_USER_ID:?CONFIG_ADMIN_USER_ID is required}"
: "${CONFIG_COMPANY_ID:?CONFIG_COMPANY_ID is required}"
SCENARIO_ONLY="${SCENARIO_ONLY:-0}"

source "${ROOT_DIR}/scripts/common/env.sh"
source "${ROOT_DIR}/scripts/common/guard_prod.sh"
guard_prod_forbid

[[ "${COMPOSE_PROJECT_NAME:-}" == "sc-local-dev" ]] || { echo "[DENY] expected sc-local-dev" >&2; exit 2; }
[[ "${DB_NAME:-}" == "sc_dev_demo" ]] || { echo "[DENY] expected sc_dev_demo" >&2; exit 2; }
[[ "${ODOO_DBFILTER:-}" == "^sc_dev_demo$" ]] || { echo "[DENY] expected exact sc_dev_demo dbfilter" >&2; exit 2; }
[[ "${SC_ENVIRONMENT:-}" == "dev" ]] || { echo "[DENY] expected SC_ENVIRONMENT=dev" >&2; exit 2; }
[[ "${SC_DEMO_USER_PASSWORD:-}" == "" ]] && { echo "[DENY] governed demo credential is missing" >&2; exit 2; }
[[ "$(git -C "$ROOT_DIR" rev-parse HEAD)" == "$TEST_TOOL_GIT_HEAD" ]] || {
  echo "[DENY] TEST_TOOL_GIT_HEAD does not match the current worktree" >&2
  exit 2
}

export E2E_PASSWORD="$SC_DEMO_USER_PASSWORD"
if [[ "${ENTERPRISE_READ_ONLY:-0}" == "1" ]]; then
  export FRONTEND_URL="http://127.0.0.1:18081/t/demo"
else
  export FRONTEND_URL="http://127.0.0.1:5176"
fi
export CONFIG_ADMIN_LOGIN CONFIG_ADMIN_USER_ID CONFIG_COMPANY_ID
export C02_SCENARIO_ONLY="$SCENARIO_ONLY"
export CANDIDATE_GIT_HEAD="$CANDIDATE_SHA"
export TEST_TOOL_GIT_HEAD
export ARTIFACT_DIR="${ARTIFACT_DIR:-${ROOT_DIR}/.runtime/agent-runs/SCENE-PRODUCT-02-ENTERPRISE-CONFIG-JOURNEY-20261120/enterprise-configuration-consumer}"

readonly_fingerprint() {
  DB_NAME="$DB_NAME" bash "$ROOT_DIR/scripts/ops/odoo_shell_exec.sh" <<'PYREAD' | sed -n 's/^ENTERPRISE_STATE=//p' | tail -1
import hashlib, json
assert env.cr.dbname == 'sc_dev_demo'
facts = {}
for model in ('res.company', 'hr.department', 'hr.job', 'hr.employee', 'res.users', 'sc.scene.company.enablement'):
    facts[model] = env[model].sudo().with_context(active_test=False).search_read([], ['id', 'write_date'], order='id')
print('ENTERPRISE_STATE=' + hashlib.sha256(json.dumps(facts, sort_keys=True, default=str).encode()).hexdigest())
env.cr.rollback()
PYREAD
}
if [[ "${ENTERPRISE_READ_ONLY:-0}" == "1" ]]; then
  before="$(readonly_fingerprint)"
  [[ "$before" =~ ^[0-9a-f]{64}$ ]] || { echo '[DENY] missing enterprise readback'; exit 2; }
  mkdir -p "$ARTIFACT_DIR"
  printf '%s\n' "$before" > "$ARTIFACT_DIR/state-before.sha256"
fi
set +e
node "${ROOT_DIR}/scripts/verify/local_dev_enterprise_configuration_consumer.mjs"
browser_status=$?
set -e
if [[ "${ENTERPRISE_READ_ONLY:-0}" == "1" ]]; then
  after="$(readonly_fingerprint)"
  printf '%s\n' "$after" > "$ARTIFACT_DIR/state-after.sha256"
  [[ "$before" == "$after" ]] || { echo '[FAIL] enterprise business state changed'; exit 1; }
  echo '[enterprise-initialization] business state unchanged'
fi
exit "$browser_status"
