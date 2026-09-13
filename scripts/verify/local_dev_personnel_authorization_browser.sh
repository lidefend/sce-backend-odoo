#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:?ROOT_DIR is required}"
ENV_FILE="${ENV_FILE:?ENV_FILE is required}"
person_id="${PERSON_ID-}"
project_id="${PROJECT_ID-}"
[[ "$person_id" =~ ^[1-9][0-9]*$ ]] || { echo "[DENY] PERSON_ID must be an explicit positive integer" >&2; exit 2; }
[[ "$project_id" =~ ^[1-9][0-9]*$ ]] || { echo "[DENY] PROJECT_ID must be an explicit positive integer" >&2; exit 2; }
source "${ROOT_DIR}/scripts/common/env.sh"
source "${ROOT_DIR}/scripts/common/guard_prod.sh"
guard_prod_forbid
[[ "${COMPOSE_PROJECT_NAME:-}" == "sc-local-dev" ]] || { echo "[DENY] expected sc-local-dev" >&2; exit 2; }
[[ "${DB_NAME:-}" == "sc_dev_demo" ]] || { echo "[DENY] expected sc_dev_demo" >&2; exit 2; }
[[ "${ODOO_DBFILTER:-}" == "^sc_dev_demo$" ]] || { echo "[DENY] expected exact sc_dev_demo dbfilter" >&2; exit 2; }
[[ "${SC_ENVIRONMENT:-}" == "dev" ]] || { echo "[DENY] expected SC_ENVIRONMENT=dev" >&2; exit 2; }
[[ "${FRONTEND_URL:-http://127.0.0.1:5176}" == "http://127.0.0.1:5176" ]] || { echo "[DENY] expected candidate frontend 5176" >&2; exit 2; }
batch="${P4_PERSONNEL_AUTH_BATCH-}"
[[ "$batch" =~ ^[a-z0-9][a-z0-9-]{2,31}$ ]] || { echo "[DENY] P4_PERSONNEL_AUTH_BATCH is required" >&2; exit 2; }
product_sha="${PRODUCT_CANDIDATE_SHA:?PRODUCT_CANDIDATE_SHA is required}"
tool_sha="${P4_TOOL_CANDIDATE_SHA:?P4_TOOL_CANDIDATE_SHA is required}"
[[ "$product_sha" =~ ^[0-9a-f]{40}$ && "$tool_sha" =~ ^[0-9a-f]{40}$ ]] || { echo "[DENY] product/tool SHA must be full immutable SHAs" >&2; exit 2; }

export FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:5176}" DB_NAME SC_ENVIRONMENT ODOO_DBFILTER
export P4_PERSONNEL_AUTH_BATCH="$batch" PRODUCT_CANDIDATE_SHA="$product_sha" P4_TOOL_CANDIDATE_SHA="$tool_sha"
export PERSON_ID="$person_id" PROJECT_ID="$project_id"
export E2E_PASSWORD="${SC_DEMO_USER_PASSWORD:?SC_DEMO_USER_PASSWORD is required}"
export ARTIFACT_DIR="${ARTIFACT_DIR:-}"
node "${ROOT_DIR}/scripts/verify/local_dev_personnel_authorization_browser.mjs"
