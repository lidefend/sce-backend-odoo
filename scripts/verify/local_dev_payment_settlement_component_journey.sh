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
[[ "${CANDIDATE_GIT_HEAD:-}" =~ ^[0-9a-f]{40}$ ]] || { echo "CANDIDATE_GIT_HEAD is required" >&2; exit 2; }
[[ "$(git -C "$ROOT_DIR" rev-parse HEAD)" == "$CANDIDATE_GIT_HEAD" ]] || { echo "candidate head mismatch" >&2; exit 2; }

EVIDENCE_DIR="${EVIDENCE_DIR:-$ROOT_DIR/artifacts/playwright/local-dev-payment-settlement-component-journey}"
mkdir -p "$EVIDENCE_DIR"

resolve_target() {
  DB_NAME="$DB_NAME" bash "$ROOT_DIR/scripts/ops/odoo_shell_exec.sh" \
    < "$ROOT_DIR/scripts/verify/local_dev_payment_settlement_component_ids.py" \
    | sed -n 's/^LOCAL_DEV_PAYMENT_SETTLEMENT_COMPONENT_JSON=//p' | tail -1
}

ENV_FILE="$LOCAL_DEV_CANONICAL_ENV_FILE" \
  make -C "$ROOT_DIR" --no-print-directory local.dev.reset_payment_request_fixture

before="$(resolve_target)"
[[ -n "$before" ]] || { echo "payment settlement component target resolution failed" >&2; exit 1; }

introduce_status=0
LOCAL_DEV_PAYMENT_SETTLEMENT_COMPONENT_JSON="$before" \
CANDIDATE_GIT_HEAD="$CANDIDATE_GIT_HEAD" JOURNEY_PHASE="introduce" EVIDENCE_DIR="$EVIDENCE_DIR" \
FRONTEND_URL="http://127.0.0.1:5176" \
DB_NAME="$DB_NAME" E2E_PASSWORD="$SC_DEMO_USER_PASSWORD" \
node "$ROOT_DIR/scripts/verify/local_dev_payment_settlement_component_journey.mjs" || introduce_status=$?

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
if not after["request"]["amount_uses_details"]:
    raise SystemExit("introduced detail did not become the authoritative amount source")
if round(after["request"]["amount"], 2) != round(after["request"]["detail_amount_total"], 2):
    raise SystemExit("request amount does not equal the authoritative detail total")
if after["request"]["detail_amount_total"] <= 0:
    raise SystemExit("introduced detail total must be positive")
print("[local.dev.payment.settlement-component] authoritative line and amount relationship created")
PY

remove_status=0
LOCAL_DEV_PAYMENT_SETTLEMENT_COMPONENT_JSON="$after" \
CANDIDATE_GIT_HEAD="$CANDIDATE_GIT_HEAD" JOURNEY_PHASE="remove" EVIDENCE_DIR="$EVIDENCE_DIR" \
FRONTEND_URL="http://127.0.0.1:5176" \
DB_NAME="$DB_NAME" E2E_PASSWORD="$SC_DEMO_USER_PASSWORD" \
node "$ROOT_DIR/scripts/verify/local_dev_payment_settlement_component_journey.mjs" || remove_status=$?

removed="$(resolve_target)"
BEFORE_JSON="$before" INTRODUCED_JSON="$after" REMOVED_JSON="$removed" python3 - <<'PY' || mutation_status=$?
import json
import os

before = json.loads(os.environ["BEFORE_JSON"])
introduced = json.loads(os.environ["INTRODUCED_JSON"])
removed = json.loads(os.environ["REMOVED_JSON"])
if removed["request"]["line_count"] != before["request"]["line_count"]:
    raise SystemExit("last-detail confirmation did not persist the removal")
if removed["request"]["settlement_line_count"] != before["request"]["settlement_line_count"]:
    raise SystemExit("last-detail confirmation left the settlement relationship behind")
if removed["request"]["amount_uses_details"]:
    raise SystemExit("request did not return to direct amount entry after removing all details")
if round(removed["request"]["amount"], 2) != round(introduced["request"]["amount"], 2):
    raise SystemExit("removing the last detail did not preserve the last authoritative total")
print("[local.dev.payment.settlement-component] cancel preserved the row; confirmation removed it and preserved amount")
PY

reset_status=0
ENV_FILE="$LOCAL_DEV_CANONICAL_ENV_FILE" \
  make -C "$ROOT_DIR" --no-print-directory local.dev.reset_payment_request_fixture || reset_status=$?
reset="$(resolve_target)"
BEFORE_JSON="$before" RESET_JSON="$reset" python3 - <<'PY' || reset_status=$?
import json
import os

before = json.loads(os.environ["BEFORE_JSON"])
reset = json.loads(os.environ["RESET_JSON"])
stable_fields = ("name", "state", "line_count", "settlement_line_count")
if any(reset["request"][field] != before["request"][field] for field in stable_fields):
    raise SystemExit("governed fixture reset did not restore payment settlement component baseline")
if round(reset["request"]["amount"], 2) != round(before["request"]["amount"], 2):
    raise SystemExit("governed fixture reset did not restore the baseline request amount")
print("[local.dev.payment.settlement-component] fixture reset restored baseline")
PY

(( introduce_status == 0 && remove_status == 0 && mutation_status == 0 && reset_status == 0 ))
