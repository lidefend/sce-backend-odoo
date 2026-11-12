# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api


MY_WORK_MENU_XMLID = "smart_construction_core.menu_sc_my_work"


def migrate(cr, version):
    """Add My Work to established product policies without replacing edits."""
    del version
    env = api.Environment(cr, SUPERUSER_ID, {})
    policy = env["sc.product.policy"].sudo().with_context(active_test=False)
    from odoo.addons.smart_core.delivery.edition_release_snapshot_service import (
        EditionReleaseSnapshotService,
    )
    snapshot_service = EditionReleaseSnapshotService(env)
    for product_key in ("construction.standard", "construction.preview"):
        record = policy.search([("product_key", "=", product_key)], limit=1)
        if not record:
            policy.synchronize_locked_formal_menu_policy(product_key)
        else:
            result = policy.merge_locked_formal_menu_additions(
                product_key,
                menu_xmlids=[MY_WORK_MENU_XMLID],
            )
            if MY_WORK_MENU_XMLID not in result["added"] + result["skipped"]:
                raise RuntimeError("MY_WORK_POLICY_MIGRATION_INCOMPLETE: %s" % product_key)
        snapshot_service.freeze_release_surface(
            product_key=product_key,
            replace_active=True,
            note="17.0.0.182 reconcile My Work product policy",
        )
    env.registry.clear_cache()
