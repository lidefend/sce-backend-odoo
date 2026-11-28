#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
export ROOT_DIR

source "$ROOT_DIR/scripts/common/env.sh"
source "$ROOT_DIR/scripts/common/guard_prod.sh"
guard_prod_forbid

EXPECTED_HEAD="${EXPECTED_HEAD:-${SC_SOURCE_REVISION:-}}"
if [[ ! "$EXPECTED_HEAD" =~ ^[0-9a-f]{40}$ ]]; then
  echo "[DENY] EXPECTED_HEAD must be the complete 40-character candidate SHA" >&2
  exit 2
fi
if [[ "${ENV:-}" != "dev" || "${DB_NAME:-}" != "sc_clean" || "${ISOLATED_REHEARSAL_DATABASE:-0}" != "1" ]]; then
  echo "[DENY] finance E2E requires the registered local.clean dev/profile" >&2
  exit 3
fi
if [[ "${CONFIRM_LOCAL_CLEAN_FINANCE_E2E:-}" != "RUN_LOCAL_CLEAN_FINANCE_E2E" ]]; then
  echo "[DENY] confirmation required: CONFIRM_LOCAL_CLEAN_FINANCE_E2E=RUN_LOCAL_CLEAN_FINANCE_E2E" >&2
  exit 2
fi
if [[ -z "${SC_ACCEPTANCE_FIXTURE_PASSWORD:-}" ]]; then
  echo "[DENY] SC_ACCEPTANCE_FIXTURE_PASSWORD is required" >&2
  exit 24
fi

ACCEPTANCE_BASE_URL="${SC_ACCEPTANCE_FRONTEND_URL:-http://127.0.0.1:18083/t/clean}"
EVIDENCE_ROOT="${SC_ACCEPTANCE_OUTPUT_ROOT:-$ROOT_DIR/.runtime/agent-runs/FE-CONSUMPTION-CLOSEOUT-20261126/local-clean-finance-e2e}"
FINANCE_FIXTURE_RECEIPT="$EVIDENCE_ROOT/finance-fixture.json"
mkdir -p "$EVIDENCE_ROOT"

echo "[finance.e2e] 1/8 rebuild disposable clean installation"
make --no-print-directory local.clean.rebuild \
  CONFIRM_LOCAL_CLEAN_REBUILD=REBUILD_ISOLATED_REHEARSAL \
  SC_SOURCE_REVISION="$EXPECTED_HEAD"

echo "[finance.e2e] 2/8 build and bind the exact candidate frontend"
make --no-print-directory local.clean.frontend SC_SOURCE_REVISION="$EXPECTED_HEAD"
FRONTEND_BUILD_SHA256="$(cat "$ROOT_DIR/frontend/apps/web/dist-clean/.build-sha256")"
make --no-print-directory local.clean.up \
  SC_SOURCE_REVISION="$EXPECTED_HEAD" \
  FRONTEND_BUILD_SHA256="$FRONTEND_BUILD_SHA256"
make --no-print-directory local.clean.entry_identity.ensure
make --no-print-directory local.clean.entry_identity.verify

echo "[finance.e2e] 3/8 provision enterprise, role, project and payment-basis fixtures"
make --no-print-directory local.clean.finance_fixture.ensure \
  CONFIRM_LOCAL_CLEAN_FINANCE_FIXTURE=PROVISION_LOCAL_CLEAN_FINANCE_ACCEPTANCE_FIXTURE \
  SC_ACCEPTANCE_FINANCE_FIXTURE_RECEIPT="$FINANCE_FIXTURE_RECEIPT"
if [[ ! -s "$FINANCE_FIXTURE_RECEIPT" ]]; then
  echo "[finance.e2e] fixture receipt was not produced: $FINANCE_FIXTURE_RECEIPT" >&2
  exit 5
fi
COMPANY_ID="$(
  node -e 'const fs=require("fs");const d=JSON.parse(fs.readFileSync(process.argv[1],"utf8"));process.stdout.write(String(d.company?.id||0));' \
    "$FINANCE_FIXTURE_RECEIPT"
)"
if [[ ! "$COMPANY_ID" =~ ^[1-9][0-9]*$ ]]; then
  echo "[finance.e2e] fixture receipt has no exact company id" >&2
  exit 5
fi
make --no-print-directory local.clean.restart \
  SC_SOURCE_REVISION="$EXPECTED_HEAD" \
  FRONTEND_BUILD_SHA256="$FRONTEND_BUILD_SHA256"
make --no-print-directory local.clean.entry_identity.verify

COMMON_ENV=(
  "SC_ACCEPTANCE_FRONTEND_URL=$ACCEPTANCE_BASE_URL"
  "SC_ACCEPTANCE_TARGET_SHA=$EXPECTED_HEAD"
  "SC_ACCEPTANCE_BUILD_SHA256=$FRONTEND_BUILD_SHA256"
  "SC_ACCEPTANCE_COMPANY_ID=$COMPANY_ID"
  "SC_ACCEPTANCE_FINANCE_FIXTURE=$FINANCE_FIXTURE_RECEIPT"
  "ACCEPTANCE_PASSWORD=$SC_ACCEPTANCE_FIXTURE_PASSWORD"
)

echo "[finance.e2e] 4/8 initialize the enterprise through the product page"
env "${COMMON_ENV[@]}" \
  CONFIGURATION_ADMIN_LOGIN=fixture_role_business_config_admin \
  SC_ACCEPTANCE_OUTPUT_DIR="$EVIDENCE_ROOT/enterprise-setup" \
  node scripts/dev/local_clean_enterprise_setup_probe.mjs

echo "[finance.e2e] 5/8 grant the finance operator the existing data-read capability"
env "${COMMON_ENV[@]}" \
  CONFIGURATION_ADMIN_LOGIN=fixture_role_business_config_admin \
  FINANCE_LOGIN=fixture_role_finance \
  SC_ACCEPTANCE_OUTPUT_DIR="$EVIDENCE_ROOT/data-permission" \
  node scripts/dev/local_clean_finance_data_permission_probe.mjs

echo "[finance.e2e] 6/8 define the payment approval chain through the product page"
env "${COMMON_ENV[@]}" \
  CONFIGURATION_ADMIN_LOGIN=fixture_role_business_config_admin \
  SC_ACCEPTANCE_OUTPUT_DIR="$EVIDENCE_ROOT/approval-configuration" \
  node scripts/dev/local_clean_finance_approval_configure_probe.mjs

echo "[finance.e2e] 7/8 create, save, reopen and submit the payment request"
env "${COMMON_ENV[@]}" \
  SC_ACCEPTANCE_DATABASE=sc_clean \
  ACCEPTANCE_LOGIN=fixture_role_finance \
  SC_ACCEPTANCE_OUTPUT_DIR="$EVIDENCE_ROOT/payment-journey" \
  node scripts/dev/local_clean_finance_payment_journey_probe.mjs

RECORD_ID="$(
  node -e 'const fs=require("fs");const p=process.argv[1];const d=JSON.parse(fs.readFileSync(p,"utf8"));process.stdout.write(String(d.readback?.after_submit?.id||0));' \
    "$EVIDENCE_ROOT/payment-journey/receipt.json"
)"
if [[ ! "$RECORD_ID" =~ ^[1-9][0-9]*$ ]]; then
  echo "[finance.e2e] payment journey did not produce an exact request id" >&2
  exit 4
fi

echo "[finance.e2e] 8/8 approve through finance, project, finance review and executive roles"
env "${COMMON_ENV[@]}" \
  PAYMENT_REQUEST_ID="$RECORD_ID" \
  SC_ACCEPTANCE_OUTPUT_DIR="$EVIDENCE_ROOT/approval-journey" \
  node scripts/dev/local_clean_finance_approval_journey_probe.mjs

echo "[finance.e2e] PASS head=$EXPECTED_HEAD build=$FRONTEND_BUILD_SHA256 request_id=$RECORD_ID"
echo "[finance.e2e] evidence=$EVIDENCE_ROOT"
