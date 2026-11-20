# -*- coding: utf-8 -*-
"""Add missing standard scenario organizations without replacing maintained facts."""
from __future__ import annotations

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return {"skipped": "fresh_install"}
    env = api.Environment(cr, SUPERUSER_ID, {})
    scenario_model = env["sc.product.scenario"].sudo()
    result = scenario_model.import_scenario_product_surface(force=True)
    scenario_model.initialize_navigation_entry_exemptions()
    env.registry.clear_cache()
    return result
