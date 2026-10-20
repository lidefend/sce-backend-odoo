# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import AccessError


class ScProductSystemParameterChange(models.Model):
    _name = "sc.product.system.parameter.change"
    _description = "受控系统参数变更"
    _order = "id desc"

    parameter_key = fields.Char(required=True, index=True)
    proposed_value = fields.Json(required=True)
    previous_value = fields.Json()
    state = fields.Selection(
        [
            ("draft", "草稿"),
            ("previewed", "已预览"),
            ("published", "已发布"),
            ("rolled_back", "已回滚"),
            ("failed", "失败"),
        ],
        required=True,
        default="draft",
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    user_id = fields.Many2one(
        "res.users",
        required=True,
        default=lambda self: self.env.user,
        readonly=True,
        index=True,
    )
    change_reason = fields.Char()
    risk_level = fields.Selection(
        [("low", "低"), ("medium", "中"), ("high", "高")],
        default="low",
    )
    published_at = fields.Datetime(readonly=True)
    rolled_back_at = fields.Datetime(readonly=True)
    audit_json = fields.Json(default=dict)

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su:
            raise AccessError("请通过受管系统参数变更集入口维护参数。")
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.su:
            raise AccessError("请通过受管系统参数变更集入口维护参数。")
        return super().write(vals)

    def unlink(self):
        if not self.env.su:
            raise AccessError("请通过受管系统参数变更集入口维护参数。")
        return super().unlink()

    def serialize(self):
        self.ensure_one()
        return {
            "id": int(self.id),
            "parameter_key": str(self.parameter_key or ""),
            "proposed_value": self.proposed_value,
            "previous_value": self.previous_value,
            "state": str(self.state or ""),
            "company_id": int(self.company_id.id or 0),
            "change_reason": str(self.change_reason or ""),
            "risk_level": str(self.risk_level or "low"),
            "published_at": fields.Datetime.to_string(self.published_at) if self.published_at else False,
            "rolled_back_at": fields.Datetime.to_string(self.rolled_back_at) if self.rolled_back_at else False,
            "audit_json": self.audit_json or {},
        }
