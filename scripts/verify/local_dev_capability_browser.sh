#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
ENV_FILE="${ENV_FILE:?ENV_FILE is required}"
[[ -f "$ENV_FILE" ]] || { echo "local.dev env file not found: $ENV_FILE" >&2; exit 2; }
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
[[ "${COMPOSE_PROJECT_NAME:-}" == "sc-local-dev" ]] || { echo "expected sc-local-dev" >&2; exit 2; }
[[ "${DB_NAME:-}" == "sc_dev_demo" ]] || { echo "expected sc_dev_demo" >&2; exit 2; }
[[ "${NGINX_PORT:-}" == "18081" ]] || { echo "expected local.dev port 18081" >&2; exit 2; }
[[ -n "${SC_DEMO_USER_PASSWORD:-}" ]] || { echo "SC_DEMO_USER_PASSWORD is required" >&2; exit 2; }

resolve_target() {
  DB_NAME="$DB_NAME" bash "$ROOT_DIR/scripts/ops/odoo_shell_exec.sh" < "$ROOT_DIR/scripts/verify/local_dev_capability_ids.py" | sed -n 's/^LOCAL_DEV_CAPABILITY_JSON=//p' | tail -1
}
before="$(resolve_target)"
[[ -n "$before" ]] || { echo "capability target resolution failed" >&2; exit 1; }
evidence_dir="$ROOT_DIR/.runtime/agent-runs/PRODUCT-ITERATION-V2-20261020/capability-browser"
mkdir -p "$evidence_dir"
printf '%s\n' "$before" > "$evidence_dir/before.json"
if [[ "${1:-}" == "--readback" ]]; then
  printf '%s\n' "$before"
  exit 0
fi
set +e
LOCAL_DEV_CAPABILITY_JSON="$before" FRONTEND_URL="http://127.0.0.1:${NGINX_PORT}/t/demo" \
E2E_PASSWORD="$SC_DEMO_USER_PASSWORD" CANDIDATE_HEAD="$(git -C "$ROOT_DIR" rev-parse HEAD)" \
node "$ROOT_DIR/scripts/verify/local_dev_capability_browser.mjs"
browser_status=$?
set -e
after="$(resolve_target)"
printf '%s\n' "$after" > "$evidence_dir/after.json"
BEFORE_JSON="$before" AFTER_JSON="$after" python3 - <<'PYREADBACK'
import json, os
before = json.loads(os.environ['BEFORE_JSON'])
after = json.loads(os.environ['AFTER_JSON'])
assert before == after, 'capability browser changed business data or projected state'
print('[capability.browser] business readback unchanged')
PYREADBACK
exit "$browser_status"
