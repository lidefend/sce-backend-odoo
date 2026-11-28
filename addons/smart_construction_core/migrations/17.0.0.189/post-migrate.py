# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api


PRODUCT_CONFIG_PARENT_XMLID = "smart_construction_core.menu_sc_business_config_center"
PRODUCT_CONFIG_MENU_XMLIDS = (
    "smart_construction_core.menu_sc_business_category",
    "smart_construction_core.menu_sc_dictionary",
    "smart_construction_core.menu_sc_project_cost_code",
    "smart_construction_core.menu_sc_project_stage_requirement_items",
    "smart_construction_core.menu_sc_approval_scope",
)


def migrate(cr, version):
    """Publish newly shipped product-configuration facts on existing databases."""
    del version
    env = api.Environment(cr, SUPERUSER_ID, {})
    parent = env.ref(PRODUCT_CONFIG_PARENT_XMLID, raise_if_not_found=False)
    if not parent:
        raise RuntimeError("PRODUCT_CONFIGURATION_PARENT_MISSING")
    Menu = env["ir.ui.menu"].sudo().with_context(active_test=False)
    for xmlid in PRODUCT_CONFIG_MENU_XMLIDS:
        menu = env.ref(xmlid, raise_if_not_found=False)
        if not menu:
            raise RuntimeError("PRODUCT_CONFIGURATION_MENU_MISSING: %s" % xmlid)
        menu.write({
            "parent_id": parent.id,
            "active": True,
        })

    product_policy = env["sc.product.policy"].sudo().with_context(active_test=False)
    results = {}
    for product_key in ("construction.standard", "construction.preview"):
        record = product_policy.search([
            ("product_key", "=", product_key),
        ], limit=1)
        if not record:
            raise RuntimeError("PRODUCT_POLICY_MISSING: %s" % product_key)
        result = product_policy.reconcile_locked_formal_menu_surface(
            product_key,
            version="17.0.0.189-product-configuration-surface",
        )
        if not result.get("release_present"):
            raise RuntimeError("PRODUCT_MENU_RELEASE_INCOMPLETE: %s" % product_key)
        results[product_key] = {
            "added": result.get("added") or [],
            "snapshot_id": int(result.get("snapshot_id") or 0),
            "snapshot_created": bool(result.get("snapshot_created")),
        }
    env.registry.clear_cache()
    return results
