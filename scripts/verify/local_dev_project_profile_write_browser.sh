#!/usr/bin/env bash
set -euo pipefail

project_id="${PROJECT_ID-}"
[[ "$project_id" =~ ^[1-9][0-9]*$ ]] || { echo "[DENY] PROJECT_ID must be an explicit positive integer" >&2; exit 2; }
[[ "${#project_id}" -le 10 ]] && (( 10#$project_id <= 2147483647 )) \
  || { echo "[DENY] PROJECT_ID is outside the supported record ID range" >&2; exit 2; }
PROJECT_ID="$project_id"
for test_only_name in P4_RUNNER_VALIDATE_ONLY P4_RUNNER_SERVED_PRODUCT_SHA P4_PROJECT_PROFILE_AUTHORITY_JSON P4_RUNNER_FACTS_JSON; do
  if [[ -n "${!test_only_name+x}" ]]; then
    echo "[DENY] ${test_only_name} is test-only and forbidden by the governed browser entry" >&2
    exit 2
  fi
done
ROOT_DIR="${ROOT_DIR:?ROOT_DIR is required}"
ENV_FILE="${ENV_FILE:?ENV_FILE is required}"
PRODUCT_CANDIDATE_SHA="${PRODUCT_CANDIDATE_SHA:?PRODUCT_CANDIDATE_SHA is required}"
source "${ROOT_DIR}/scripts/common/env.sh"
source "${ROOT_DIR}/scripts/common/guard_prod.sh"
guard_prod_forbid
[[ "${COMPOSE_PROJECT_NAME:-}" == "sc-local-dev" ]] || { echo "[DENY] expected sc-local-dev" >&2; exit 2; }
[[ "${DB_NAME:-}" == "sc_dev_demo" ]] || { echo "[DENY] expected sc_dev_demo" >&2; exit 2; }
[[ "${ODOO_DBFILTER:-}" == "^sc_dev_demo$" ]] || { echo "[DENY] expected exact sc_dev_demo dbfilter" >&2; exit 2; }
[[ "${SC_ENVIRONMENT:-}" == "dev" ]] || { echo "[DENY] expected SC_ENVIRONMENT=dev" >&2; exit 2; }
[[ "${FRONTEND_URL:-http://127.0.0.1:5176}" == "http://127.0.0.1:5176" ]] || { echo "[DENY] expected candidate frontend 5176" >&2; exit 2; }
for flag_name in READ_ONLY PREFLIGHT_ONLY NETWORK_FAILURE_RECOVERY; do
  flag_value="${!flag_name:-0}"
  [[ "$flag_value" =~ ^[01]$ ]] || { echo "[DENY] ${flag_name} must be 0 or 1" >&2; exit 2; }
done
if [[ "${NETWORK_FAILURE_RECOVERY:-0}" == "1" && ( "${READ_ONLY:-0}" == "1" || "${PREFLIGHT_ONLY:-0}" == "1" ) ]]; then
  echo "[DENY] read-only preflight cannot enable failure injection or retry" >&2
  exit 2
fi
pidfile="/tmp/sc-local-dev-candidate-frontend.pid"
[[ -f "$pidfile" ]] || { echo "[DENY] candidate pidfile missing" >&2; exit 2; }
served_sha="$(python3 - "$pidfile" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as handle:
    print(json.load(handle).get("head", ""))
PY
)"
[[ "$served_sha" == "$PRODUCT_CANDIDATE_SHA" ]] || { echo "[DENY] product candidate SHA mismatch: $served_sha" >&2; exit 2; }

if [[ "${READ_ONLY:-0}" != "1" && "${PREFLIGHT_ONLY:-0}" != "1" ]]; then
  batch="${P4_PROJECT_PROFILE_BATCH-}"
  [[ "$batch" =~ ^[a-z0-9][a-z0-9-]{2,31}$ ]] || { echo "[DENY] P4_PROJECT_PROFILE_BATCH is required in write mode" >&2; exit 2; }
  tool_sha="${P4_TOOL_CANDIDATE_SHA:?P4_TOOL_CANDIDATE_SHA is required in write mode}"
  [[ "$tool_sha" =~ ^[0-9a-f]{40}$ ]] || { echo "[DENY] P4_TOOL_CANDIDATE_SHA must be a full SHA" >&2; exit 2; }
  export P4_PROJECT_PROFILE_BATCH="$batch"
  export P4_TOOL_CANDIDATE_SHA="$tool_sha"
fi
export FRONTEND_URL DB_NAME E2E_PASSWORD="${SC_DEMO_USER_PASSWORD:?SC_DEMO_USER_PASSWORD is required}"
export PROJECT_ID ACTION_ID="${ACTION_ID:-861}" MENU_ID="${MENU_ID:-681}"
export PROJECT_NAME="${PROJECT_NAME:-}" NETWORK_FAILURE_RECOVERY="${NETWORK_FAILURE_RECOVERY:-0}"
export ARTIFACT_DIR="${ARTIFACT_DIR:-}"
export PM_LOGIN="${PM_LOGIN:-demo_role_project_manager}"
export MEMBER_LOGIN="${MEMBER_LOGIN:-demo_role_project_a_member}"
export READ_LOGIN="${READ_LOGIN:-demo_role_project_read}"
node "${ROOT_DIR}/scripts/verify/local_dev_project_profile_write_browser.mjs"
