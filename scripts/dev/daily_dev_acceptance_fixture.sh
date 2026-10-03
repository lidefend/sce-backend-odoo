#!/usr/bin/env bash
# Governed daily-development acceptance fixture entry.
#
# The daily runtime database is an existing declared profile the owner approved
# to carry the same deterministic fixture as the isolated acceptance runtime, so
# the daily readonly probe can produce an exact-instance backend contract
# receipt from the runtime it actually measures. This entry never relaxes the
# isolated acceptance scope: it declares the daily_dev scope explicitly and the
# fixture builder itself still fails closed on any other database, environment
# or scope name.
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
export ROOT_DIR

source "$ROOT_DIR/scripts/common/env.sh"
source "$ROOT_DIR/scripts/common/guard_prod.sh"
guard_prod_forbid

DAILY_DEV_ACCEPTANCE_DB="${DAILY_DEV_ACCEPTANCE_DB:-sc_demo}"

if [[ "${DB_NAME:-}" != "$DAILY_DEV_ACCEPTANCE_DB" ]]; then
  echo "[DENY] daily dev acceptance fixture requires DB_NAME=${DAILY_DEV_ACCEPTANCE_DB} (got ${DB_NAME:-<empty>})" >&2
  exit 24
fi
if [[ -z "${SC_ACCEPTANCE_FIXTURE_PASSWORD:-}" ]]; then
  echo "[DENY] daily dev acceptance fixture requires SC_ACCEPTANCE_FIXTURE_PASSWORD" >&2
  exit 25
fi

export DB_NAME SC_ACCEPTANCE_FIXTURE_PASSWORD
export SC_ENVIRONMENT=dev
export SC_ALLOW_DEMO_DATA=1
export SC_ACCEPTANCE_FIXTURE_SCOPE=daily_dev
export ODOO_SHELL_RUN_ISOLATED="${ODOO_SHELL_RUN_ISOLATED:-1}"

DB_NAME="$DB_NAME" bash "$ROOT_DIR/scripts/ops/odoo_shell_exec.sh" <<'PY'
import json
import os

from odoo.addons.smart_construction_acceptance_fixture.tools.frontend_productization_fixture import (
    ensure_fixture,
)

MODULE = "smart_construction_acceptance_fixture"
REQUIRED_XMLIDS = (
    "smart_construction_acceptance_fixture.fe_project_a",
    "smart_construction_acceptance_fixture.fe_general_contract_a",
    "smart_construction_acceptance_fixture.fe_settlement_a",
    "smart_construction_acceptance_fixture.fe_delivery_hardening_payment_request_a",
    "smart_construction_acceptance_fixture.fe_request_c_001",
    "smart_construction_acceptance_fixture.fe_execution_a",
    "smart_construction_acceptance_fixture.fe_b05_work_settlement_a",
    "smart_construction_acceptance_fixture.fe_company_a",
    "smart_construction_acceptance_fixture.fe_company_b",
    "smart_construction_acceptance_fixture.fe_user_finance",
)

summary = ensure_fixture(env)

carrier = env["ir.module.module"].sudo().search([("name", "=", MODULE)], limit=1)
if not carrier or carrier.state != "installed":
    raise RuntimeError("daily acceptance fixture carrier is not installed")

missing = [xmlid for xmlid in REQUIRED_XMLIDS if not env.ref(xmlid, raise_if_not_found=False)]
if missing:
    raise RuntimeError("daily acceptance fixture missing xmlids: %s" % ",".join(missing))

finance = env.ref("smart_construction_acceptance_fixture.fe_user_finance")
authenticated_uid = env["res.users"].sudo().authenticate(
    env.cr.dbname,
    finance.login,
    os.environ["SC_ACCEPTANCE_FIXTURE_PASSWORD"],
    {"interactive": True},
)
if int(authenticated_uid or 0) != finance.id:
    raise RuntimeError("daily acceptance fixture credential verification failed")
env.cr.commit()

print("[daily.dev.acceptance_fixture] PASS db=%s" % env.cr.dbname)
print("[daily.dev.acceptance_fixture.auth] PASS login=%s uid=%s" % (finance.login, authenticated_uid))
print(
    "DAILY_DEV_ACCEPTANCE_FIXTURE_JSON="
    + json.dumps(
        {
            "database": env.cr.dbname,
            "carrier": carrier.state,
            "finance_login": finance.login,
            "finance_uid": int(finance.id),
            "http_uid": int(authenticated_uid or 0),
            "company_name": finance.company_id.name,
            "xmlids": list(REQUIRED_XMLIDS),
            "summary_keys": sorted(summary.keys()) if isinstance(summary, dict) else [],
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
)
PY
