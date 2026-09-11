#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:?ROOT_DIR is required}"
PRODUCT_CANDIDATE_SHA="${PRODUCT_CANDIDATE_SHA:?PRODUCT_CANDIDATE_SHA is required}"
[[ "${DB_NAME:-sc_dev_demo}" == "sc_dev_demo" ]] || { echo "[DENY] expected sc_dev_demo" >&2; exit 2; }
[[ "${FRONTEND_URL:-http://127.0.0.1:5176}" == "http://127.0.0.1:5176" ]] || { echo "[DENY] expected candidate frontend 5176" >&2; exit 2; }
pidfile="/tmp/sc-local-dev-candidate-frontend.pid"
[[ -f "$pidfile" ]] || { echo "[DENY] candidate pidfile missing" >&2; exit 2; }
served_sha="$(python3 - "$pidfile" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as handle:
    print(json.load(handle).get("head", ""))
PY
)"
[[ "$served_sha" == "$PRODUCT_CANDIDATE_SHA" ]] || { echo "[DENY] product candidate SHA mismatch: $served_sha" >&2; exit 2; }
export FRONTEND_URL DB_NAME E2E_PASSWORD="${SC_DEMO_USER_PASSWORD:?SC_DEMO_USER_PASSWORD is required}"
export PROJECT_ID="${PROJECT_ID:-366}" ACTION_ID="${ACTION_ID:-861}" MENU_ID="${MENU_ID:-681}"
export PM_LOGIN="${PM_LOGIN:-demo_role_project_manager}"
export MEMBER_LOGIN="${MEMBER_LOGIN:-demo_role_project_a_member}"
export READ_LOGIN="${READ_LOGIN:-demo_role_project_read}"
node "${ROOT_DIR}/scripts/verify/local_dev_project_profile_write_browser.mjs"
