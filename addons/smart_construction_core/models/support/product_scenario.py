# -*- coding: utf-8 -*-
"""Maintainable business-scenario organization for the scenario center navigation.

The scenario is an organization layer over already-authorized navigation
entries. Center ownership is derived from the native ``ir.ui.menu`` tree, with
a separate menu relation for external entries; a scenario may span centers, while an entry
binds to exactly one scenario. This model is the runtime maintenance source
that ``system.init`` projects; the P1 JSON surface is only a seed input.
"""
from __future__ import annotations

from odoo import api, fields, models
from odoo.exceptions import ValidationError


SCENARIO_INTENTS = [
    ("handle", "办理"),
    ("view", "查看"),
    ("approve", "审批"),
    ("report", "报表"),
    ("master_data", "基础信息维护"),
]
SCENARIO_INTENT_CODES = tuple(item[0] for item in SCENARIO_INTENTS)
SCENARIO_SEED_KEY = "smart_construction_core.scenario_seed.v1"
EXTERNAL_CENTER_SEED_KEY = "smart_construction_core.external_center_seed.v1"


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

    @api.constrains("code")
    def _check_stable_code(self):
        for record in self:
            if not record.code or not record.code.strip() or record.code != record.code.strip():
                raise ValidationError("Scenario code must be nonempty and have no surrounding whitespace.")

    def write(self, vals):
        if "code" in vals and any(record.code != vals["code"] for record in self):
            raise ValidationError("Scenario code is a stable enablement identity; edit the name instead.")
        return super().write(vals)

    @api.model
    def initialize_direct_entry_exemptions(self):
        """Finalize scope initialization without inferring new exemptions.

        Neither an absent binding nor absence from the seed proves a legacy
        direct entry: administrators may have deleted a custom association.
        There is no authoritative association history to distinguish those
        cases, so preserve explicit declarations and leave unknowns denied.
        """
        params = self.env["ir.config_parameter"].sudo()
        marker = "smart_construction_core.scenario_entry_scope.v1"
        if params.get_param(marker):
            return
        params.set_param(marker, "1")

    @api.model
    def import_scenario_product_surface(self):
        """Initialize once, atomically; later upgrades preserve even deletions.

        A versioned migration marks legacy installations initialized before
        this method is called. Future seed changes require explicit migrations.
        """
        from odoo.addons.smart_construction_core.services.scenario_surface_projection import load_surface

        Param = self.env["ir.config_parameter"].sudo()
        if Param.get_param(SCENARIO_SEED_KEY):
            return {"created_scenarios": 0, "skipped_scenarios": 0, "created_entries": 0}
        surface = load_surface()
        Scenario = self.sudo().with_context(active_test=False)
        Entry = self.env["sc.product.scenario.entry"].sudo()
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
                        [("menu_id", "=", menu.id)], limit=1
                    )
                    if not exists:
                        Entry.create({
                            "scenario_id": record.id,
                            "menu_id": menu.id,
                            "intent": intent_code,
                            "sequence": 10,
                        })
                        created_entries += 1
        Param.set_param(SCENARIO_SEED_KEY, "1")
        return {
            "created_scenarios": created_scenarios,
            "skipped_scenarios": skipped_scenarios,
            "created_entries": created_entries,
        }

    @api.model
    def initialize_external_navigation_centers(self):
        """Seed stable external-menu placement once, independently of scenarios."""
        import json
        from odoo.addons.smart_construction_core.services.product_menu_source import SOURCE_PATH

        Param = self.env["ir.config_parameter"].sudo()
        if Param.get_param(EXTERNAL_CENTER_SEED_KEY):
            return
        source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
        for entry in source.get("entries", []):
            placement = entry.get("external_presentation")
            if not placement:
                continue
            menu = self.env.ref(entry["menu_xmlid"], raise_if_not_found=False)
            center = self.env.ref(placement["center_xmlid"], raise_if_not_found=False)
            if not menu or not center:
                raise ValidationError("External navigation seed references an unavailable menu or center.")
            if not menu.sc_product_center_id:
                menu.sudo().sc_product_center_id = center
        Param.set_param(EXTERNAL_CENTER_SEED_KEY, "1")


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    sc_product_center_id = fields.Many2one(
        "ir.ui.menu", string="External Product Center", ondelete="restrict",
        help="Placement for entries outside the business root. A native business parent chain takes precedence.",
    )
    sc_scenario_exempt = fields.Boolean(
        string="Exempt from Company Scenario Enablement", default=False,
        help="Explicitly bypass only scenario enablement. Publication, ACL and company scope still apply. A scenario binding takes precedence.",
    )

    def write(self, vals):
        if vals.get("sc_scenario_exempt") and self.env["sc.product.scenario.entry"].sudo().search_count([
            ("menu_id", "in", self.ids),
        ]):
            raise ValidationError("Remove the scenario binding before explicitly exempting an entry.")
        return super().write(vals)

    @api.constrains("sc_product_center_id", "parent_id")
    def _check_product_center(self):
        root = self.env.ref("smart_construction_core.menu_sc_root", raise_if_not_found=False)
        for menu in self:
            if menu.sc_product_center_id and (not root or menu.sc_product_center_id.parent_id != root):
                raise ValidationError("External Product Center must be a direct child of the business root.")


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

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.mapped("menu_id").sudo().write({"sc_scenario_exempt": False})
        return records

    def write(self, vals):
        result = super().write(vals)
        if "menu_id" in vals or "scenario_id" in vals:
            self.mapped("menu_id").sudo().write({"sc_scenario_exempt": False})
        return result

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
