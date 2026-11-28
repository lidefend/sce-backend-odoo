# -*- coding: utf-8 -*-
"""Native company-scoped enablement for published product scenarios."""
from odoo import _, fields, models
from odoo.exceptions import AccessError, UserError

from odoo.addons.smart_construction_scene.services.business_scene_enablement import business_key
from odoo.addons.smart_construction_scene.services.tenant_scene_activation import (
    read_tenant_enablement,
    resolve_product_released,
    write_tenant_enablement,
)


class ScProductScenario(models.Model):
    _inherit = "sc.product.scenario"

    sc_product_released = fields.Boolean(
        string="产品已发布",
        compute="_compute_company_enablement_facts",
    )
    sc_product_release_label = fields.Char(
        string="产品状态",
        compute="_compute_company_enablement_facts",
    )
    sc_company_enabled = fields.Boolean(
        string="企业已启用",
        compute="_compute_company_enablement_facts",
    )
    sc_company_status_label = fields.Char(
        string="企业状态",
        compute="_compute_company_enablement_facts",
    )

    def _compute_company_enablement_facts(self):
        company = self.env.company
        for scenario in self:
            released = bool(
                scenario.active
                and resolve_product_released(
                    business_key(scenario.code),
                    env=self.env,
                )
            )
            enabled = bool(
                released
                and read_tenant_enablement(
                    self.env,
                    company.id,
                    business_key(scenario.code),
                )
            )
            scenario.sc_product_released = released
            scenario.sc_product_release_label = _("已发布") if released else _("未发布")
            scenario.sc_company_enabled = enabled
            scenario.sc_company_status_label = _("已启用") if enabled else _("未启用")

    def _ensure_company_enablement_administrator(self):
        if not self.env.user.has_group(
            "smart_construction_core.group_sc_cap_business_config_admin"
        ):
            raise AccessError(_("只有企业业务配置管理员可以调整企业场景启停。"))

    def _set_company_enablement(self, enabled):
        self.ensure_one()
        self._ensure_company_enablement_administrator()
        company = self.env.company
        if company not in self.env.user.company_ids:
            raise AccessError(_("当前企业不在用户允许的公司范围内。"))
        stored_key = business_key(self.code)
        if enabled and not resolve_product_released(stored_key, env=self.env):
            raise UserError(_("该业务场景尚未发布，当前企业不能启用。"))
        write_tenant_enablement(self.env, company.id, stored_key, bool(enabled))
        readback = read_tenant_enablement(self.env, company.id, stored_key)
        if readback is not bool(enabled):
            raise UserError(_("企业场景启停写入后回读不一致。"))
        self.invalidate_recordset([
            "sc_product_released",
            "sc_product_release_label",
            "sc_company_enabled",
            "sc_company_status_label",
        ])
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_enable_for_company(self):
        return self._set_company_enablement(True)

    def action_disable_for_company(self):
        return self._set_company_enablement(False)
