# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Promote formerly preview-only product entries without widening ACLs."""
    del version
    env = api.Environment(cr, SUPERUSER_ID, {})
    policy = env["sc.product.policy"].sudo()
    previous = policy.preview_entry_policy_snapshot()
    result = policy.promote_preview_entries_to_standard_release()
    validation = policy.validate_preview_entry_promotion(result, previous=previous)
    env.registry.clear_cache()
    return validation
