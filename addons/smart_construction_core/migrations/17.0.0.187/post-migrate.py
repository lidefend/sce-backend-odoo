# -*- coding: utf-8 -*-
"""Retire superseded standard process scenarios, then add current scenarios."""
from __future__ import annotations

from odoo import SUPERUSER_ID, api


LEGACY_STANDARD_SCENARIO_CODES = (
    "governance.organization",
    "project.management",
    "contract.performance",
    "cost.budget",
    "procurement.supplier",
    "material.management",
    "subcontract.management",
    "labor.management",
    "quality.management",
    "safety.management",
    "payment.capital",
    "receipt.payment.ledger",
    "tax.management",
    "accounting.management",
    "analytics.decision",
    "equipment.management",
    "administration.office",
)


def migrate(cr, version):
    if not version:
        return {"skipped": "fresh_install"}
    env = api.Environment(cr, SUPERUSER_ID, {})
    scenario_model = env["sc.product.scenario"].sudo()
    legacy = scenario_model.with_context(active_test=False).search([
        ("code", "in", LEGACY_STANDARD_SCENARIO_CODES),
    ])
    retired_codes = sorted(legacy.mapped("code"))
    legacy.mapped("entry_ids").unlink()
    legacy.unlink()
    result = scenario_model.import_scenario_product_surface(force=True)
    scenario_model.initialize_navigation_entry_exemptions()
    env.registry.clear_cache()
    return {
        "retired_legacy_scenarios": retired_codes,
        **result,
    }
