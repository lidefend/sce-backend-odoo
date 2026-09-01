#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
ENV_FILE="${ENV_FILE:?ENV_FILE is required}"
[[ -f "$ENV_FILE" ]] || { echo "local.dev env file not found: $ENV_FILE" >&2; exit 2; }
LOCAL_DEV_CANONICAL_ENV_FILE="$(readlink -f "$ENV_FILE")"

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

[[ "${COMPOSE_PROJECT_NAME:-}" == "sc-local-dev" ]] || { echo "expected sc-local-dev" >&2; exit 2; }
[[ "${DB_NAME:-}" == "sc_dev_demo" ]] || { echo "expected sc_dev_demo" >&2; exit 2; }
[[ "${NGINX_PORT:-}" == "18081" ]] || { echo "expected custom frontend port 18081" >&2; exit 2; }
[[ -n "${SC_DEMO_USER_PASSWORD:-}" ]] || { echo "SC_DEMO_USER_PASSWORD is required" >&2; exit 2; }

resolve_target() {
  DB_NAME="$DB_NAME" bash "$ROOT_DIR/scripts/ops/odoo_shell_exec.sh" \
    < "$ROOT_DIR/scripts/verify/local_dev_payment_settlement_component_ids.py" \
    | sed -n 's/^LOCAL_DEV_PAYMENT_SETTLEMENT_COMPONENT_JSON=//p' | tail -1
}

before="$(resolve_target)"
[[ -n "$before" ]] || { echo "payment settlement component target resolution failed" >&2; exit 1; }

browser_status=0
LOCAL_DEV_PAYMENT_SETTLEMENT_COMPONENT_JSON="$before" \
FRONTEND_URL="http://127.0.0.1:${NGINX_PORT}" \
DB_NAME="$DB_NAME" E2E_PASSWORD="$SC_DEMO_USER_PASSWORD" \
node "$ROOT_DIR/scripts/verify/local_dev_payment_settlement_component_journey.mjs" || browser_status=$?

after="$(resolve_target)"
mutation_status=0
BEFORE_JSON="$before" AFTER_JSON="$after" python3 - <<'PY' || mutation_status=$?
import json
import os

before = json.loads(os.environ["BEFORE_JSON"])
after = json.loads(os.environ["AFTER_JSON"])
if after["request"]["line_count"] <= before["request"]["line_count"]:
    raise SystemExit("settlement journey did not create a payment request line")
if after["request"]["settlement_line_count"] <= before["request"]["settlement_line_count"]:
    raise SystemExit("settlement journey did not persist the selected settlement relationship")
print("[local.dev.payment.settlement-component] authoritative line relationship created")
PY

reset_status=0
ENV_FILE="$LOCAL_DEV_CANONICAL_ENV_FILE" \
  make -C "$ROOT_DIR" --no-print-directory local.dev.sync_demo || reset_status=$?
reset="$(resolve_target)"
BEFORE_JSON="$before" RESET_JSON="$reset" python3 - <<'PY' || reset_status=$?
import json
import os

before = json.loads(os.environ["BEFORE_JSON"])
reset = json.loads(os.environ["RESET_JSON"])
stable_fields = ("name", "state", "line_count", "settlement_line_count")
if any(reset["request"][field] != before["request"][field] for field in stable_fields):
    raise SystemExit("governed fixture reset did not restore payment settlement component baseline")
print("[local.dev.payment.settlement-component] fixture reset restored baseline")
PY

(( browser_status == 0 && mutation_status == 0 && reset_status == 0 ))
