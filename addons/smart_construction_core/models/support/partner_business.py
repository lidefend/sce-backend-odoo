# -*- coding: utf-8 -*-


from odoo import _, api, fields, models
from odoo.exceptions import UserError


SUPPLIER_TYPE_SELECTION = [
    ("material", "材料供应商"),
    ("labor", "劳务供应商"),
    ("subcontract", "分包单位"),
    ("service", "服务供应商"),
    ("equipment", "设备供应商"),
    ("other", "其他"),
]


class ScSupplierType(models.Model):
    _name = "sc.supplier.type"
    _description = "供应商类型"
    _inherit = ["sc.delete.guard.mixin"]
    _order = "sequence, id"

    name = fields.Char(string="类型名称", required=True, translate=True)
    code = fields.Char(string="类型编码", required=True, index=True)
    sequence = fields.Integer(string="排序", default=10)
    active = fields.Boolean(string="启用", default=True)

    _sql_constraints = [
        ("code_uniq", "unique(code)", "供应商类型编码必须唯一。"),
    ]

    def unlink(self):
        active_types = self.filtered("active")
        if active_types:
            raise UserError("请先停用供应商类型后再删除。")
        self._sc_raise_delete_blockers(action_label="删除供应商类型")
        return super().unlink()


class ResPartner(models.Model):
    _name = "res.partner"
    _inherit = ["res.partner", "sc.delete.guard.mixin"]
    _sc_delete_guard_blocker_models = (
        "construction.contract",
        "payment.request",
        "project.project",
        "sc.contract.event",
        "sc.expense.claim",
        "sc.financing.loan",
        "sc.invoice.registration",
        "sc.material.acceptance",
        "sc.material.inbound",
        "sc.material.outbound",
        "sc.material.price",
        "sc.material.purchase.request",
        "sc.material.rfq",
        "sc.material.rental.order",
        "sc.material.rental.plan",
        "sc.payment.execution",
        "sc.plan",
        "sc.quality.issue",
        "sc.receipt.income",
        "sc.safety.issue",
        "sc.settlement.adjustment",
        "sc.settlement.order",
        "sc.subcontract.plan",
        "sc.subcontract.register",
        "sc.subcontract.request",
        "sc.subcontract.settlement",
        "sc.tax.deduction.registration",
        "tender.bid",
    )

    # Localize the standard Odoo company_type field so customer/supplier
    # archives render Chinese labels and selection values.
    company_type = fields.Selection(
        [
            ("person", "个人"),
            ("company", "公司"),
        ],
        string="客户类型",
        index=True,
    )

    # Localize other standard Odoo res.partner field labels so the customer/
    # supplier archives render Chinese labels (contract assembler consumes the
    # field string). Field types are kept identical to the Odoo base module.
    is_company = fields.Boolean(string="企业/组织")
    category_id = fields.Many2many("res.partner.category", string="业务分类")
    vat = fields.Char(string="统一社会信用代码")
    company_registry = fields.Char(string="工商注册号")
    industry_id = fields.Many2one("res.partner.industry", string="行业")
    phone = fields.Char(string="电话")
    mobile = fields.Char(string="手机")
    email = fields.Char(string="电子邮件")
    website = fields.Char(string="网站")
    street = fields.Char(string="街道地址")
    street2 = fields.Char(string="详细地址")
    city = fields.Char(string="城市")
    state_id = fields.Many2one("res.country.state", string="省/州")
    zip = fields.Char(string="邮编")
    country_id = fields.Many2one("res.country", string="国家/地区")

    sc_supplier_type = fields.Selection(
        SUPPLIER_TYPE_SELECTION,
        string="主供应商类型",
        index=True,
    )
    sc_supplier_type_ids = fields.Many2many(
        "sc.supplier.type",
        "sc_res_partner_supplier_type_rel",
        "partner_id",
        "supplier_type_id",
        string="供应商类型",
    )
    sc_supplier_type_label = fields.Char(
        string="供应商类型汇总",
        compute="_compute_sc_supplier_type_label",
        store=True,
        readonly=True,
    )
    sc_account_name = fields.Char(string="账户名称")
    sc_bank_name = fields.Char(string="开户银行")
    sc_bank_account = fields.Char(string="账号")
    sc_region = fields.Char(string="所属地区", index=True)
    sc_registered_capital = fields.Char(string="注册资本")
    sc_establishment_date = fields.Date(string="成立日期")
    sc_business_term = fields.Char(string="营业期限")
    sc_legal_representative = fields.Char(string="法定代表人")
    sc_contact_name = fields.Char(string="联系人")
    sc_business_scope = fields.Text(string="经营范围")
    sc_default_tax_rate = fields.Float(string="默认税率%", digits=(16, 4))
    sc_default_tax_rate_text = fields.Char(string="税率文本")
    sc_supplier_note = fields.Text(string="供应商备注")
    sc_blacklisted = fields.Boolean(string="黑名单", default=False, index=True, tracking=True)
    sc_blacklist_level = fields.Selection(
        [("attention", "关注"), ("restricted", "限制合作"), ("blocked", "停止合作")],
        string="风险级别",
        default="attention",
        index=True,
        tracking=True,
    )
    sc_blacklist_reason = fields.Text(string="列入原因", tracking=True)
    sc_blacklist_review_date = fields.Date(string="复核日期", tracking=True)
    sc_blacklisted_at = fields.Datetime(string="列入时间", readonly=True, tracking=True)
    sc_blacklisted_by = fields.Many2one("res.users", string="列入人", readonly=True, tracking=True)
    sc_blacklist_advisory = fields.Char(
        string="完善提示",
        compute="_compute_sc_blacklist_advisory",
        help="黑名单原因和复核日期仅作治理提示，不作为操作硬阻断条件。",
    )
    sc_transaction_eligibility = fields.Selection(
        [
            ("eligible", "可办理"),
            ("review_required", "需风险复核"),
            ("blocked", "禁止新业务"),
        ],
        string="交易资格",
        compute="_compute_sc_transaction_eligibility",
        store=True,
        index=True,
        help="由档案启用状态和客商风险级别统一判定，供付款申请等新业务办理复用。",
    )
    sc_transaction_eligibility_reason = fields.Char(
        string="交易资格说明",
        compute="_compute_sc_transaction_eligibility",
        store=True,
    )
    sc_attachment_ids = fields.Many2many(
        "ir.attachment",
        "sc_res_partner_supplier_attachment_rel",
        "partner_id",
        "attachment_id",
        string="供应商附件",
    )

    # Historical identity carrier fields for idempotent migration replay.

    @api.depends("sc_supplier_type_ids.name", "sc_supplier_type_ids.sequence", "sc_supplier_type")
    def _compute_sc_supplier_type_label(self):
        selection_labels = dict(SUPPLIER_TYPE_SELECTION)
        for partner in self:
            types = partner.sc_supplier_type_ids.sorted(lambda item: (item.sequence, item.id))
            if types:
                partner.sc_supplier_type_label = "、".join(types.mapped("name"))
            else:
                partner.sc_supplier_type_label = selection_labels.get(partner.sc_supplier_type or "", "")

    @api.depends("sc_blacklisted", "sc_blacklist_reason", "sc_blacklist_review_date")
    def _compute_sc_blacklist_advisory(self):
        for partner in self:
            suggestions = []
            if partner.sc_blacklisted and not partner.sc_blacklist_reason:
                suggestions.append("建议补充列入原因")
            if partner.sc_blacklisted and not partner.sc_blacklist_review_date:
                suggestions.append("建议设置复核日期")
            partner.sc_blacklist_advisory = "；".join(suggestions) if suggestions else "治理信息已完善"

    @api.depends("active", "sc_blacklisted", "sc_blacklist_level", "sc_blacklist_reason")
    def _compute_sc_transaction_eligibility(self):
        for partner in self:
            if not partner.active:
                partner.sc_transaction_eligibility = "blocked"
                partner.sc_transaction_eligibility_reason = "档案已归档，不允许发起新业务。"
            elif partner.sc_blacklisted and partner.sc_blacklist_level == "blocked":
                partner.sc_transaction_eligibility = "blocked"
                partner.sc_transaction_eligibility_reason = (
                    partner.sc_blacklist_reason or "风险级别为停止合作。"
                )
            elif partner.sc_blacklisted:
                partner.sc_transaction_eligibility = "review_required"
                partner.sc_transaction_eligibility_reason = (
                    partner.sc_blacklist_reason or "客商处于风险关注或限制合作状态。"
                )
            else:
                partner.sc_transaction_eligibility = "eligible"
                partner.sc_transaction_eligibility_reason = "档案有效，可正常发起业务。"

    def _sc_assert_transaction_eligible(self, business_label=None):
        """Fail closed when a document starts business with a blocked counterparty."""
        label = business_label or _("业务")
        blocked = self.filtered(
            lambda partner: partner.sc_transaction_eligibility == "blocked"
        )
        if blocked:
            details = "；".join(
                _(
                    "%(name)s：%(reason)s",
                    name=partner.display_name,
                    reason=partner.sc_transaction_eligibility_reason,
                )
                for partner in blocked
            )
            raise UserError(
                _("无法发起%(label)s。%(details)s", label=label, details=details)
            )
        return True

    def _check_sc_blacklist_permission(self):
        if self.env.su or self.env.user.has_group(
            "smart_construction_core.group_sc_cap_contact_manager"
        ) or self.env.user.has_group("smart_construction_core.group_sc_super_admin"):
            return
        raise UserError(_("你没有权限维护客商黑名单。"))

    def action_sc_add_blacklist(self):
        self._check_sc_blacklist_permission()
        self.filtered(lambda partner: not partner.sc_blacklisted).write(
            {
                "sc_blacklisted": True,
                "sc_blacklisted_at": fields.Datetime.now(),
                "sc_blacklisted_by": self.env.user.id,
            }
        )
        suggestions = [item for item in self.mapped("sc_blacklist_advisory") if item and item != "治理信息已完善"]
        if suggestions:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "已列入客商黑名单",
                    "message": "；".join(dict.fromkeys(suggestions)),
                    "type": "warning",
                    "sticky": False,
                },
            }
        return True

    def action_sc_remove_blacklist(self):
        self._check_sc_blacklist_permission()
        self.filtered("sc_blacklisted").write({"sc_blacklisted": False})
        return True

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.context.get("sc_skip_supplier_type_sync"):
            for record, vals in zip(records, vals_list):
                record._sc_sync_supplier_type_fields(vals)
        return records

    def write(self, vals):
        result = super().write(vals)
        if vals and not self.env.context.get("sc_skip_supplier_type_sync"):
            self._sc_sync_supplier_type_fields(vals)
        return result

    @api.model
    def _sc_backfill_supplier_type_ids(self):
        partners = self.sudo().with_context(active_test=False).search([("supplier_rank", ">", 0)])
        if not partners:
            return True

        type_by_code = {
            supplier_type.code: supplier_type
            for supplier_type in self.env["sc.supplier.type"].sudo().search([])
            if supplier_type.code
        }
        fallback_type = type_by_code.get("other")
        for partner in partners:
            supplier_type = type_by_code.get(partner.sc_supplier_type or "") or fallback_type
            if supplier_type and supplier_type not in partner.sc_supplier_type_ids:
                partner.with_context(sc_skip_supplier_type_sync=True).write(
                    {"sc_supplier_type_ids": [(4, supplier_type.id)]}
                )
        return True

    def _sc_sync_supplier_type_fields(self, vals):
        if not vals or self.env.context.get("sc_skip_supplier_type_sync"):
            return
        Type = self.env["sc.supplier.type"].sudo()
        for partner in self:
            if "sc_supplier_type_ids" in vals:
                first_type = partner.sc_supplier_type_ids.sorted(lambda item: (item.sequence, item.id))[:1]
                partner.with_context(sc_skip_supplier_type_sync=True).write(
                    {"sc_supplier_type": first_type.code if first_type else False}
                )
                continue
            if "sc_supplier_type" in vals and partner.sc_supplier_type:
                type_rec = Type.search([("code", "=", partner.sc_supplier_type)], limit=1)
                if type_rec and type_rec not in partner.sc_supplier_type_ids:
                    partner.with_context(sc_skip_supplier_type_sync=True).write(
                        {"sc_supplier_type_ids": [(4, type_rec.id)]}
                    )







    def unlink(self):
        self._sc_raise_delete_blockers(action_label="删除往来单位")
        return super().unlink()




class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    sc_account_holder_name = fields.Char(string="账户名称")
    sc_bank_name = fields.Char(string="开户银行", index=True)


class ResPartnerCategory(models.Model):
    """业务分类（客户/供应商分类实体）。

    Odoo 标准 res.partner.category 的英文模型名为 "Partner Tags"，
    本项目业务语义为“业务分类”（客户角色/行业/资质类别等），
    模型显示名统一为中文，供选择器、创建对话框等场景展示。
    """

    _inherit = "res.partner.category"
    _description = "业务分类"
