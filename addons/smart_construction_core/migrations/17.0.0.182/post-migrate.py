# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api


MY_WORK_MENU_XMLID = "smart_construction_core.menu_sc_my_work"


def migrate(cr, version):
    """Add My Work without publishing unrelated maintained-policy drafts."""
    del version
    env = api.Environment(cr, SUPERUSER_ID, {})
    policy = env["sc.product.policy"].sudo().with_context(active_test=False)
    for product_key in ("construction.standard", "construction.preview"):
        record = policy.search([("product_key", "=", product_key)], limit=1)
        if not record:
            policy.synchronize_locked_formal_menu_policy(product_key)
        result = policy._reconcile_locked_menu_release(
            product_key,
            menu_xmlid=MY_WORK_MENU_XMLID,
            version="17.0.0.182-my-work",
        )
        if not result["release_present"]:
            raise RuntimeError("MY_WORK_POLICY_MIGRATION_INCOMPLETE: %s" % product_key)
    env.registry.clear_cache()
