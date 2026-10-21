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
  cat "$ROOT_DIR/scripts/verify/local_dev_base_configuration_domain_ids.py" \
    "$ROOT_DIR/scripts/verify/local_dev_system_parameter_readback.py" | \
    DB_NAME="$DB_NAME" bash "$ROOT_DIR/scripts/ops/odoo_shell_exec.sh" \
    | sed -n 's/^LOCAL_DEV_BASE_CONFIGURATION_DOMAIN_JSON=//p' | tail -1
}
if [[ "${1:-}" == "--readback" ]]; then
  resolve_target
  exit 0
fi
before="$(resolve_target)"
[[ -n "$before" ]] || { echo "system-parameter browser target resolution failed" >&2; exit 1; }
probe=local_dev_system_parameter_browser.mjs
folder=parameter-browser
if [[ "${1:-}" == "--mutation" ]]; then
  probe=local_dev_system_parameter_mutation.mjs
  folder="parameter-mutation-${SC_PARAMETER_SCENARIO:-payment_terms}"
fi
if [[ "${1:-}" == "--denial" ]]; then
  probe=local_dev_system_parameter_denial.mjs
  folder=parameter-denial
fi
evidence_dir="$ROOT_DIR/.runtime/agent-runs/PRODUCT-ITERATION-V2-20261020/$folder"
mkdir -p "$evidence_dir"
printf '%s\n' "$before" > "$evidence_dir/before.json"
set +e
FRONTEND_BASE_CONFIGURATION_DOMAIN_TARGET="$before" \
FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:${NGINX_PORT}/t/demo}" \
DB_NAME="$DB_NAME" E2E_PASSWORD="$SC_DEMO_USER_PASSWORD" \
CANDIDATE_HEAD="${CANDIDATE_GIT_HEAD:-$(git -C "$ROOT_DIR" rev-parse HEAD)}" \
node "$ROOT_DIR/scripts/verify/$probe"
browser_status=$?
set -e
after="$(resolve_target)"
printf '%s\n' "$after" > "$evidence_dir/after.json"
PROBE="$probe" BEFORE_JSON="$before" AFTER_JSON="$after" python3 - <<'PY'
import json, os
before = json.loads(os.environ["BEFORE_JSON"])
after = json.loads(os.environ["AFTER_JSON"])
if os.environ["PROBE"] == "local_dev_system_parameter_mutation.mjs":
    original = before["parameter_facts"]
    final = after["parameter_facts"]
    assert original["values"] == final["values"], "parameter authority not restored"
    assert original["purchase_default"] == final["purchase_default"], "business default not restored"
    assert original["approval_configuration"] == final["approval_configuration"], "approval configuration not restored"
    assert original["approval_required"] == final["approval_required"], "approval routing decision not restored"
    old = {row["id"]: row for row in original["changes"]}
    now = {row["id"]: row for row in final["changes"]}
    assert all(now.get(key) == row for key, row in old.items()), "preexisting audit changed"
    assert all(row["state"] == "rolled_back" and row["parameter_key"] in ("default_payment_terms", "approval_mode")
               for key, row in now.items() if key not in old), "new changes not restored"
elif before["business_fingerprint"] != after["business_fingerprint"]:
    raise SystemExit("system-parameter browser changed governed business data")
print("[frontend.system-parameter-domain.browser] authority recovery/read-only verification passed")
PY
exit "$browser_status"
