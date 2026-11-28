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
if [[ "${CONFIRM_LOCAL_CLEAN_FINANCE_FIXTURE:-}" != "PROVISION_LOCAL_CLEAN_FINANCE_ACCEPTANCE_FIXTURE" ]]; then
  echo "[DENY] confirmation required: CONFIRM_LOCAL_CLEAN_FINANCE_FIXTURE=PROVISION_LOCAL_CLEAN_FINANCE_ACCEPTANCE_FIXTURE" >&2
  exit 2
fi
if [[ -z "${SC_ACCEPTANCE_FIXTURE_PASSWORD:-}" ]]; then
  echo "[DENY] SC_ACCEPTANCE_FIXTURE_PASSWORD is required" >&2
  exit 24
fi

ODOO_SHELL_RUN_ISOLATED=1 DB_NAME="sc_clean" bash scripts/ops/odoo_shell_exec.sh <<'PY'
import json
import os
from pathlib import Path

from odoo.addons.smart_core.security import data_space_provisioning as provisioning

login = "fixture_role_finance"
password = os.environ["SC_ACCEPTANCE_FIXTURE_PASSWORD"]

company = env.ref("base.main_company", raise_if_not_found=False)
User = env["res.users"].sudo()
fixture_users = {}
user_specs = (
    (
        "fixture_role_business_config_admin",
        "验收业务配置管理员",
        "smart_construction_core.group_sc_role_business_admin",
    ),
    (
        login,
        "验收财务经办",
        "smart_construction_core.group_sc_role_finance_user",
    ),
    (
        "fixture_role_finance_reviewer",
        "验收财务复核",
        "smart_construction_core.group_sc_role_finance_user",
    ),
    (
        "fixture_role_project_manager",
        "验收项目负责人",
        "smart_construction_core.group_sc_role_project_manager",
    ),
    (
        "fixture_role_finance_manager",
        "验收财务审核",
        "smart_construction_core.group_sc_role_finance_manager",
    ),
    (
        "fixture_role_executive",
        "验收管理层",
        "smart_construction_core.group_sc_role_executive",
    ),
)
for fixture_login, fixture_name, role_group_xmlid in user_specs:
    role_group = env.ref(role_group_xmlid, raise_if_not_found=False)
    if not role_group:
        raise RuntimeError("missing %s" % role_group_xmlid)
    fixture_user = User.search([("login", "=", fixture_login)], limit=1)
    fixture_values = {
        "login": fixture_login,
        "name": fixture_name,
        "active": True,
        "password": password,
        "groups_id": [(6, 0, [env.ref("base.group_user").id, role_group.id])],
    }
    if company:
        fixture_values["company_id"] = company.id
        fixture_values["company_ids"] = [(6, 0, [company.id])]
    if fixture_user:
        fixture_user.write(fixture_values)
    else:
        fixture_user = User.create(fixture_values)
    fixture_users[fixture_login] = fixture_user

user = fixture_users[login]
project_manager_user = fixture_users["fixture_role_project_manager"]

# The clean profile is disposable test data. Register its main company through
# the same governed non-customer data-space entry used by the other local
# profiles instead of leaving every business identity outside the data realm.
environment_role = provisioning.environment_role(env)
if environment_role == "customer_production":
    provisioning.declare_environment_role(env, "industry_acceptance")
    environment_role = "industry_acceptance"
if environment_role != "industry_acceptance":
    raise RuntimeError(
        "local.clean fixture requires environment role industry_acceptance, got %s"
        % environment_role
    )
registration = provisioning.onboard_environment_business_company(
    env, tenant_key="sc-local-clean"
)
enrollment = provisioning.enroll_data_space_identities(env, purpose="test")

project = env["project.project"].sudo().search(
    [("name", "=", "验收付款项目"), ("company_id", "=", company.id)], limit=1
)
if not project:
    project = env["project.project"].sudo().create({
        "name": "验收付款项目",
        "company_id": company.id,
        "privacy_visibility": "followers",
    })
elif project.privacy_visibility != "followers":
    project.sudo().write({"privacy_visibility": "followers"})
project.sudo().write({
    "user_id": project_manager_user.id,
    "manager_id": project_manager_user.id,
})

partner = env["res.partner"].sudo().search(
    [("name", "=", "验收供应商"), ("company_id", "in", [False, company.id])], limit=1
)
if not partner:
    partner = env["res.partner"].sudo().create({
        "name": "验收供应商",
        "company_id": company.id,
        "supplier_rank": 1,
    })

business_category = env["sc.business.category"].sudo().search(
    [("code", "=", "finance.payment.apply.pay")], limit=1
)
if not business_category:
    raise RuntimeError("missing finance.payment.apply.pay business category")
payment_currency = env["res.currency"].sudo().search([("name", "=", "CNY")], limit=1)
if not payment_currency:
    raise RuntimeError("missing CNY payment currency")
if company.currency_id != payment_currency:
    company.sudo().write({"currency_id": payment_currency.id})

Tax = env["account.tax"].sudo()
tax = Tax.search([
    ("name", "=", "验收付款零税率"),
    ("company_id", "=", company.id),
], limit=1)
if not tax:
    tax = Tax.create({
        "name": "验收付款零税率",
        "amount": 0.0,
        "amount_type": "percent",
        "type_tax_use": "purchase",
        "price_include": False,
        "company_id": company.id,
    })

Contract = env["construction.contract"].sudo()
contract = Contract.search([
    ("subject", "=", "验收付款合同 CNY"),
    ("project_id", "=", project.id),
], limit=1)
if not contract:
    contract = Contract.create({
        "subject": "验收付款合同 CNY",
        "type": "in",
        "project_id": project.id,
        "partner_id": partner.id,
        "company_id": company.id,
        "currency_id": payment_currency.id,
        "tax_id": tax.id,
    })

Settlement = env["sc.settlement.order"].sudo()
settlement = Settlement.search([
    ("title", "=", "验收付款结算单 CNY"),
    ("project_id", "=", project.id),
], limit=1)
if not settlement:
    settlement = Settlement.create({
        "title": "验收付款结算单 CNY",
        "project_id": project.id,
        "partner_id": partner.id,
        "contract_id": contract.id,
        "settlement_type": "out",
        "company_id": company.id,
        "currency_id": payment_currency.id,
        "line_ids": [(0, 0, {
            "name": "验收付款结算明细",
            "contract_id": contract.id,
            "qty": 1.0,
            "price_unit": 200.0,
        })],
    })
if settlement.state != "approve":
    settlement._write_lifecycle("approve")

Assignment = env["sc.project.member.assignment"].sudo().with_context(active_test=False)
assignments = {}
for fixture_login, fixture_user in fixture_users.items():
    assignment = Assignment.search([
        ("project_id", "=", project.id),
        ("user_id", "=", fixture_user.id),
    ], limit=1)
    if not assignment:
        # A direct follower is not the product's project-member authority. The
        # formal assignment owns and recreates it so the acceptance fixture uses
        # the same audited path as the personnel permission surface.
        project.message_unsubscribe(partner_ids=[fixture_user.partner_id.id])
        assignment = Assignment.create({
            "project_id": project.id,
            "user_id": fixture_user.id,
            "active": True,
            "source": "manual",
            "note": "local.clean acceptance fixture: %s" % fixture_login,
        })
    elif not assignment.active or not assignment.sc_follower_owned:
        if assignment.active:
            assignment.write({"active": False})
        project.message_unsubscribe(partner_ids=[fixture_user.partner_id.id])
        assignment.write({
            "active": True,
            "source": "manual",
            "note": "local.clean acceptance fixture: %s" % fixture_login,
        })
    if not assignment.sc_follower_owned:
        raise RuntimeError(
            "formal project membership did not own its follower for %s" % fixture_login
        )
    assignments[fixture_login] = assignment

assignment = assignments[login]
env.cr.commit()
env.registry.clear_cache()

user_id = user.id
uid = env["res.users"].sudo().authenticate(env.cr.dbname, login, password, {"interactive": True})
if int(uid or 0) != user_id:
    raise RuntimeError("finance fixture credential verification failed")

user_env = env(
    user=user_id,
    context={**env.context, "allowed_company_ids": [company.id]},
)
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

payment_probe = {"ok": False}
try:
    with env.cr.savepoint():
        payment = user_env["payment.request"].create({
            "project_id": project.id,
            "partner_id": partner.id,
            "business_category_id": business_category.id,
            "date_request": "2026-11-28",
            "amount": 123.45,
            "currency_id": payment_currency.id,
        })
        payment_probe = {
            "ok": True,
            "id": payment.id,
            "project_id": payment.project_id.id,
            "partner_id": payment.partner_id.id,
            "business_category_id": payment.business_category_id.id,
            "amount": payment.amount,
        }
        raise RuntimeError("rollback fixture access probe")
except RuntimeError as error:
    if str(error) != "rollback fixture access probe":
        raise
except Exception as error:
    payment_probe = {
        "ok": False,
        "type": type(error).__name__,
        "message": str(error),
    }

env.cr.execute(
    "SELECT count(*) FROM ui_business_config_contract "
    "WHERE contract_json->'view_orchestration'->'context'->>'source' LIKE 'smart_core.lowcode.%'"
)
lowcode_seed_count = env.cr.fetchone()[0]

payload = {
    "db": env.cr.dbname,
    "login": login,
    "uid": user_id,
    "role_groups": [g.name for g in user.groups_id],
    "environment_role": provisioning.environment_role(env),
    "data_space": {
        "registration_id": registration.id,
        "tenant_key": registration.tenant_key,
        "data_purpose": registration.data_purpose,
        "company_id": registration.company_id.id,
        "operator_pending_enrollment": provisioning.data_space_operators_pending_enrollment(
            env, purpose="test"
        ),
        "enrollment": enrollment,
        "finance_sc_data_company_ids": user_env.user._sc_data_company_ids(),
    },
    "project": {
        "id": project.id,
        "name": project.name,
        "display_name": project.display_name,
        "privacy_visibility": project.privacy_visibility,
        "project_manager_login": project_manager_user.login,
        "assignment_id": assignment.id,
        "assignment_source": assignment.source,
        "assignment_follower_owned": assignment.sc_follower_owned,
        "finance_is_follower": user.partner_id in project.message_partner_ids,
    },
    "company": {
        "id": company.id,
        "name": company.display_name,
        "currency_id": payment_currency.id,
        "currency_code": payment_currency.name,
    },
    "partner": {
        "id": partner.id,
        "name": partner.name,
        "display_name": partner.display_name,
    },
    "business_category": {
        "id": business_category.id,
        "name": business_category.name,
        "display_name": business_category.display_name,
    },
    "approval_principals": {
        fixture_login: {
            "uid": fixture_user.id,
            "role_groups": [
                group.name
                for group in fixture_user.groups_id
                if group.name.startswith("SC 角色")
            ],
            "project_assignment_id": assignments[fixture_login].id,
        }
        for fixture_login, fixture_user in fixture_users.items()
    },
    "partner_id": partner.id,
    "business_category_id": business_category.id,
    "payment_basis": {
        "tax_id": tax.id,
        "currency_id": payment_currency.id,
        "currency_code": payment_currency.name,
        "contract_id": contract.id,
        "contract_name": contract.display_name,
        "contract_state": contract.state,
        "contract_currency_id": contract.currency_id.id,
        "contract_currency_code": contract.currency_id.name,
        "settlement_id": settlement.id,
        "settlement_name": settlement.display_name,
        "settlement_state": settlement.state,
        "settlement_currency_id": settlement.currency_id.id,
        "settlement_currency_code": settlement.currency_id.name,
    },
    "payment_create_probe": payment_probe,
    "model_access": model_access,
    "action_count": action_counts,
    "lowcode_seed_count": lowcode_seed_count,
}
receipt_path = os.environ.get("SC_ACCEPTANCE_FINANCE_FIXTURE_RECEIPT", "").strip()
if receipt_path:
    receipt = Path(receipt_path)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
print(json.dumps(payload, ensure_ascii=False, indent=2))
PY
