"""Verify the persistent development database has no Odoo demo carrier."""

from odoo.exceptions import UserError


def require(condition, message):
    if not condition:
        raise UserError(message)


for module_name in ("smart_core", "smart_construction_core", "smart_construction_seed", "smart_construction_portal"):
    module = env["ir.module.module"].sudo().search([("name", "=", module_name)], limit=1)  # noqa: F821
    require(module and module.state == "installed", f"REALISTIC_DEV_PRODUCT_MODULE_MISSING: {module_name}")

demo = env["ir.module.module"].sudo().search([("name", "=", "smart_construction_demo")], limit=1)  # noqa: F821
require(not demo or demo.state != "installed", "REALISTIC_DEV_DEMO_CARRIER_INSTALLED")

print(f"[local.dev.realistic.authority] PASS db={env.cr.dbname} odoo_demo=0 demo_carrier=absent")  # noqa: F821
