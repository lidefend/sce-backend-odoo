#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
export ROOT_DIR
source "$ROOT_DIR/scripts/common/env.sh"

# The fingerprint protects a provisioned demo DB. Resolution order is:
#   1) explicit FRONTEND_FIXTURE_GUARD_DB override
#   2) the governed profile's DB_NAME (make verify.frontend.fixture.guard runs
#      under $(RUN_ENV), so the registered local.dev profile binds sc_dev_demo)
#   3) the legacy sc_demo default
# An unbound/empty/unprovisioned DB fails closed with an explicit DENY instead
# of an opaque KeyError, and no assertion is relaxed.
GUARD_DB="${FRONTEND_FIXTURE_GUARD_DB:-${DB_NAME:-sc_demo}}"

fingerprint() {
  DB_NAME="$GUARD_DB" bash scripts/ops/odoo_shell_exec.sh \
    < scripts/verify/frontend_productization_history_fingerprint.py \
    | grep '^FRONTEND_HISTORY_FINGERPRINT=' | tail -1
}

deny_unbound_db() {
  echo "[DENY] verify.frontend.fixture.guard needs a provisioned demo DB to fingerprint (resolved DB_NAME=${GUARD_DB})" >&2
  echo "[DENY] run under the registered profile (make verify.frontend.fixture.guard binds its demo DB; local.dev: sc_dev_demo) or set FRONTEND_FIXTURE_GUARD_DB=<demo DB>; the DB must have project and the smart_construction_* models installed" >&2
}

if ! before="$(fingerprint 2>/tmp/frontend-fixture-guard-before.log)"; then
  deny_unbound_db
  tail -5 /tmp/frontend-fixture-guard-before.log >&2
  exit 2
fi
for denied_db in sc_demo postgres arbitrary_database ""; do
  set +e
  # The deny ring must exercise the entry that actually consumes DB_NAME and
  # fails closed: scripts/verify/frontend_productization_fixture.sh sources
  # scripts/common/frontend_acceptance_guard.sh and calls
  # guard_frontend_acceptance_scope (rc=20) before any DB access. The previous
  # `make acceptance.frontend.fixture` entry ignores DB_NAME and never produced
  # this DENY, so the ring could not prove the guard.
  DB_NAME="$denied_db" SC_ENVIRONMENT=acceptance SC_ALLOW_DEMO_DATA=1 \
    bash scripts/verify/frontend_productization_fixture.sh >/tmp/frontend-fixture-deny.log 2>&1
  status=$?
  set -e
  if [[ $status -eq 0 ]]; then
    cat /tmp/frontend-fixture-deny.log >&2
    echo "[verify.frontend.fixture.guard] FAIL accepted DB_NAME=${denied_db:-<empty>}" >&2
    exit 2
  fi
  if ! grep -q '^\[DENY\] frontend acceptance fixture requires DB_NAME=sc_frontend_acceptance' /tmp/frontend-fixture-deny.log; then
    cat /tmp/frontend-fixture-deny.log >&2
    echo "[verify.frontend.fixture.guard] FAIL database guard did not fail first" >&2
    exit 2
  fi
  echo "[verify.frontend.fixture.guard] denied DB_NAME=${denied_db:-<empty>} exit=${status}"
done
if ! after="$(fingerprint 2>/tmp/frontend-fixture-guard-after.log)"; then
  deny_unbound_db
  tail -5 /tmp/frontend-fixture-guard-after.log >&2
  exit 2
fi
if [[ "$before" != "$after" ]]; then
  echo "[verify.frontend.fixture.guard] FAIL ${GUARD_DB} fingerprint changed" >&2
  echo "before: $before" >&2
  echo "after:  $after" >&2
  exit 2
fi
echo "[verify.frontend.fixture.guard] PASS ${GUARD_DB} fingerprint unchanged"
echo "$after"
