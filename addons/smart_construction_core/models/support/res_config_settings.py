# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    """
    兜底：部分继承视图里引用了 is_installed_sale，
    在未安装 sale/purchase 组合时字段不存在会导致设置页加载失败。
    """

    _inherit = "res.config.settings"

    is_installed_sale = fields.Boolean(
        string="销售模块安装状态",
        readonly=True,
        help="设置页中对销售模块安装状态的引用；真实安装状态以当前环境为准。",
    )

    days_to_purchase = fields.Float(
        string="采购交期天数",
        readonly=True,
        help="设置页中对采购交期字段的引用；"
             "未安装采购库存模块时不会实际生效。",
    )

    sc_cost_from_account_move = fields.Boolean(
        string="成本台账来源：凭证",
        related="company_id.sc_cost_from_account_move",
        readonly=False,
        help="勾选后凭证过账会写入项目成本台账。",
    )
    sc_cost_from_purchase = fields.Boolean(
        string="成本台账来源：采购",
        related="company_id.sc_cost_from_purchase",
        readonly=False,
        help="勾选后采购订单确认写入项目成本台账。",
    )
    sc_cost_from_stock = fields.Boolean(
        string="成本台账来源：入库",
        related="company_id.sc_cost_from_stock",
        readonly=False,
        help="勾选后入库完成写入项目成本台账。",
    )

    def set_values(self):
        for settings in self:
            enabled = sum(
                bool(value)
                for value in (
                    settings.sc_cost_from_account_move,
                    settings.sc_cost_from_purchase,
                    settings.sc_cost_from_stock,
                )
            )
            if enabled > 1:
                raise ValidationError(_("成本台账只能启用凭证、采购或入库中的一个自动来源。"))
        return super().set_values()
