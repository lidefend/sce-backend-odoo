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
[[ "${ODOO_PORT:-}" == "8070" ]] || { echo "expected native Odoo port 8070" >&2; exit 2; }
[[ "${NGINX_PORT:-}" == "18081" ]] || { echo "expected custom frontend port 18081" >&2; exit 2; }
[[ -n "${SC_DEMO_USER_PASSWORD:-}" ]] || { echo "SC_DEMO_USER_PASSWORD is required" >&2; exit 2; }

resolve_target() {
  DB_NAME="$DB_NAME" bash "$ROOT_DIR/scripts/ops/odoo_shell_exec.sh" \
    < "$ROOT_DIR/scripts/verify/local_dev_payment_request_native_parity_ids.py" \
    | sed -n 's/^LOCAL_DEV_PAYMENT_PARITY_JSON=//p' | tail -1
}

before="$(resolve_target)"
[[ -n "$before" ]] || { echo "payment parity target resolution failed" >&2; exit 1; }
BEFORE_JSON="$before" python3 - <<'PY'
import json
import os

payload = json.loads(os.environ["BEFORE_JSON"])
print("[local.dev.payment.native-parity] execution contracts=%s" % json.dumps(
    payload.get("execution_contract_inventory", []),
    ensure_ascii=False,
    separators=(",", ":"),
))
PY

set +e
LOCAL_DEV_PAYMENT_PARITY_JSON="$before" \
FRONTEND_URL="http://127.0.0.1:${NGINX_PORT}" \
ODOO_URL="http://127.0.0.1:${ODOO_PORT}" \
DB_NAME="$DB_NAME" E2E_PASSWORD="$SC_DEMO_USER_PASSWORD" \
node "$ROOT_DIR/scripts/verify/local_dev_payment_request_native_parity_readonly.mjs"
browser_status=$?
set -e

after="$(resolve_target)"
BEFORE_JSON="$before" AFTER_JSON="$after" python3 - <<'PY'
import json
import os

before = json.loads(os.environ["BEFORE_JSON"])
after = json.loads(os.environ["AFTER_JSON"])
if before["business_fingerprint"] != after["business_fingerprint"]:
    raise SystemExit("payment parity probe changed governed business data")
print("[local.dev.payment.native-parity] business fingerprint unchanged")
PY
exit "$browser_status"
