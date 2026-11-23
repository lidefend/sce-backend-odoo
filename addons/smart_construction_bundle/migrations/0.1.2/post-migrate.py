# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Provision the shipped release after the complete product bundle upgrades."""
    del version
    env = api.Environment(cr, SUPERUSER_ID, {})
    policy = env["sc.product.policy"].sudo()
    policy.sync_construction_menu_product_policies()
    policy.ensure_system_product_release_snapshots()
    env.registry.clear_cache()
