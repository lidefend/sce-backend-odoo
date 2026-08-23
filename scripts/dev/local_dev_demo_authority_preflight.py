"""Fail-closed semantic readiness check for a governed demo database."""

from odoo.exceptions import UserError


def require(condition, message):
    if not condition:
        raise UserError(message)


demo_module = env["ir.module.module"].sudo().search(  # noqa: F821
    [("name", "=", "smart_construction_demo")], limit=1
)
require(
    demo_module and demo_module.state == "installed",
    "DEMO_AUTHORITY_MODULE_MISSING: smart_construction_demo is not installed",
)

finance_user = env.ref(  # noqa: F821
    "smart_construction_demo.user_demo_role_finance", raise_if_not_found=False
)
require(
    finance_user and finance_user._name == "res.users" and finance_user.exists(),
    "DEMO_AUTHORITY_FINANCE_ROLE_XMLID_MISSING",
)
require(
    finance_user.active and finance_user.login == "demo_role_finance",
    "DEMO_AUTHORITY_FINANCE_ROLE_IDENTITY_INVALID",
)
finance_group = env.ref(  # noqa: F821
    "smart_construction_core.group_sc_role_finance_manager",
    raise_if_not_found=False,
)
require(
    finance_group and finance_group._name == "res.groups" and finance_group.exists(),
    "DEMO_AUTHORITY_FINANCE_GROUP_XMLID_MISSING",
)
require(
    finance_group in finance_user.groups_id,
    "DEMO_AUTHORITY_FINANCE_ROLE_MEMBERSHIP_MISSING",
)

company = env.ref("base.main_company")  # noqa: F821
cny = env.ref("base.CNY", raise_if_not_found=False)  # noqa: F821
require(cny and company.currency_id == cny, "DEMO_AUTHORITY_COMPANY_CNY_MISSING")
sale_tax = (
    env["account.tax"]  # noqa: F821
    .sudo()
    .with_company(company)
    .with_context(active_test=False, allowed_company_ids=[company.id])
    .search(
        [
            ("company_id", "=", company.id),
            ("type_tax_use", "=", "sale"),
            ("amount_type", "=", "percent"),
            ("amount", "=", 9.0),
        ],
        limit=1,
    )
)
require(sale_tax, "DEMO_AUTHORITY_SALE_TAX_9_MISSING")

print(
    "[local.dev.demo.authority] PASS "
    f"db={env.cr.dbname} module=installed finance_xmlid=present "  # noqa: F821
    "finance_membership=authoritative "
    "company_currency=CNY sale_tax_9=present"
)
