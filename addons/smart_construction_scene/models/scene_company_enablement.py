# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ScSceneCompanyEnablement(models.Model):
    _name = "sc.scene.company.enablement"
    _description = "SC Scene Company Enablement"
    _order = "company_id, scene_key"
    _rec_name = "scene_key"

    company_id = fields.Many2one("res.company", string="公司", required=True, ondelete="cascade")
    scene_key = fields.Char(string="场景标识", required=True, index=True)
    enabled = fields.Boolean(string="企业已启用", default=False)
    provenance = fields.Char(string="配置来源", default="tenant", readonly=True)

    _sql_constraints = [
        (
            "sc_scene_company_enablement_company_scene_uniq",
            "unique(company_id, scene_key)",
            "同一公司同一场景只能有一条启用配置。",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self.env.registry.clear_cache()
        return records

    def write(self, vals):
        result = super().write(vals)
        # Only persisted delivery inputs invalidate navigation/route caches.
        # Company and key changes matter just as much as the enabled flag.
        if {"company_id", "scene_key", "enabled"}.intersection(vals):
            self.env.registry.clear_cache()
        return result

    def unlink(self):
        result = super().unlink()
        self.env.registry.clear_cache()
        return result

    @api.model
    def _ensure_for(self, company, scene_key):
        from odoo.addons.smart_construction_scene.services.tenant_scene_activation import (
            decide_tenant_enablement,
            resolve_product_released,
        )

        record = self.sudo().search(
            [("company_id", "=", company.id), ("scene_key", "=", scene_key)], limit=1
        )
        product_released = resolve_product_released(scene_key)
        currently_enabled = bool(record.enabled) if record else False
        return record, decide_tenant_enablement(
            product_released=product_released,
            currently_enabled=currently_enabled,
            requested=not currently_enabled,
        )

    def set_enabled(self, enabled: bool):
        from odoo.addons.smart_construction_scene.services.tenant_scene_activation import (
            decide_tenant_enablement,
            resolve_product_released,
        )

        self.ensure_one()
        if not isinstance(enabled, bool):
            raise UserError(_("启用状态必须为布尔值。"))
        allowed, next_enabled = decide_tenant_enablement(
            product_released=resolve_product_released(self.scene_key),
            currently_enabled=bool(self.enabled),
            requested=enabled,
        )
        if not allowed:
            raise UserError(_("该场景为 Preview 状态，企业不能启用。"))
        if bool(self.enabled) != bool(next_enabled):
            self.write({"enabled": bool(next_enabled)})
        return self
