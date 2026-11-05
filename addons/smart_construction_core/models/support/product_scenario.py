# -*- coding: utf-8 -*-
"""Maintainable business-scenario organization for the scenario center navigation.

The scenario is an organization layer over already-authorized navigation
entries. Center ownership is derived from the native ``ir.ui.menu`` tree and is
never duplicated here; a scenario may span centers, while a navigation entry
binds to exactly one scenario. This model is the runtime maintenance source
that ``system.init`` projects; the P1 JSON surface is only a seed input.
"""
from __future__ import annotations

from odoo import api, fields, models


SCENARIO_INTENTS = [
    ("handle", "办理"),
    ("view", "查看"),
    ("approve", "审批"),
    ("report", "报表"),
    ("master_data", "基础信息维护"),
]
SCENARIO_INTENT_CODES = tuple(item[0] for item in SCENARIO_INTENTS)


class ScProductScenario(models.Model):
    _name = "sc.product.scenario"
    _description = "Business Product Scenario"
    _order = "sequence, id"

    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    code = fields.Char(required=True, index=True)
    name = fields.Char(required=True)
    description = fields.Char()
    entry_ids = fields.One2many("sc.product.scenario.entry", "scenario_id", string="Navigation Entries")

    _sql_constraints = [
        ("sc_product_scenario_code_uniq", "unique(code)", "Scenario code must be unique."),
    ]

    @api.model
    def import_scenario_product_surface(self):
        """Idempotent, create-only seed from the P1 scenario surface JSON.

        Runs on both fresh install and module upgrade through the data file
        ``data/product_scenario_seed.xml``. It never rewrites an existing
        scenario or entry, so operator edits survive later upgrades.
        """
        from odoo.addons.smart_construction_core.services.scenario_surface_projection import load_surface

        surface = load_surface()
        Scenario = self.sudo()
        Entry = self.env["sc.product.scenario.entry"].sudo()
        Menu = self.env["ir.ui.menu"].sudo()
        existing_codes = {rec.code: rec for rec in Scenario.search([])}
        created_scenarios = 0
        skipped_scenarios = 0
        created_entries = 0
        for scenario in surface.get("scenarios") or []:
            code = str(scenario.get("key") or "").strip()
            name = str(scenario.get("name") or code).strip()
            if not code:
                continue
            record = existing_codes.get(code)
            if not record:
                record = Scenario.create({"code": code, "name": name})
                existing_codes[code] = record
                created_scenarios += 1
            else:
                skipped_scenarios += 1
            for intent, menu_xmlids in (scenario.get("intents") or {}).items():
                intent_code = intent if intent in SCENARIO_INTENT_CODES else "view"
                for menu_xmlid in menu_xmlids or []:
                    menu = self.env.ref(menu_xmlid, raise_if_not_found=False)
                    if not menu or str(getattr(menu, "_name", "")) != "ir.ui.menu":
                        continue
                    exists = Entry.search(
                        [("scenario_id", "=", record.id), ("menu_id", "=", menu.id)], limit=1
                    )
                    if not exists:
                        Entry.create({
                            "scenario_id": record.id,
                            "menu_id": menu.id,
                            "intent": intent_code,
                            "sequence": 10,
                        })
                        created_entries += 1
        return {
            "created_scenarios": created_scenarios,
            "skipped_scenarios": skipped_scenarios,
            "created_entries": created_entries,
        }


class ScProductScenarioEntry(models.Model):
    _name = "sc.product.scenario.entry"
    _description = "Business Product Scenario Entry"
    _order = "sequence, id"

    scenario_id = fields.Many2one("sc.product.scenario", required=True, ondelete="cascade")
    menu_id = fields.Many2one("ir.ui.menu", required=True, ondelete="restrict")
    menu_xmlid = fields.Char(compute="_compute_menu_xmlid", store=True, readonly=True)
    intent = fields.Selection(SCENARIO_INTENTS, required=True, default="handle")
    sequence = fields.Integer(default=10)

    _sql_constraints = [
        (
            "sc_product_scenario_entry_menu_uniq",
            "unique(menu_id)",
            "Each navigation entry can bind to exactly one scenario.",
        ),
    ]

    @api.depends("menu_id")
    def _compute_menu_xmlid(self):
        for entry in self:
            entry.menu_xmlid = ""
            if entry.menu_id:
                try:
                    external = entry.menu_id.get_external_id().get(entry.menu_id.id)
                    entry.menu_xmlid = str(external or "").strip()
                except Exception:
                    entry.menu_xmlid = ""
