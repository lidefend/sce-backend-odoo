# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class ScProductSystemSettings(models.TransientModel):
    _name = "sc.product.system.settings"
    _description = "产品系统参数"

    cost_ledger_source = fields.Selection(
        [
            ("account_move", "会计凭证"),
            ("purchase_order", "采购订单"),
            ("stock_move", "库存入库"),
            ("disabled", "暂不自动归集"),
        ],
        string="成本台账自动归集来源",
        required=True,
        default="account_move",
    )
    parameter_scope = fields.Char(string="参数范围", default="施工标准产品 / 当前公司", readonly=True)
    operation_notice = fields.Text(
        string="运行说明",
        default="成本台账只能选择一个自动归集来源，避免同一成本重复计入。部署参数、认证密钥和运行秘密不在产品页面维护。",
        readonly=True,
    )

    @api.model
    def default_get(self, field_names):
        values = super().default_get(field_names)
        params = self.env["ir.config_parameter"].sudo().with_company(self.env.company)
        enabled = {
            "account_move": params.get_param("smart_construction_core.sc_cost_from_account_move", "True"),
            "purchase_order": params.get_param("smart_construction_core.sc_cost_from_purchase", "False"),
            "stock_move": params.get_param("smart_construction_core.sc_cost_from_stock", "False"),
        }
        selected = [key for key, value in enabled.items() if str(value).lower() in ("1", "true", "yes")]
        values["cost_ledger_source"] = selected[0] if len(selected) == 1 else "disabled"
        return values

    def action_apply(self):
        self.ensure_one()
        if not (
            self.env.su
            or self.env.user.has_group("smart_construction_core.group_sc_cap_config_admin")
            or self.env.user.has_group("smart_construction_core.group_sc_super_admin")
        ):
            raise AccessError(_("只有行业配置管理员可以修改产品系统参数。"))
        params = self.env["ir.config_parameter"].sudo().with_company(self.env.company)
        mapping = {
            "account_move": "smart_construction_core.sc_cost_from_account_move",
            "purchase_order": "smart_construction_core.sc_cost_from_purchase",
            "stock_move": "smart_construction_core.sc_cost_from_stock",
        }
        for source, key in mapping.items():
            params.set_param(key, "True" if self.cost_ledger_source == source else "False")
        return {"type": "ir.actions.client", "tag": "display_notification", "params": {"title": _("系统参数"), "message": _("产品参数已生效。"), "type": "success", "sticky": False}}
