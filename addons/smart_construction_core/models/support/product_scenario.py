# -*- coding: utf-8 -*-
"""Maintainable business-scenario organization for the scenario center navigation.

The scenario is an organization layer over already-authorized navigation
entries. Center ownership and ordering are scenario composition, while the
native menu/action remains the only executable fact. A scenario may span
centers, and one native menu may be referenced by multiple scenarios. This
model is the runtime maintenance source that ``system.init`` projects; the P1
JSON surface is only a seed input.
"""
from __future__ import annotations

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.addons.smart_construction_core.services.scenario_product_declarations import (
    DIRECT_CONFIGURATION_MENU_XMLIDS,
    DIRECT_NAVIGATION_MENU_XMLIDS,
    DIRECT_PLATFORM_MENU_XMLIDS,
    DIRECT_WORKSPACE_MENU_XMLIDS,
)


SCENARIO_INTENTS = [
    ("handle", "办理"),
    ("view", "查看"),
    ("approve", "审批"),
    ("report", "报表"),
    ("master_data", "基础信息维护"),
]
SCENARIO_INTENT_CODES = tuple(item[0] for item in SCENARIO_INTENTS)
DIRECT_NAVIGATION_MENU_XMLID_SET = frozenset(DIRECT_NAVIGATION_MENU_XMLIDS)
NAVIGATION_ENTRY_SCOPE_MARKER = (
    "smart_construction_core.navigation_entry_scope.v3"
)
SCENARIO_SEED_KEY = "smart_construction_core.scenario_seed.v1"
EXTERNAL_CENTER_SEED_KEY = "smart_construction_core.external_center_seed.v1"


def _is_direct_navigation_menu(menu) -> bool:
    if not menu:
        return False
    try:
        xmlid = menu.get_external_id().get(menu.id, "")
    except Exception:
        xmlid = ""
    return str(xmlid or "").strip() in DIRECT_NAVIGATION_MENU_XMLID_SET


class ScProductScenario(models.Model):
    _name = "sc.product.scenario"
    _description = "Business Product Scenario"
    _order = "sequence, id"

    active = fields.Boolean(
        default=True,
        string="场景定义启用",
        help=(
            "Controls whether this scenario definition participates in product "
            "organization. It is not the current company's enablement switch."
        ),
    )
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

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self.env.registry.clear_cache()
        return records

    def write(self, vals):
        if "code" in vals and any(record.code != vals["code"] for record in self):
            raise ValidationError("Scenario code is a stable enablement identity; edit the name instead.")
        result = super().write(vals)
        self.env.registry.clear_cache()
        return result

    def unlink(self):
        result = super().unlink()
        self.env.registry.clear_cache()
        return result

    @api.model
    def initialize_direct_entry_exemptions(self):
        """Declare known configuration entries only during first installation.

        Missing association history never proves a legacy direct entry. Upgrades
        preserve explicit decisions, including revocations and deleted bindings.
        """
        params = self.env["ir.config_parameter"].sudo()
        marker = "smart_construction_core.scenario_entry_scope.v1"
        if params.get_param(marker):
            return
        module = self.env["ir.module.module"].sudo().search([
            ("name", "=", "smart_construction_core"),
        ], limit=1)
        if module.state in ("to install", "installing"):
            for xmlid in DIRECT_CONFIGURATION_MENU_XMLIDS:
                menu = self.env.ref(xmlid)
                if menu._name != "ir.ui.menu" or not menu.action:
                    raise ValidationError("Direct configuration declaration requires an action menu: %s" % xmlid)
                menu.sudo().write({"sc_scenario_exempt": True})
        params.set_param(marker, "1")

    @api.model
    def initialize_navigation_entry_exemptions(self):
        """Declare system shell and platform entries that are not business scenes.

        These are native menu facts, not scene-created permissions. Native ACL
        still controls every entry. The one-time marker means an administrator
        can later revoke an exemption without the next upgrade restoring it.
        """
        params = self.env["ir.config_parameter"].sudo()
        marker = NAVIGATION_ENTRY_SCOPE_MARKER
        if params.get_param(marker):
            return
        for xmlid in DIRECT_NAVIGATION_MENU_XMLIDS:
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            if not menu or str(getattr(menu, "_name", "")) != "ir.ui.menu":
                raise ValidationError(
                    "Direct navigation declaration requires an available menu: %s" % xmlid
                )
            if not menu.action and xmlid not in DIRECT_WORKSPACE_MENU_XMLIDS:
                raise ValidationError(
                    "Direct platform declaration requires an action menu: %s" % xmlid
                )
            if not menu.sc_scenario_exempt:
                menu.sudo().write({"sc_scenario_exempt": True})
        params.set_param(marker, "1")

    @api.model
    def import_scenario_product_surface(self):
        """Initialize once, atomically; later upgrades preserve even deletions.

        This is a fresh-install seed initializer. It runs once and never
        overwrites or deletes maintained records.
        """
        from odoo.addons.smart_construction_core.services.scenario_surface_projection import (
            load_surface,
        )

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
                record = Scenario.create({
                    "code": code,
                    "name": name,
                    "description": str(scenario.get("description") or "").strip(),
                    "sequence": int(scenario.get("sequence") or 10),
                })
                existing_codes[code] = record
                created_scenarios += 1
            else:
                skipped_scenarios += 1
            bindings = scenario.get("bindings")
            if isinstance(bindings, list) and bindings:
                binding_rows = [
                    (
                        binding.get("menu_key"),
                        binding.get("intent"),
                        binding.get("sequence"),
                    )
                    for binding in bindings
                    if isinstance(binding, dict)
                ]
            else:
                binding_rows = [
                    (menu_xmlid, intent, 10)
                    for intent, menu_xmlids in (scenario.get("intents") or {}).items()
                    for menu_xmlid in menu_xmlids or []
                ]
            for menu_xmlid, intent, sequence in binding_rows:
                menu = self.env.ref(menu_xmlid, raise_if_not_found=False)
                if not menu or str(getattr(menu, "_name", "")) != "ir.ui.menu":
                    continue
                exists = Entry.search([
                    ("scenario_id", "=", record.id),
                    ("menu_id", "=", menu.id),
                ], limit=1)
                if not exists:
                    Entry.create({
                        "scenario_id": record.id,
                        "menu_id": menu.id,
                        "intent": intent if intent in SCENARIO_INTENT_CODES else "view",
                        "sequence": int(sequence or 10),
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
        help=(
            "Explicitly bypass only scenario enablement. Publication, ACL and "
            "company scope still apply. Direct platform declarations may also "
            "remain organized by a business scenario."
        ),
    )

    def write(self, vals):
        if vals.get("sc_scenario_exempt"):
            bound = self.env["sc.product.scenario.entry"].sudo().search([
                ("menu_id", "in", self.ids),
            ])
            non_direct = bound.mapped("menu_id").filtered(
                lambda menu: not _is_direct_navigation_menu(menu)
            )
            if non_direct:
                raise ValidationError(
                    "Only declared platform direct entries may remain exempt "
                    "while bound to a business scenario."
                )
        result = super().write(vals)
        if {"sc_scenario_exempt", "sc_product_center_id", "parent_id"}.intersection(vals):
            self.env.registry.clear_cache()
        return result

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
    center_key = fields.Char(
        compute="_compute_center_reference",
        string="Product Center",
        help="Derived stable product-center identity from the maintained product policy.",
    )
    center_name = fields.Char(
        compute="_compute_center_reference",
        string="Product Center Name",
        help="Derived label from the maintained product policy.",
    )
    center_sequence = fields.Integer(
        compute="_compute_center_reference",
        string="Product Center Sequence",
        help="Derived order from the maintained product policy.",
    )

    _sql_constraints = [
        (
            "sc_scenario_entry_scenario_menu_uniq",
            "unique(scenario_id, menu_id)",
            "Each native menu may appear only once within a scenario.",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        ordinary = records.mapped("menu_id").filtered(
            lambda menu: not _is_direct_navigation_menu(menu)
        )
        ordinary.sudo().write({"sc_scenario_exempt": False})
        self.env.registry.clear_cache()
        return records

    def write(self, vals):
        result = super().write(vals)
        if "menu_id" in vals or "scenario_id" in vals:
            ordinary = self.mapped("menu_id").filtered(
                lambda menu: not _is_direct_navigation_menu(menu)
            )
            ordinary.sudo().write({"sc_scenario_exempt": False})
        self.env.registry.clear_cache()
        return result

    def unlink(self):
        result = super().unlink()
        self.env.registry.clear_cache()
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

    @api.depends("menu_id")
    def _compute_center_reference(self):
        from odoo.addons.smart_construction_core.services.product_center_policy import (
            construction_product_center_index,
        )

        policy = self.env["sc.product.policy"].sudo().search(
            [
                ("product_key", "=", "construction.standard"),
                ("active", "=", True),
            ],
            limit=1,
        )
        center_index = (
            construction_product_center_index(policy.to_runtime_dict())
            if policy
            else {"by_menu": {}}
        )
        for entry in self:
            center = center_index["by_menu"].get(entry.menu_xmlid or "")
            entry.center_key = str(
                (center or {}).get("center_key") or ""
            ).strip()
            entry.center_name = str(
                (center or {}).get("center_label") or ""
            ).strip()
            entry.center_sequence = int(
                (center or {}).get("center_sequence") or 10
            )
