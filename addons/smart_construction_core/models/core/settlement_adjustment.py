# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


_DOCUMENT_STATE_TOKEN = object()


class ScSettlementAdjustment(models.Model):
    _name = "sc.settlement.adjustment"
    _description = "结算调整"
    _inherit = ["mail.thread", "mail.activity.mixin", "tier.validation"]
    _order = "date_adjustment desc, id desc"

    name = fields.Char(string="调整单号", required=True, default="新建", copy=False)
    source_origin = fields.Selection(
        [("manual", "新系统登记"), ("legacy", "历史迁移")],
        string="来源",
        default="manual",
        required=True,
        index=True,
    )
    adjustment_type = fields.Selection(
        [("deduction", "扣款"), ("addition", "调增")],
        string="调整类型",
        default="deduction",
        required=True,
        index=True,
    )
    state = fields.Selection(
        [
            ("draft", "草稿"),
            ("confirmed", "已确认"),
            ("cancel", "已取消"),
            ("legacy_confirmed", "历史已确认"),
        ],
        string="状态",
        default="draft",
        required=True,
        index=True,
    )
    project_id = fields.Many2one("project.project", string="项目", required=True, index=True)
    company_id = fields.Many2one(
        "res.company",
        string="公司",
        related="project_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    settlement_id = fields.Many2one("sc.settlement.order", string="结算单", index=True, ondelete="set null")
    contract_id = fields.Many2one("construction.contract", string="合同", index=True)
    partner_id = fields.Many2one("res.partner", string="往来单位", index=True)
    date_adjustment = fields.Date(string="调整日期", default=fields.Date.context_today, index=True)
    item_name = fields.Char(string="调整事项", index=True)
    account_name = fields.Char(string="扣款账户", index=True)
    amount = fields.Monetary(string="调整金额", currency_field="currency_id", required=True)
    signed_amount = fields.Monetary(
        string="影响金额",
        currency_field="currency_id",
        compute="_compute_signed_amount",
        store=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="币种",
        required=True,
        default=lambda self: self.env.company.currency_id.id,
    )
    legacy_line_id = fields.Char(string="历史行ID", index=True, readonly=True)
    legacy_document_no = fields.Char(string="历史单据号", index=True, readonly=True)
    legacy_document_state = fields.Char(string="历史单据状态", index=True, readonly=True)
    legacy_fund_confirmation_id = fields.Char(string="历史资金确认ID", index=True, readonly=True)
    legacy_source_table = fields.Char(string="历史来源表", readonly=True)
    reject_reason = fields.Char(string="驳回原因", readonly=True, copy=False)
    note = fields.Text(string="备注")
    active = fields.Boolean("有效", default=True, index=True)

    _sql_constraints = [
        ("legacy_line_unique", "unique(legacy_line_id)", "历史结算调整行记录必须唯一。"),
        ("amount_nonnegative", "CHECK(amount >= 0)", "Adjustment amount must be non-negative."),
    ]

    @api.depends("adjustment_type", "amount")
    def _compute_signed_amount(self):
        for rec in self:
            amount = rec.amount or 0.0
            rec.signed_amount = -amount if rec.adjustment_type == "deduction" else amount

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            state = values.get("state", self.env.context.get("default_state", "draft"))
            origin = values.get("source_origin", self.env.context.get("default_source_origin", "manual"))
            historical_import = self.env.su and origin == "legacy" and state == "legacy_confirmed"
            if origin == "legacy" and not self.env.su:
                raise UserError(_("历史单据只能由受管迁移导入。"))
            if state != "draft" and not historical_import:
                raise UserError(_("单据必须从草稿通过正式审批和业务动作流转。"))
        seq = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", "新建") == "新建":
                vals["name"] = seq.next_by_code("sc.settlement.adjustment") or _("结算调整")
            if vals.get("settlement_id"):
                settlement = self.env["sc.settlement.order"].browse(vals["settlement_id"])
                vals.setdefault("project_id", settlement.project_id.id)
                vals.setdefault("contract_id", settlement.contract_id.id)
                vals.setdefault("partner_id", settlement.partner_id.id)
                vals.setdefault("currency_id", settlement.currency_id.id)
        return super().create(vals_list)

    def write(self, vals):
        authoritative = self.env.context.get("sc_document_state_token") is _DOCUMENT_STATE_TOKEN
        if not authoritative and {"state", "source_origin"}.intersection(vals):
            raise UserError(_("单据状态与来源只能由正式业务动作写入。"))
        reviewed_fields = {
            "project_id", "company_id", "settlement_id", "contract_id", "partner_id",
            "adjustment_type", "date_adjustment", "item_name", "account_name",
            "amount", "currency_id", "active",
        }
        if not authoritative and reviewed_fields.intersection(vals) and any(
            rec.source_origin != "legacy" and (
                rec.state == "confirmed" or (
                    rec.state == "draft" and rec.validation_status in ("waiting", "pending", "validated")
                )
            ) for rec in self
        ):
            raise UserError(_("审批中或已确认的结算调整内容不可改写；请按正式流程重新办理。"))
        if any(rec.source_origin == "legacy" and rec.state == "legacy_confirmed" for rec in self):
            allowed = {"settlement_id", "contract_id", "partner_id", "note", "active", "write_uid", "write_date"}
            if set(vals) - allowed:
                raise UserError(_("历史迁移调整已确认，只允许补充业务锚点和备注。"))
        return super().write(vals)

    def _write_document_state(self, values):
        return self.with_context(sc_document_state_token=_DOCUMENT_STATE_TOKEN).write(values)

    def action_confirm(self):
        policy = self.env["sc.approval.policy"]
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("只有草稿状态的结算调整可以确认。"))
            rec._check_business_anchor()
            if not policy._start_submission_review(rec):
                rec._write_document_state({"state": "confirmed", "reject_reason": False})

    def action_cancel(self):
        for rec in self:
            if rec.source_origin == "legacy":
                raise UserError(_("历史迁移调整不能在新系统取消。"))
            if rec.state not in ("draft", "confirmed"):
                raise UserError(_("只有草稿或已确认状态的结算调整可以取消。"))
        self._write_document_state({"state": "cancel"})

    def _business_anchor_errors(self):
        self.ensure_one()
        errors = []
        if not self.item_name:
            errors.append(("SETTLEMENT_ADJUSTMENT_MISSING_ITEM", _("结算调整确认前必须维护调整事项。")))
        if (self.amount or 0.0) <= 0:
            errors.append(("SETTLEMENT_ADJUSTMENT_INVALID_AMOUNT", _("结算调整确认前调整金额必须大于 0。")))
        if not self.settlement_id and not self.contract_id:
            errors.append(("SETTLEMENT_ADJUSTMENT_MISSING_ANCHOR", _("结算调整确认前必须关联结算单或合同。")))
        for source in (self.settlement_id, self.contract_id):
            if not source:
                continue
            if self.project_id != source.project_id:
                errors.append(("SETTLEMENT_ADJUSTMENT_PROJECT_MISMATCH", _("结算调整项目必须与来源项目一致。")))
            if self.currency_id != source.currency_id:
                errors.append(("SETTLEMENT_ADJUSTMENT_CURRENCY_MISMATCH", _("结算调整币种必须与来源币种一致。")))
            if self.partner_id and self.partner_id != source.partner_id:
                errors.append(("SETTLEMENT_ADJUSTMENT_PARTNER_MISMATCH", _("结算调整往来单位必须与来源往来单位一致。")))
        if self.settlement_id and self.contract_id and self.contract_id != self.settlement_id.contract_id:
            errors.append(("SETTLEMENT_ADJUSTMENT_CONTRACT_MISMATCH", _("结算调整合同必须与来源结算单合同一致。")))
        return errors

    def _check_business_anchor(self):
        for rec in self:
            errors = rec._business_anchor_errors()
            if errors:
                raise UserError(errors[0][1])

    def _check_state_from_condition(self):
        self.ensure_one()
        parent = getattr(super(), "_check_state_from_condition", None)
        base_ok = parent() if parent else False
        return base_ok or self.state == "draft"

    def _get_tier_reject_reason(self):
        self.ensure_one()
        reviews = self.review_ids.filtered(lambda review: review.status == "rejected" and review.comment)
        if reviews:
            return reviews.sorted(lambda review: review.write_date or review.create_date, reverse=True)[0].comment
        return _("OCA审批驳回（未填写原因）")

    def action_on_tier_approved(self):
        for rec in self:
            if not rec.review_ids or rec.validation_status != "validated":
                # Intermediate or forged callbacks cannot create approval facts.
                continue
            if rec.state == "draft":
                rec._check_business_anchor()
                rec.with_context(skip_validation_check=True)._write_document_state({"state": "confirmed", "reject_reason": False})

    def action_on_tier_rejected(self, reason=None):
        for rec in self:
            if not rec.review_ids or rec.validation_status != "rejected":
                continue
            if rec.state == "draft":
                rec.with_context(skip_validation_check=True).write(
                    {"reject_reason": reason or rec._get_tier_reject_reason()}
                )


class ScSettlementOrder(models.Model):
    _inherit = "sc.settlement.order"

    adjustment_ids = fields.One2many("sc.settlement.adjustment", "settlement_id", string="结算调整")
    adjustment_total = fields.Monetary(
        string="调整合计",
        currency_field="currency_id",
        compute="_compute_adjustment_totals",
        store=True,
    )
    amount_after_adjustment = fields.Monetary(
        string="调整后金额",
        currency_field="currency_id",
        compute="_compute_adjustment_totals",
        store=True,
    )

    @api.depends("amount_total", "adjustment_ids.signed_amount", "adjustment_ids.state")
    def _compute_adjustment_totals(self):
        for order in self:
            adjustment_total = sum(
                order.adjustment_ids.filtered(lambda rec: rec.state in ("confirmed", "legacy_confirmed")).mapped(
                    "signed_amount"
                )
            )
            order.adjustment_total = adjustment_total
            order.amount_after_adjustment = (order.amount_total or 0.0) + adjustment_total
