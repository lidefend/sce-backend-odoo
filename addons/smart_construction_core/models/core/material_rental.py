# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare


_RENTAL_APPROVAL_STATE_TOKEN = object()


class ScMaterialRentalPlan(models.Model):
    _name = "sc.material.rental.plan"
    _description = "周转材料租赁计划"
    _inherit = ["mail.thread", "mail.activity.mixin", "tier.validation"]
    _state_from = ["draft", "submitted"]
    _state_to = ["approved"]
    company_id = fields.Many2one("res.company", related="project_id.company_id", store=True, readonly=True)
    reject_reason = fields.Text(string="审批驳回原因", readonly=True, copy=False)
    _order = "plan_date desc, id desc"

    name = fields.Char(string="计划单号", required=True, default="新建", tracking=True)
    project_id = fields.Many2one("project.project", string="项目", required=True, index=True, tracking=True)
    contract_id = fields.Many2one("construction.contract", string="关联合同", index=True)
    supplier_id = fields.Many2one("res.partner", string="建议供应商", index=True, tracking=True)
    plan_date = fields.Date(string="计划日期", required=True, default=fields.Date.context_today, index=True)
    planned_start = fields.Date(string="计划进场日期", index=True)
    planned_end = fields.Date(string="计划退场日期", index=True)
    rent_purpose = fields.Char(string="租赁用途", index=True)
    owner_id = fields.Many2one("res.users", string="负责人", default=lambda self: self.env.user, index=True)
    currency_id = fields.Many2one("res.currency", string="币种", required=True, default=lambda self: self.env.company.currency_id.id)
    estimated_amount = fields.Monetary(string="预计租赁金额", currency_field="currency_id", compute="_compute_estimated_amount", store=True)
    line_ids = fields.One2many("sc.material.rental.plan.line", "plan_id", string="计划明细")
    state = fields.Selection(
        [("draft", "草稿"), ("submitted", "已提交"), ("approved", "已确认"), ("cancel", "已取消")],
        string="状态",
        default="draft",
        required=True,
        index=True,
        tracking=True,
    )
    note = fields.Text(string="备注")
    legacy_fact_model = fields.Char(string="来源通用模型", index=True)
    legacy_fact_id = fields.Integer(string="来源通用记录ID", index=True)
    legacy_fact_type = fields.Char(string="来源业务类型", index=True)

    @api.depends("line_ids.estimated_amount")
    def _compute_estimated_amount(self):
        for record in self:
            record.estimated_amount = sum(record.line_ids.mapped("estimated_amount"))

    @api.model_create_multi
    def create(self, vals_list):
        if any(values.get("state", "draft") != "draft" for values in vals_list):
            raise UserError(_("状态必须通过办理动作产生。"))
        seq = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", "新建") == "新建":
                vals["name"] = seq.next_by_code("sc.material.rental.plan") or _("周转材料租赁计划")
        return super().create(vals_list)

    @api.constrains("planned_start", "planned_end")
    def _check_date_order(self):
        for record in self:
            if record.planned_start and record.planned_end and record.planned_start > record.planned_end:
                raise ValidationError(_("计划进场日期不能晚于计划退场日期。"))

    def write(self, vals):
        if "state" in vals and self.env.context.get("sc_rental_approval_state_token") is not _RENTAL_APPROVAL_STATE_TOKEN:
            raise UserError(_("状态必须通过办理动作产生。"))
        return super().write(vals)

    def _write_approval_state(self, vals):
        return self.with_context(sc_rental_approval_state_token=_RENTAL_APPROVAL_STATE_TOKEN).write(vals)

    def _get_tier_reject_reason(self):
        self.ensure_one()
        reviews = self.review_ids.filtered(lambda review: review.status == "rejected" and review.comment)
        if reviews:
            return reviews.sorted(lambda review: review.write_date or review.create_date, reverse=True)[0].comment
        return _("统一审批驳回（未填写原因）")

    def action_on_tier_approved(self):
        for record in self:
            if record.state == "submitted" and record.review_ids and record.validation_status == "validated":
                record._write_approval_state({"state": "approved", "reject_reason": False})

    def action_on_tier_rejected(self, reason=None):
        for record in self:
            if record.state == "submitted" and record.review_ids and record.validation_status == "rejected":
                record.with_context(skip_validation_check=True)._write_approval_state({"state": "draft", "reject_reason": reason or record._get_tier_reject_reason()})

    def action_submit(self):
        for record in self:
            if record.state not in ("draft", "submitted"):
                raise UserError(_("只有草稿或待重新提交的租赁计划可以提交。"))
            record._check_business_anchor()
        self.with_context(skip_validation_check=True)._write_approval_state({"state": "submitted"})
        for record in self:
            if not self.env["sc.approval.policy"]._start_submission_review(record):
                record._write_approval_state({"state": "approved", "reject_reason": False})
        return True

    def action_approve(self):
        self.ensure_one()
        return self.env["sc.approval.policy"]._approve_submission_review(self)

    def action_cancel(self):
        for record in self:
            if record.state not in ("draft", "submitted"):
                raise UserError(_("只有草稿或已提交租赁计划可以取消。"))
            record._write_approval_state({"state": "cancel"})
        return True

    def action_reset_draft(self):
        for record in self:
            if record.state != "cancel":
                raise UserError(_("只有已取消租赁计划可以重置为草稿。"))
            record._write_approval_state({"state": "draft"})
        return True

    def _check_business_anchor(self):
        for record in self:
            if not record.line_ids:
                raise UserError(_("租赁计划必须填写计划明细。"))
            if record.contract_id:
                if record.contract_id.project_id != record.project_id:
                    raise UserError(_("租赁计划关联合同必须属于当前项目。"))
                if record.contract_id.partner_id and record.supplier_id and record.contract_id.partner_id != record.supplier_id:
                    raise UserError(_("租赁计划建议供应商必须与合同相对方一致。"))
            for line in record.line_ids:
                if line.planned_qty <= 0:
                    raise UserError(_("计划租赁数量必须大于 0。"))
                if line.planned_days <= 0:
                    raise UserError(_("计划租赁天数必须大于 0。"))
                if line.daily_price < 0:
                    raise UserError(_("计划日租单价不能为负数。"))


class ScMaterialRentalPlanLine(models.Model):
    _name = "sc.material.rental.plan.line"
    _description = "周转材料租赁计划明细"
    _order = "plan_id, sequence, id"

    plan_id = fields.Many2one("sc.material.rental.plan", string="租赁计划", required=True, ondelete="cascade", index=True)
    sequence = fields.Integer(default=10)
    project_id = fields.Many2one("project.project", string="项目", related="plan_id.project_id", store=True, index=True)
    material_catalog_id = fields.Many2one("sc.material.catalog", string="材料档案", index=True)
    product_id = fields.Many2one("product.product", string="材料", index=True)
    material_name = fields.Char(string="材料名称", required=True)
    material_spec = fields.Char(string="规格型号")
    unit_name = fields.Char(string="单位")
    planned_qty = fields.Float(string="计划数量", default=1.0)
    planned_days = fields.Float(string="计划租赁天数", default=1.0)
    daily_price = fields.Monetary(string="日租单价", currency_field="currency_id")
    currency_id = fields.Many2one("res.currency", string="币种", related="plan_id.currency_id", store=True)
    estimated_amount = fields.Monetary(string="预计金额", currency_field="currency_id", compute="_compute_amount", store=True)
    note = fields.Char(string="备注")

    @api.depends("planned_qty", "planned_days", "daily_price")
    def _compute_amount(self):
        for line in self:
            line.estimated_amount = (line.planned_qty or 0.0) * (line.planned_days or 0.0) * (line.daily_price or 0.0)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._apply_material_catalog_defaults(vals)
        return super().create(vals_list)

    @api.model
    def _apply_material_catalog_defaults(self, vals):
        catalog = self.env["sc.material.catalog"].browse(vals.get("material_catalog_id")) if vals.get("material_catalog_id") else False
        if not catalog:
            return vals
        vals.setdefault("material_name", catalog.display_name)
        vals.setdefault("material_spec", catalog.spec_model or False)
        vals.setdefault("unit_name", catalog.uom_text or False)
        return vals

    @api.onchange("material_catalog_id")
    def _onchange_material_catalog_id(self):
        for line in self:
            catalog = line.material_catalog_id
            if not catalog:
                continue
            line.material_name = catalog.display_name
            line.material_spec = catalog.spec_model or line.material_spec
            line.unit_name = catalog.uom_text or line.unit_name

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for line in self:
            if line.product_id and not line.material_catalog_id:
                line.material_name = line.product_id.display_name
                line.material_spec = line.product_id.default_code or line.material_spec
                line.unit_name = line.product_id.uom_id.name or line.unit_name


class ScMaterialRentalOrder(models.Model):
    _name = "sc.material.rental.order"
    _description = "周转材料租赁单"
    _inherit = ["mail.thread", "mail.activity.mixin", "tier.validation"]
    _state_from = ["draft", "submitted"]
    _state_to = ["approved"]
    company_id = fields.Many2one("res.company", related="project_id.company_id", store=True, readonly=True)
    reject_reason = fields.Text(string="审批驳回原因", readonly=True, copy=False)
    _order = "rental_date desc, id desc"

    name = fields.Char(string="租赁单号", required=True, default="新建", tracking=True)
    project_id = fields.Many2one("project.project", string="项目", required=True, index=True, tracking=True)
    plan_id = fields.Many2one("sc.material.rental.plan", string="来源租赁计划", index=True)
    contract_id = fields.Many2one("construction.contract", string="租赁合同", index=True)
    supplier_id = fields.Many2one("res.partner", string="供应商", required=True, index=True, tracking=True)
    account_holder = fields.Char(string="开户人姓名", related="supplier_id.sc_account_name", store=True, readonly=True)
    bank_name = fields.Char(string="开户行", related="supplier_id.sc_bank_name", store=True, readonly=True, index=True)
    bank_account = fields.Char(string="银行账号", related="supplier_id.sc_bank_account", store=True, readonly=True, index=True)
    rental_date = fields.Date(string="租赁日期", required=True, default=fields.Date.context_today, index=True)
    planned_return_date = fields.Date(string="计划退还日期", index=True)
    actual_return_date = fields.Date(string="实际退还日期", index=True, tracking=True)
    use_unit_name = fields.Char(string="使用单位")
    owner_id = fields.Many2one("res.users", string="经办人", default=lambda self: self.env.user, index=True)
    currency_id = fields.Many2one("res.currency", string="币种", required=True, default=lambda self: self.env.company.currency_id.id)
    amount_total = fields.Monetary(string="租赁金额", currency_field="currency_id", compute="_compute_amount_total", store=True)
    deposit_amount = fields.Monetary(string="租赁押金", currency_field="currency_id")
    compensation_fee = fields.Monetary(string="赔偿费", currency_field="currency_id")
    repair_fee = fields.Monetary(string="维修费", currency_field="currency_id")
    transport_fee = fields.Monetary(string="进出场费", currency_field="currency_id")
    deposit_deduction = fields.Monetary(string="抵扣押金", currency_field="currency_id")
    settlement_amount = fields.Monetary(
        string="应结算金额",
        currency_field="currency_id",
        compute="_compute_settlement_amount",
        store=True,
        readonly=True,
    )
    material_summary = fields.Char(string="材料摘要", compute="_compute_line_summary", store=True, readonly=True)
    specification_summary = fields.Char(string="规格摘要", compute="_compute_line_summary", store=True, readonly=True)
    quantity_total = fields.Float(string="租赁数量", compute="_compute_line_summary", store=True, readonly=True)
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "sc_material_rental_order_attachment_rel",
        "order_id",
        "attachment_id",
        string="附件",
    )
    line_ids = fields.One2many("sc.material.rental.order.line", "order_id", string="租赁明细")
    state = fields.Selection(
        [("draft", "草稿"), ("submitted", "审批中"), ("approved", "已审批待启用"), ("active", "租赁中"), ("returned", "已退还"), ("settled", "已结算"), ("cancel", "已取消")],
        string="状态",
        default="draft",
        required=True,
        index=True,
        tracking=True,
    )
    note = fields.Text(string="备注")
    legacy_fact_model = fields.Char(string="来源通用模型", index=True)
    legacy_fact_id = fields.Integer(string="来源通用记录ID", index=True)
    legacy_fact_type = fields.Char(string="来源业务类型", index=True)

    @api.depends("line_ids.amount_total")
    def _compute_amount_total(self):
        for record in self:
            record.amount_total = sum(record.line_ids.mapped("amount_total"))

    @api.depends("amount_total", "compensation_fee", "repair_fee", "transport_fee", "deposit_deduction")
    def _compute_settlement_amount(self):
        for record in self:
            record.settlement_amount = max(
                (record.amount_total or 0.0)
                + (record.compensation_fee or 0.0)
                + (record.repair_fee or 0.0)
                + (record.transport_fee or 0.0)
                - (record.deposit_deduction or 0.0),
                0.0,
            )

    @api.depends("line_ids.material_name", "line_ids.material_spec", "line_ids.qty")
    def _compute_line_summary(self):
        for record in self:
            record.material_summary = "、".join(filter(None, record.line_ids.mapped("material_name")[:3])) or False
            record.specification_summary = "、".join(filter(None, record.line_ids.mapped("material_spec")[:3])) or False
            record.quantity_total = sum(record.line_ids.mapped("qty"))

    @api.model_create_multi
    def create(self, vals_list):
        if any(values.get("state", "draft") != "draft" for values in vals_list):
            raise UserError(_("状态必须通过办理动作产生。"))
        seq = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", "新建") == "新建":
                vals["name"] = seq.next_by_code("sc.material.rental.order") or _("周转材料租赁单")
        return super().create(vals_list)

    def write(self, vals):
        if "state" in vals and self.env.context.get("sc_rental_approval_state_token") is not _RENTAL_APPROVAL_STATE_TOKEN:
            raise UserError(_("状态必须通过办理动作产生。"))
        return super().write(vals)

    def _write_approval_state(self, vals):
        return self.with_context(sc_rental_approval_state_token=_RENTAL_APPROVAL_STATE_TOKEN).write(vals)

    def _get_tier_reject_reason(self):
        self.ensure_one()
        reviews = self.review_ids.filtered(lambda review: review.status == "rejected" and review.comment)
        if reviews:
            return reviews.sorted(lambda review: review.write_date or review.create_date, reverse=True)[0].comment
        return _("统一审批驳回（未填写原因）")

    def action_on_tier_approved(self):
        for record in self:
            if record.state == "submitted" and record.review_ids and record.validation_status == "validated":
                record._write_approval_state({"state": "approved", "reject_reason": False})

    def action_on_tier_rejected(self, reason=None):
        for record in self:
            if record.state == "submitted" and record.review_ids and record.validation_status == "rejected":
                record.with_context(skip_validation_check=True)._write_approval_state({"state": "draft", "reject_reason": reason or record._get_tier_reject_reason()})

    def action_submit(self):
        for record in self:
            if record.state not in ("draft", "submitted"):
                raise UserError(_("只有草稿或待重新提交的租赁单可以提交。"))
            record._check_business_anchor()
        self.with_context(skip_validation_check=True)._write_approval_state({"state": "submitted"})
        for record in self:
            if not self.env["sc.approval.policy"]._start_submission_review(record):
                record._write_approval_state({"state": "approved", "reject_reason": False})
        return True

    def action_activate(self):
        for record in self:
            if record.state != "approved":
                raise UserError(_("只有已审批租赁单可以启用。"))
            self.env["sc.approval.policy"]._assert_submission_approved(record, ("approved",))
            record._check_business_anchor()
            record._write_approval_state({"state": "active"})
        return True

    def action_return(self):
        for record in self:
            if record.state != "active":
                raise UserError(_("只有租赁中的租赁单可以退还。"))
            record._check_business_anchor()
            record._write_approval_state({"state": "returned", "actual_return_date": record.actual_return_date or fields.Date.context_today(record)})
        return True

    def action_settle(self):
        for record in self:
            if record.state != "returned":
                raise UserError(_("只有已退还的租赁单可以结算。"))
            record._check_business_anchor()
            record._write_approval_state({"state": "settled"})
        return True

    def action_cancel(self):
        for record in self:
            if record.state not in ("draft", "submitted", "approved", "active"):
                raise UserError(_("只有尚未退还或结算的租赁单可以取消。"))
            record._write_approval_state({"state": "cancel"})
        return True

    def _check_business_anchor(self):
        for record in self:
            if not record.line_ids:
                raise UserError(_("租赁单必须填写租赁明细。"))
            if record.plan_id:
                if record.plan_id.project_id != record.project_id:
                    raise UserError(_("租赁单来源计划必须属于当前项目。"))
                if record.plan_id.state != "approved":
                    raise UserError(_("租赁单来源计划必须已确认。"))
            if record.contract_id:
                if record.contract_id.project_id != record.project_id:
                    raise UserError(_("租赁合同必须属于当前项目。"))
                if record.contract_id.partner_id and record.contract_id.partner_id != record.supplier_id:
                    raise UserError(_("租赁单供应商必须与租赁合同相对方一致。"))
            for line in record.line_ids:
                if line.qty <= 0:
                    raise UserError(_("租赁数量必须大于 0。"))
                if line.rental_days <= 0:
                    raise UserError(_("租赁天数必须大于 0。"))
                if line.daily_price < 0:
                    raise UserError(_("日租单价不能为负数。"))


class ScMaterialRentalOrderLine(models.Model):
    _name = "sc.material.rental.order.line"
    _description = "周转材料租赁明细"
    _order = "order_id, sequence, id"

    order_id = fields.Many2one("sc.material.rental.order", string="租赁单", required=True, ondelete="cascade", index=True)
    sequence = fields.Integer(default=10)
    material_catalog_id = fields.Many2one("sc.material.catalog", string="材料档案", index=True)
    product_id = fields.Many2one("product.product", string="材料", index=True)
    material_name = fields.Char(string="材料名称", required=True)
    material_spec = fields.Char(string="规格型号")
    unit_name = fields.Char(string="单位")
    qty = fields.Float(string="租赁数量", default=1.0)
    rental_days = fields.Float(string="租赁天数", default=1.0)
    daily_price = fields.Monetary(string="日租单价", currency_field="currency_id")
    currency_id = fields.Many2one("res.currency", string="币种", related="order_id.currency_id", store=True)
    amount_total = fields.Monetary(string="租赁金额", currency_field="currency_id", compute="_compute_amount_total", store=True)
    returned_qty = fields.Float(string="已退还数量")
    damage_qty = fields.Float(string="损坏数量")
    note = fields.Char(string="备注")

    @api.depends("qty", "rental_days", "daily_price")
    def _compute_amount_total(self):
        for line in self:
            line.amount_total = (line.qty or 0.0) * (line.rental_days or 0.0) * (line.daily_price or 0.0)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._apply_material_catalog_defaults(vals)
        return super().create(vals_list)

    @api.model
    def _apply_material_catalog_defaults(self, vals):
        catalog = self.env["sc.material.catalog"].browse(vals.get("material_catalog_id")) if vals.get("material_catalog_id") else False
        if not catalog:
            return vals
        vals.setdefault("material_name", catalog.display_name)
        vals.setdefault("material_spec", catalog.spec_model or False)
        vals.setdefault("unit_name", catalog.uom_text or False)
        return vals

    @api.onchange("material_catalog_id")
    def _onchange_material_catalog_id(self):
        for line in self:
            catalog = line.material_catalog_id
            if not catalog:
                continue
            line.material_name = catalog.display_name
            line.material_spec = catalog.spec_model or line.material_spec
            line.unit_name = catalog.uom_text or line.unit_name

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for line in self:
            if line.product_id and not line.material_catalog_id:
                line.material_name = line.product_id.display_name
                line.material_spec = line.product_id.default_code or line.material_spec
                line.unit_name = line.product_id.uom_id.name or line.unit_name


class ScMaterialRentalSettlement(models.Model):
    _name = "sc.material.rental.settlement"
    _description = "周转材料租赁结算"
    _inherit = ["mail.thread", "mail.activity.mixin", "tier.validation"]
    _state_from = ["draft", "submitted"]
    _state_to = ["approved"]
    company_id = fields.Many2one("res.company", related="project_id.company_id", store=True, readonly=True)
    reject_reason = fields.Text(string="审批驳回原因", readonly=True, copy=False)
    _order = "settlement_date desc, id desc"

    name = fields.Char(string="结算单号", required=True, default="新建", tracking=True)
    project_id = fields.Many2one("project.project", string="项目", required=True, index=True, tracking=True)
    rental_order_id = fields.Many2one("sc.material.rental.order", string="租赁单", index=True)
    contract_id = fields.Many2one("construction.contract", string="租赁合同", index=True)
    supplier_id = fields.Many2one("res.partner", string="供应商", required=True, index=True, tracking=True)
    payment_request_id = fields.Many2one("payment.request", string="支付申请", index=True)
    # The historical single link is not payment allocation authority. New
    # attribution lives on each request; a settlement can have many requests.
    payment_allocation_revision = fields.Integer(default=0, readonly=True, copy=False)
    payment_request_ids = fields.One2many(
        "payment.request", "rental_settlement_id", string="归属付款申请", readonly=True,
    )
    settlement_date = fields.Date(string="结算日期", required=True, default=fields.Date.context_today, index=True)
    owner_id = fields.Many2one("res.users", string="经办人", default=lambda self: self.env.user, index=True)
    currency_id = fields.Many2one("res.currency", string="币种", required=True, default=lambda self: self.env.company.currency_id.id)
    rent_amount = fields.Monetary(string="租金金额", currency_field="currency_id", compute="_compute_amounts", store=True)
    damage_amount = fields.Monetary(string="赔偿金额", currency_field="currency_id", compute="_compute_amounts", store=True)
    amount_total = fields.Monetary(string="结算金额", currency_field="currency_id", compute="_compute_amounts", store=True)
    payment_paid_amount = fields.Monetary(
        string="实际已付金额", currency_field="currency_id",
        compute="_compute_payment_summary", readonly=True,
    )
    payment_remaining_amount = fields.Monetary(
        string="实际未付金额", currency_field="currency_id",
        compute="_compute_payment_summary", readonly=True,
    )
    line_ids = fields.One2many("sc.material.rental.settlement.line", "settlement_id", string="结算明细")
    state = fields.Selection(
        [("draft", "草稿"), ("submitted", "审批中"), ("approved", "已审批待确认"), ("confirmed", "已确认"), ("paid", "已支付"), ("cancel", "已取消")],
        string="状态",
        default="draft",
        required=True,
        index=True,
        tracking=True,
    )
    note = fields.Text(string="备注")
    legacy_fact_model = fields.Char(string="来源通用模型", index=True)
    legacy_fact_id = fields.Integer(string="来源通用记录ID", index=True)
    legacy_fact_type = fields.Char(string="来源业务类型", index=True)

    @api.depends("line_ids.rent_amount", "line_ids.damage_amount")
    def _compute_amounts(self):
        for record in self:
            record.rent_amount = sum(record.line_ids.mapped("rent_amount"))
            record.damage_amount = sum(record.line_ids.mapped("damage_amount"))
            record.amount_total = record.rent_amount + record.damage_amount

    @api.model_create_multi
    def create(self, vals_list):
        if any("payment_allocation_revision" in values for values in vals_list):
            raise UserError(_("付款额度版本只能由付款依据服务维护。"))
        if any(values.get("state", "draft") != "draft" for values in vals_list):
            raise UserError(_("状态必须通过办理动作产生。"))
        seq = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", "新建") == "新建":
                vals["name"] = seq.next_by_code("sc.material.rental.settlement") or _("周转材料租赁结算")
        return super().create(vals_list)

    def _lock_payment_basis(self):
        ids = sorted(record_id for record_id in self.ids if isinstance(record_id, int) and record_id > 0)
        if ids:
            self.env.cr.execute(
                "SELECT id FROM sc_material_rental_settlement WHERE id IN %s ORDER BY id FOR UPDATE",
                [tuple(ids)],
            )
            self.invalidate_recordset()

    def _serialize_payment_reservation(self):
        # A lock alone does not refresh a REPEATABLE READ snapshot. Touch the
        # shared source row so competing allocations conflict and retry using
        # a fresh transaction instead of both accepting an old aggregate.
        self._lock_payment_basis()
        for record in self:
            # Finance may reserve a readable settlement without being allowed
            # to edit its business facts. Elevation is confined to this counter.
            record.sudo()._write_approval_state({
                "payment_allocation_revision": record.payment_allocation_revision + 1,
            })

    def _assert_business_facts_editable(self):
        self._lock_payment_basis()
        if any(record.state != "draft" for record in self):
            raise UserError(_("租赁结算提交后，项目、供应商、合同、币种及结算明细不可修改；驳回后可在草稿中修订。"))

    def write(self, vals):
        if "payment_allocation_revision" in vals and self.env.context.get("sc_rental_approval_state_token") is not _RENTAL_APPROVAL_STATE_TOKEN:
            raise UserError(_("付款额度版本只能由付款依据服务维护。"))
        business_fields = {
            "project_id", "supplier_id", "contract_id", "currency_id",
            "rental_order_id", "settlement_date", "line_ids",
            "rent_amount", "damage_amount", "amount_total",
        }
        if business_fields.intersection(vals):
            self._assert_business_facts_editable()
        if "state" in vals and self.env.context.get("sc_rental_approval_state_token") is not _RENTAL_APPROVAL_STATE_TOKEN:
            raise UserError(_("状态必须通过办理动作产生。"))
        return super().write(vals)

    def _write_approval_state(self, vals):
        return self.with_context(sc_rental_approval_state_token=_RENTAL_APPROVAL_STATE_TOKEN).write(vals)

    def _get_tier_reject_reason(self):
        self.ensure_one()
        reviews = self.review_ids.filtered(lambda review: review.status == "rejected" and review.comment)
        if reviews:
            return reviews.sorted(lambda review: review.write_date or review.create_date, reverse=True)[0].comment
        return _("统一审批驳回（未填写原因）")

    def action_on_tier_approved(self):
        for record in self:
            if record.state == "submitted" and record.review_ids and record.validation_status == "validated":
                record._write_approval_state({"state": "approved", "reject_reason": False})

    def action_on_tier_rejected(self, reason=None):
        for record in self:
            if record.state == "submitted" and record.review_ids and record.validation_status == "rejected":
                record.with_context(skip_validation_check=True)._write_approval_state({"state": "draft", "reject_reason": reason or record._get_tier_reject_reason()})

    def action_submit(self):
        self._lock_payment_basis()
        for record in self:
            if record.state not in ("draft", "submitted"):
                raise UserError(_("只有草稿或待重新提交的租赁结算可以提交。"))
            record._check_business_anchor()
        self.with_context(skip_validation_check=True)._write_approval_state({"state": "submitted"})
        for record in self:
            if not self.env["sc.approval.policy"]._start_submission_review(record):
                record._write_approval_state({"state": "approved", "reject_reason": False})
        return True

    def action_confirm(self):
        for record in self:
            if record.state != "approved":
                raise UserError(_("只有已审批租赁结算可以确认。"))
            self.env["sc.approval.policy"]._assert_submission_approved(record, ("approved",))
            record._check_business_anchor()
            record._write_approval_state({"state": "confirmed"})
        return True

    def _payment_reserved_amount(self, exclude_request_id=False):
        self.ensure_one()
        domain = [
            ("rental_settlement_id", "=", self.id),
            ("state", "not in", ("draft", "rejected", "cancel")),
        ]
        if exclude_request_id:
            domain.append(("id", "!=", exclude_request_id))
        rows = self.env["payment.request"].sudo().read_group(domain, ["amount:sum"], [])
        return rows[0].get("amount_sum", rows[0].get("amount", 0.0)) if rows else 0.0

    def _payment_unreserved_amount(self):
        self.ensure_one()
        return max(self.amount_total - self._payment_reserved_amount(), 0.0)

    def _assert_no_live_payment_obligations(self):
        self._lock_payment_basis()
        for record in self:
            requests = record.sudo().with_context(active_test=False).payment_request_ids
            if requests.filtered(lambda request: request.state not in ("draft", "rejected", "cancel")):
                raise UserError(_("租赁结算仍有关联的在途或已办结付款申请，不能取消。"))
            if requests.mapped("ledger_line_ids").filtered(lambda ledger: ledger.state == "posted"):
                raise UserError(_("租赁结算仍有有效付款台账，不能取消。"))

    @api.depends(
        "amount_total", "payment_request_ids",
        "payment_request_ids.ledger_line_ids.amount",
        "payment_request_ids.ledger_line_ids.state",
        "payment_request_ids.ledger_line_ids.normalization_state",
    )
    def _compute_payment_summary(self):
        requests = self.sudo().with_context(active_test=False).mapped("payment_request_ids")
        paid_map = requests._canonical_payment_paid_amount_map()
        for record in self:
            attributed = record.sudo().with_context(active_test=False).payment_request_ids
            paid = sum(paid_map.get(request.id, 0.0) for request in attributed)
            record.payment_paid_amount = paid
            record.payment_remaining_amount = max(record.amount_total - paid, 0.0)

    def _payment_confirmation_blocker(self):
        self.ensure_one()
        requests = self.sudo().with_context(active_test=False).payment_request_ids
        if not requests:
            return {
                "reason_code": "RENTAL_PAYMENT_ATTRIBUTION_MISSING",
                "message": _("没有明确归属本结算的付款申请，不能确认已支付。"),
            }
        rounding = self.currency_id.rounding or 0.01
        if float_compare(self.amount_total, 0.0, precision_rounding=rounding) <= 0:
            return {
                "reason_code": "RENTAL_PAYMENT_AMOUNT_INVALID",
                "message": _("结算金额必须大于零才能确认实际支付。"),
            }
        if requests._ambiguous_posted_payment_request_ids():
            return {
                "reason_code": "RENTAL_PAYMENT_HISTORY_AMBIGUOUS",
                "message": _("归属付款申请存在身份不完整或不一致的有效台账，请先核对付款事实。"),
            }
        if float_compare(self.payment_paid_amount, self.amount_total, precision_rounding=rounding) < 0:
            return {
                "reason_code": "RENTAL_PAYMENT_NOT_FULLY_PAID",
                "message": _("本结算的有效付款台账尚未足额，不能确认已支付。"),
            }
        return None

    def _refresh_payment_confirmation(self):
        # Reversal and explicit paid confirmation serialize on the same source
        # version even when reversal finds a still-confirmed settlement.
        self._serialize_payment_reservation()
        for record in self:
            if record.state == "paid" and record._payment_confirmation_blocker():
                record._write_approval_state({"state": "confirmed"})

    def action_paid(self):
        self._lock_payment_basis()
        for record in self:
            if record.state != "confirmed":
                raise UserError(_("只有已确认租赁结算可以支付。"))
            record._check_business_anchor()
            blocker = record._payment_confirmation_blocker()
            if blocker:
                raise UserError("[%s] %s" % (blocker["reason_code"], blocker["message"]))
            record._write_approval_state({"state": "paid"})
        return True

    def action_cancel(self):
        self._assert_no_live_payment_obligations()
        for record in self:
            if record.state not in ("draft", "submitted", "approved", "confirmed"):
                raise UserError(_("只有未支付租赁结算可以取消。"))
            record._write_approval_state({"state": "cancel"})
        return True

    def _check_business_anchor(self):
        for record in self:
            if not record.line_ids:
                raise UserError(_("租赁结算必须填写结算明细。"))
            if record.rental_order_id:
                if record.rental_order_id.project_id != record.project_id:
                    raise UserError(_("租赁结算来源租赁单必须属于当前项目。"))
                if record.rental_order_id.state not in ("returned", "settled"):
                    raise UserError(_("租赁结算来源租赁单必须已退还或已结算。"))
                if record.rental_order_id.supplier_id != record.supplier_id:
                    raise UserError(_("租赁结算供应商必须与来源租赁单一致。"))
            if record.contract_id:
                if record.contract_id.project_id != record.project_id:
                    raise UserError(_("租赁结算合同必须属于当前项目。"))
                if record.contract_id.partner_id and record.contract_id.partner_id != record.supplier_id:
                    raise UserError(_("租赁结算供应商必须与合同相对方一致。"))
            if record.payment_request_id:
                if record.payment_request_id.project_id != record.project_id:
                    raise UserError(_("租赁结算支付申请必须属于当前项目。"))
                if record.payment_request_id.partner_id and record.payment_request_id.partner_id != record.supplier_id:
                    raise UserError(_("租赁结算供应商必须与支付申请收款方一致。"))
            for line in record.line_ids:
                if line.qty <= 0:
                    raise UserError(_("租赁结算数量必须大于 0。"))
                if line.rental_days <= 0:
                    raise UserError(_("租赁结算天数必须大于 0。"))
                if line.daily_price < 0 or line.damage_amount < 0:
                    raise UserError(_("租赁结算金额不能为负数。"))


class ScMaterialRentalSettlementLine(models.Model):
    _name = "sc.material.rental.settlement.line"
    _description = "周转材料租赁结算明细"
    _order = "settlement_id, sequence, id"

    settlement_id = fields.Many2one("sc.material.rental.settlement", string="租赁结算", required=True, ondelete="cascade", index=True)
    sequence = fields.Integer(default=10)
    material_catalog_id = fields.Many2one("sc.material.catalog", string="材料档案", index=True)
    product_id = fields.Many2one("product.product", string="材料", index=True)
    material_name = fields.Char(string="材料名称", required=True)
    material_spec = fields.Char(string="规格型号")
    unit_name = fields.Char(string="单位")
    qty = fields.Float(string="结算数量", default=1.0)
    rental_days = fields.Float(string="结算天数", default=1.0)
    daily_price = fields.Monetary(string="日租单价", currency_field="currency_id")
    damage_amount = fields.Monetary(string="赔偿金额", currency_field="currency_id")
    currency_id = fields.Many2one("res.currency", string="币种", related="settlement_id.currency_id", store=True)
    rent_amount = fields.Monetary(string="租金金额", currency_field="currency_id", compute="_compute_rent_amount", store=True)
    note = fields.Char(string="备注")

    @api.depends("qty", "rental_days", "daily_price")
    def _compute_rent_amount(self):
        for line in self:
            line.rent_amount = (line.qty or 0.0) * (line.rental_days or 0.0) * (line.daily_price or 0.0)

    @api.model_create_multi
    def create(self, vals_list):
        parent_ids = {vals.get("settlement_id") or self.env.context.get("default_settlement_id") for vals in vals_list}
        self.env["sc.material.rental.settlement"].browse([value for value in parent_ids if value])._assert_business_facts_editable()
        for vals in vals_list:
            self._apply_material_catalog_defaults(vals)
        return super().create(vals_list)

    def write(self, vals):
        business_fields = {
            "settlement_id", "material_catalog_id", "product_id", "material_name",
            "material_spec", "unit_name", "qty", "rental_days", "daily_price",
            "damage_amount", "currency_id", "rent_amount",
        }
        if business_fields.intersection(vals):
            parents = self.mapped("settlement_id")
            if vals.get("settlement_id"):
                parents |= self.env["sc.material.rental.settlement"].browse(vals["settlement_id"])
            parents._assert_business_facts_editable()
        return super().write(vals)

    def unlink(self):
        self.mapped("settlement_id")._assert_business_facts_editable()
        return super().unlink()

    @api.model
    def _apply_material_catalog_defaults(self, vals):
        catalog = self.env["sc.material.catalog"].browse(vals.get("material_catalog_id")) if vals.get("material_catalog_id") else False
        if not catalog:
            return vals
        vals.setdefault("material_name", catalog.display_name)
        vals.setdefault("material_spec", catalog.spec_model or False)
        vals.setdefault("unit_name", catalog.uom_text or False)
        return vals

    @api.onchange("material_catalog_id")
    def _onchange_material_catalog_id(self):
        for line in self:
            catalog = line.material_catalog_id
            if not catalog:
                continue
            line.material_name = catalog.display_name
            line.material_spec = catalog.spec_model or line.material_spec
            line.unit_name = catalog.uom_text or line.unit_name

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for line in self:
            if line.product_id and not line.material_catalog_id:
                line.material_name = line.product_id.display_name
                line.material_spec = line.product_id.default_code or line.material_spec
                line.unit_name = line.product_id.uom_id.name or line.unit_name
