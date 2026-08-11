# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class IrSequence(models.Model):
    _inherit = "ir.sequence"

    sc_product_configurable = fields.Boolean(
        string="产品可配置编码规则",
        compute="_compute_sc_product_configurable",
        search="_search_sc_product_configurable",
    )

    @api.model
    def _sc_product_sequence_domain(self):
        return ["|", "|", ("code", "=like", "sc.%"), ("code", "=like", "project.%"), ("code", "=", "payment.request")]

    @api.depends("code")
    def _compute_sc_product_configurable(self):
        for record in self:
            code = record.code or ""
            record.sc_product_configurable = code.startswith(("sc.", "project.")) or code == "payment.request"

    def _search_sc_product_configurable(self, operator, value):
        positive = operator in ("=", "==") and bool(value) or operator in ("!=", "<>") and not bool(value)
        domain = self._sc_product_sequence_domain()
        return domain if positive else ["!"] + domain

    def write(self, values):
        is_limited_admin = (
            not self.env.su
            and self.env.user.has_group("smart_construction_core.group_sc_cap_config_admin")
            and not self.env.user.has_group("base.group_system")
        )
        if is_limited_admin:
            if any(not record.sc_product_configurable for record in self):
                raise AccessError(_("只能维护产品业务编码规则。"))
            allowed = {"prefix", "suffix", "padding", "number_increment", "number_next_actual"}
            forbidden = set(values) - allowed
            if forbidden:
                raise AccessError(_("编码规则标识和技术属性由产品发布管理，当前仅允许调整格式与流水号。"))
        return super().write(values)
