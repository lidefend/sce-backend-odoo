from __future__ import annotations

import json
import os

from odoo.exceptions import UserError


def required(name):
    value = str(os.environ.get(name, "") or "").strip()
    if not value:
        raise UserError(f"MAINTENANCE_ENV_REQUIRED:{name}")
    return value


database = env.cr.dbname
tenant = required("SC_TENANT_PAYLOAD_TENANT_KEY")
customer_modules = tuple(
    item.strip()
    for item in required("SC_PRODUCTION_CUSTOMER_MODULES").split(",")
    if item.strip()
)
if database != "sc_production":
    raise UserError("MAINTENANCE_DATABASE_MISMATCH")
if env["ir.config_parameter"].sudo().get_param("smart_core.platform_release_db") != database:
    raise UserError("MAINTENANCE_PLATFORM_DATABASE_MISMATCH")
if env["ir.config_parameter"].sudo().get_param("sc.tenant.bound_tenant_key") != tenant:
    raise UserError("MAINTENANCE_TENANT_MISMATCH")
customer = env["ir.module.module"].sudo().search([("name", "in", list(customer_modules))])
if (
    not customer_modules
    or len(customer) != len(customer_modules)
    or set(customer.mapped("name")) != set(customer_modules)
    or any(state != "installed" for state in customer.mapped("state"))
):
    raise UserError("MAINTENANCE_CUSTOMER_MODULE_CONTRACT_MISMATCH")
snapshot = env["sc.edition.release.snapshot"].sudo().search(
    [
        ("product_key", "=", "construction.standard"),
        ("state", "=", "released"),
        ("is_active", "=", True),
        ("active", "=", True),
    ]
)
if len(snapshot) != 1:
    raise UserError("MAINTENANCE_PLATFORM_SNAPSHOT_MISMATCH")
print(json.dumps({
    "status": "PASS",
    "database": database,
    "tenant_key": tenant,
    "customer_module_count": len(customer_modules),
    "snapshot_product_key": snapshot.product_key,
    "database_write_count": 0,
}, sort_keys=True))
