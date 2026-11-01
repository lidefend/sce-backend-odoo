#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
export ROOT_DIR

source "$ROOT_DIR/scripts/common/env.sh"
source "$ROOT_DIR/scripts/common/guard_prod.sh"
guard_prod_forbid

if [[ "${ENV:-}" != "dev" ]]; then
  echo "[DENY] local.clean finance fixture requires ENV=dev (got ${ENV:-})" >&2
  exit 3
fi
if [[ "${DB_NAME:-}" != "sc_clean" ]]; then
  echo "[DENY] local.clean finance fixture requires DB_NAME=sc_clean (got ${DB_NAME:-})" >&2
  exit 3
fi
if [[ "${ISOLATED_REHEARSAL_DATABASE:-0}" != "1" ]]; then
  echo "[DENY] local.clean finance fixture requires the isolated rehearsal database" >&2
  exit 3
fi
if [[ "${CONFIRM_LOCAL_CLEAN_FINANCE_FIXTURE:-}" != "CREATE_FINANCE_ROLE_USER_ONLY" ]]; then
  echo "[DENY] confirmation required: CONFIRM_LOCAL_CLEAN_FINANCE_FIXTURE=CREATE_FINANCE_ROLE_USER_ONLY" >&2
  exit 2
fi
if [[ -z "${SC_ACCEPTANCE_FIXTURE_PASSWORD:-}" ]]; then
  echo "[DENY] SC_ACCEPTANCE_FIXTURE_PASSWORD is required" >&2
  exit 24
fi

ODOO_SHELL_RUN_ISOLATED=1 DB_NAME="sc_clean" bash scripts/ops/odoo_shell_exec.sh <<'PY'
import json
import os

login = "fixture_role_finance"
password = os.environ["SC_ACCEPTANCE_FIXTURE_PASSWORD"]

role_group = env.ref("smart_construction_core.group_sc_role_finance_manager", raise_if_not_found=False)
if not role_group:
    raise RuntimeError("missing smart_construction_core.group_sc_role_finance_manager")

company = env.ref("base.main_company", raise_if_not_found=False)
User = env["res.users"].sudo()
user = User.search([("login", "=", login)], limit=1)
values = {
    "login": login,
    "name": "Fresh-install Finance Fixture",
    "active": True,
    "password": password,
    "groups_id": [(6, 0, [env.ref("base.group_user").id, role_group.id])],
}
if company:
    values["company_id"] = company.id
    values["company_ids"] = [(6, 0, [company.id])]
if user:
    user.write(values)
else:
    user = User.create(values)
env.cr.commit()

user_id = user.id
uid = env["res.users"].sudo().authenticate(env.cr.dbname, login, password, {"interactive": True})
if int(uid or 0) != user_id:
    raise RuntimeError("finance fixture credential verification failed")

user_env = env(user=user_id)
model_access = {}
action_counts = {}
for model_name in ("payment.request", "sc.payment.execution", "sc.receipt.income"):
    Model = user_env.get(model_name)
    model_access[model_name] = {
        "read": bool(Model.check_access_rights("read", raise_exception=False)) if Model is not None else False,
        "create": bool(Model.check_access_rights("create", raise_exception=False)) if Model is not None else False,
    }
    action_counts[model_name] = env["ir.actions.act_window"].sudo().search_count(
        [("res_model", "=", model_name)]
    )

env.cr.execute(
    "SELECT count(*) FROM ui_business_config_contract "
    "WHERE contract_json->'view_orchestration'->'context'->>'source' LIKE 'smart_core.lowcode.%'"
)
lowcode_seed_count = env.cr.fetchone()[0]

print(json.dumps({
    "db": env.cr.dbname,
    "login": login,
    "uid": user_id,
    "role_groups": [g.name for g in user.groups_id],
    "model_access": model_access,
    "action_count": action_counts,
    "lowcode_seed_count": lowcode_seed_count,
}, ensure_ascii=False, indent=2))
PY
