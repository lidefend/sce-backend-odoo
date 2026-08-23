"""Reconcile governed P1 prerequisites after fresh accounting bootstrap."""

from odoo.addons.smart_construction_core.hooks import ensure_core_taxes


ensure_core_taxes(env)  # noqa: F821
env["res.company"]._sc_ensure_cny_currency()  # noqa: F821

company = env.ref("base.main_company")  # noqa: F821
cny = env.ref("base.CNY", raise_if_not_found=False)  # noqa: F821
if not cny or company.currency_id != cny:
    raise RuntimeError("LOCAL_DEMO_PRODUCT_BASELINE_CNY_MISSING")

required = (
    env["account.tax"]  # noqa: F821
    .sudo()
    .with_company(company)
    .with_context(active_test=False, allowed_company_ids=[company.id])
    .search_count(
        [
            ("company_id", "=", company.id),
            ("type_tax_use", "in", ["sale", "purchase"]),
            ("amount_type", "=", "percent"),
            ("amount", "in", [9.0, 13.0]),
        ]
    )
)
if required < 2:
    raise RuntimeError("LOCAL_DEMO_PRODUCT_BASELINE_TAX_MISSING")

# Odoo shell does not provide the module-loader transaction boundary used by
# install hooks.  Persist only after all P1 postconditions have passed; any
# earlier exception leaves the transaction rollback-safe.
env.cr.commit()  # noqa: F821

print(
    "[local.dev.demo.product-baseline] PASS "
    f"db={env.cr.dbname} company_currency=CNY required_taxes={required}"  # noqa: F821
)
