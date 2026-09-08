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
[[ -n "${SOURCE_SHA:-}" ]] || { echo "SOURCE_SHA is required" >&2; exit 2; }
[[ -n "${CANDIDATE_FINGERPRINT:-}" ]] || { echo "CANDIDATE_FINGERPRINT is required" >&2; exit 2; }

restore_needed=0
restore_on_exit() {
  local status=$?
  if (( restore_needed == 1 )); then
    echo "[local.dev.payment.full-chain] preparing the next owned fixture after interrupted journey" >&2
    ENV_FILE="$LOCAL_DEV_CANONICAL_ENV_FILE" make -C "$ROOT_DIR" --no-print-directory local.dev.reset_payment_request_fixture || true
  fi
  exit "$status"
}
trap restore_on_exit EXIT

resolve_target() {
  DB_NAME="$DB_NAME" bash "$ROOT_DIR/scripts/ops/odoo_shell_exec.sh" \
    < "$ROOT_DIR/scripts/verify/local_dev_payment_request_native_parity_ids.py" \
    | sed -n 's/^LOCAL_DEV_PAYMENT_PARITY_JSON=//p' | tail -1
}
resolve_facts() {
  DB_NAME="$DB_NAME" bash "$ROOT_DIR/scripts/ops/odoo_shell_exec.sh" \
    < "$ROOT_DIR/scripts/verify/local_dev_payment_request_full_chain_facts.py" \
    | sed -n 's/^LOCAL_DEV_PAYMENT_FULL_CHAIN_FACTS_JSON=//p' | tail -1
}
resolve_approval_chain() {
  DB_NAME="$DB_NAME" bash "$ROOT_DIR/scripts/ops/odoo_shell_exec.sh" \
    < "$ROOT_DIR/scripts/verify/local_dev_payment_request_approval_chain.py" \
    | sed -n 's/^LOCAL_DEV_PAYMENT_APPROVAL_CHAIN_JSON=//p' | tail -1
}

ENV_FILE="$LOCAL_DEV_CANONICAL_ENV_FILE" make -C "$ROOT_DIR" --no-print-directory local.dev.reset_payment_request_fixture
before="$(resolve_target)"
[[ -n "$before" ]] || { echo "payment full-chain target resolution failed" >&2; exit 1; }
restore_needed=1

browser_status=0
LOCAL_DEV_PAYMENT_FLOORPLAN_JSON="$before" \
FRONTEND_URL="http://127.0.0.1:${NGINX_PORT}" DB_NAME="$DB_NAME" \
E2E_PASSWORD="$SC_DEMO_USER_PASSWORD" PAYMENT_REQUEST_JOURNEY_SCOPE=payment \
node "$ROOT_DIR/scripts/verify/local_dev_payment_request_floorplan_submit.mjs" || browser_status=$?

if (( browser_status == 0 )); then
  approval_chain="$(resolve_approval_chain)"
  [[ -n "$approval_chain" ]] || { echo "configured payment approval chain resolution failed" >&2; browser_status=1; }
fi

if (( browser_status == 0 )); then
  LOCAL_DEV_PAYMENT_FLOORPLAN_JSON="$before" \
  LOCAL_DEV_PAYMENT_APPROVAL_CHAIN_JSON="$approval_chain" \
  FRONTEND_URL="http://127.0.0.1:${NGINX_PORT}" DB_NAME="$DB_NAME" \
  E2E_PASSWORD="$SC_DEMO_USER_PASSWORD" SOURCE_SHA="$SOURCE_SHA" \
  CANDIDATE_FINGERPRINT="$CANDIDATE_FINGERPRINT" \
  node "$ROOT_DIR/scripts/verify/local_dev_payment_request_full_chain.mjs" || browser_status=$?
fi

facts="$(resolve_facts)"
facts_status=0
FULL_CHAIN_FACTS="$facts" python3 - <<'PY' || facts_status=$?
import json
import os

facts = json.loads(os.environ["FULL_CHAIN_FACTS"])
request = facts["request"]
executions = facts["executions"]
posted = [row for row in facts["ledgers"] if row["state"] == "posted"]
if request["state"] != "done" or request["paid_amount_total"] != 10000.0 or request["unpaid_amount"] != 0.0:
    raise SystemExit("payment request final facts do not reconcile")
if len(executions) != 1 or executions[0]["state"] != "paid" or executions[0]["paid_amount"] != 10000.0:
    raise SystemExit("payment execution final facts do not reconcile")
if len(posted) != 1 or posted[0]["amount"] != 10000.0:
    raise SystemExit("payment ledger final facts do not reconcile")
print("[local.dev.payment.full-chain] authoritative request/execution/ledger facts reconciled")
PY

if (( browser_status == 0 && facts_status == 0 )); then
  restore_needed=0
  echo "[local.dev.payment.full-chain] completed payment facts retained as immutable acceptance history"
  exit 0
fi
exit 1
