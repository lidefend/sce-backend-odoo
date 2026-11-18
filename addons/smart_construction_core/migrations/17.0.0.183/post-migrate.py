# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Promote formerly preview-only product entries without widening ACLs."""
    del version
    env = api.Environment(cr, SUPERUSER_ID, {})
    result = env["sc.product.policy"].sudo().promote_preview_entries_to_standard_release()
    standard = env["sc.product.policy"].sudo().with_context(active_test=False).search([
        ("product_key", "=", "construction.standard"),
    ], limit=1)
    preview = env["sc.product.policy"].sudo().with_context(active_test=False).search([
        ("product_key", "=", "construction.preview"),
    ], limit=1)
    for product_key, record in (
        ("construction.standard", standard),
        ("construction.preview", preview),
    ):
        rows = [
            row
            for group in record.menu_groups or []
            for row in group.get("menus") or []
            if isinstance(row, dict)
        ]
        if len(rows) != 132 or any(row.get("release_state") != "released" for row in rows):
            raise RuntimeError(
                "CLOSE03_PREVIEW_PROMOTION_INCOMPLETE: %s promoted=%s"
                % (product_key, result["promoted_entry_count"])
            )
    env.registry.clear_cache()
