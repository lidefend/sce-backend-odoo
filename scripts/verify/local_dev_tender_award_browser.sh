#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:?ROOT_DIR is required}"
ENV_FILE="${ENV_FILE:?ENV_FILE is required}"
PRODUCT_SHA="${PRODUCT_CANDIDATE_SHA:?PRODUCT_CANDIDATE_SHA is required}"
TOOL_SHA="${P4_TOOL_CANDIDATE_SHA:?P4_TOOL_CANDIDATE_SHA is required}"
BATCH="${P4_TENDER_AWARD_BATCH:?P4_TENDER_AWARD_BATCH is required}"

source "${ROOT_DIR}/scripts/common/env.sh"
source "${ROOT_DIR}/scripts/common/guard_prod.sh"
guard_prod_forbid

[[ "${COMPOSE_PROJECT_NAME:-}" == "sc-local-dev" ]] || { echo "[DENY] expected sc-local-dev" >&2; exit 2; }
[[ "${DB_NAME:-}" == "sc_dev_demo" ]] || { echo "[DENY] expected sc_dev_demo" >&2; exit 2; }
[[ "${ODOO_DBFILTER:-}" == "^sc_dev_demo$" ]] || { echo "[DENY] expected exact sc_dev_demo dbfilter" >&2; exit 2; }
[[ "${SC_ENVIRONMENT:-}" == "dev" ]] || { echo "[DENY] expected SC_ENVIRONMENT=dev" >&2; exit 2; }
[[ "${FRONTEND_URL:-http://127.0.0.1:5176}" == "http://127.0.0.1:5176" ]] || { echo "[DENY] expected candidate frontend 5176" >&2; exit 2; }
[[ "${PRODUCT_SHA}" =~ ^[0-9a-f]{40}$ ]] || { echo "[DENY] product SHA must be full" >&2; exit 2; }
[[ "${TOOL_SHA}" =~ ^[0-9a-f]{40}$ ]] || { echo "[DENY] tool SHA must be full" >&2; exit 2; }

export FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:5176}"
PRODUCT_CANDIDATE_SHA="${PRODUCT_SHA}"
P4_TOOL_CANDIDATE_SHA="${TOOL_SHA}"
P4_TENDER_AWARD_BATCH="${BATCH}"
export SC_ENVIRONMENT DB_NAME ODOO_DBFILTER PRODUCT_CANDIDATE_SHA P4_TOOL_CANDIDATE_SHA P4_TENDER_AWARD_BATCH
export SC_DEMO_USER_PASSWORD="${SC_DEMO_USER_PASSWORD:?SC_DEMO_USER_PASSWORD is required}"
export ARTIFACT_DIR="${ARTIFACT_DIR:-}"
node "${ROOT_DIR}/scripts/verify/local_dev_tender_award_browser.mjs"
