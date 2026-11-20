#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:?ROOT_DIR is required}"
ENV_FILE="${ENV_FILE:?ENV_FILE is required}"
CANDIDATE_SHA="${CANDIDATE_GIT_HEAD:?CANDIDATE_GIT_HEAD is required}"
CONFIG_ADMIN_LOGIN="${CONFIG_ADMIN_LOGIN:-sc_demo_business_config}"
CONFIG_ADMIN_USER_ID="${CONFIG_ADMIN_USER_ID:-24}"
CONFIG_COMPANY_ID="${CONFIG_COMPANY_ID:-1}"

source "${ROOT_DIR}/scripts/common/env.sh"
source "${ROOT_DIR}/scripts/common/guard_prod.sh"
guard_prod_forbid

[[ "${COMPOSE_PROJECT_NAME:-}" == "sc-local-dev" ]] || { echo "[DENY] expected sc-local-dev" >&2; exit 2; }
[[ "${DB_NAME:-}" == "sc_dev_demo" ]] || { echo "[DENY] expected sc_dev_demo" >&2; exit 2; }
[[ "${ODOO_DBFILTER:-}" == "^sc_dev_demo$" ]] || { echo "[DENY] expected exact sc_dev_demo dbfilter" >&2; exit 2; }
[[ "${SC_ENVIRONMENT:-}" == "dev" ]] || { echo "[DENY] expected SC_ENVIRONMENT=dev" >&2; exit 2; }
[[ "${SC_DEMO_USER_PASSWORD:-}" == "" ]] && { echo "[DENY] governed demo credential is missing" >&2; exit 2; }
[[ "$(git -C "$ROOT_DIR" rev-parse HEAD)" == "$CANDIDATE_SHA" ]] || {
  echo "[DENY] CANDIDATE_GIT_HEAD does not match the current worktree" >&2
  exit 2
}

export E2E_PASSWORD="$SC_DEMO_USER_PASSWORD"
export FRONTEND_URL="http://127.0.0.1:5176"
export CONFIG_ADMIN_LOGIN CONFIG_ADMIN_USER_ID CONFIG_COMPANY_ID
export CANDIDATE_GIT_HEAD="$CANDIDATE_SHA"
export ARTIFACT_DIR="${ARTIFACT_DIR:-${ROOT_DIR}/.runtime/agent-runs/SCENE-PRODUCT-02-ENTERPRISE-CONFIG-JOURNEY-20261120/enterprise-configuration-consumer}"

node "${ROOT_DIR}/scripts/verify/local_dev_enterprise_configuration_consumer.mjs"
