# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class ScTaxFiling(models.Model):
    _name = "sc.tax.filing"
    _description = "税务申报"
    _inherit = ["mail.thread", "mail.activity.mixin", "sc.delete.guard.mixin"]
    _order = "period_end desc, id desc"
    _check_company_auto = True

    name = fields.Char(string="申报编号", required=True, default="新建", copy=False, index=True, tracking=True)
    company_id = fields.Many2one("res.company", string="申报公司", required=True, default=lambda self: self.env.company, index=True, tracking=True)
    period_start = fields.Date(string="申报期起", required=True, index=True, tracking=True)
    period_end = fields.Date(string="申报期止", required=True, index=True, tracking=True)
    state = fields.Selection(
        [("draft", "草稿"), ("calculated", "已测算"), ("submitted", "已申报"), ("accepted", "已受理"), ("cancelled", "已取消")],
        string="状态", required=True, default="draft", copy=False, index=True, tracking=True,
    )
    currency_id = fields.Many2one("res.currency", string="币种", required=True, related="company_id.currency_id", readonly=True)
    output_tax_amount = fields.Monetary(string="销项税额", currency_field="currency_id", readonly=True)
    input_tax_amount = fields.Monetary(string="进项税额", currency_field="currency_id", readonly=True)
    deductible_tax_amount = fields.Monetary(string="已认证抵扣税额", currency_field="currency_id", readonly=True)
    prepaid_tax_amount = fields.Monetary(string="已预缴税额", currency_field="currency_id", readonly=True)
    surcharge_amount = fields.Monetary(string="附加税额", currency_field="currency_id", readonly=True)
    vat_payable_amount = fields.Monetary(string="增值税应纳额", currency_field="currency_id", readonly=True)
    other_tax_adjustment = fields.Monetary(string="其他税费调整", currency_field="currency_id", tracking=True)
    declared_payable_amount = fields.Monetary(string="本期申报应纳额", currency_field="currency_id", compute="_compute_declared_payable", store=True)
    invoice_source_count = fields.Integer(string="发票来源数", readonly=True)
    deduction_source_count = fields.Integer(string="抵扣来源数", readonly=True)
    calculated_at = fields.Datetime(string="最近测算时间", readonly=True)
    submitted_at = fields.Datetime(string="申报时间", readonly=True)
    accepted_at = fields.Datetime(string="受理时间", readonly=True)
    handler_id = fields.Many2one("res.users", string="经办人", required=True, default=lambda self: self.env.user, tracking=True)
    declaration_no = fields.Char(string="申报回执号", index=True, tracking=True)
    note = fields.Text(string="说明")
    attachment_ids = fields.Many2many("ir.attachment", "sc_tax_filing_attachment_rel", "filing_id", "attachment_id", string="申报附件")

    _sql_constraints = [
        ("tax_filing_company_period_unique", "unique(company_id, period_start, period_end)", "同一公司同一申报期间只能建立一份税务申报。"),
    ]

    @api.depends("vat_payable_amount", "surcharge_amount", "other_tax_adjustment")
    def _compute_declared_payable(self):
        for record in self:
            record.declared_payable_amount = record.vat_payable_amount + record.surcharge_amount + record.other_tax_adjustment

    @api.constrains("period_start", "period_end")
    def _check_period(self):
        if self.filtered(lambda record: record.period_start and record.period_end and record.period_start > record.period_end):
            raise ValidationError(_("申报期起不能晚于申报期止。"))

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", "新建") == "新建":
                vals["name"] = sequence.next_by_code("sc.tax.filing") or "新建"
        return super().create(vals_list)

    def _require_manager(self):
        if not self.env.user.has_group("smart_construction_core.group_sc_cap_finance_manager"):
            raise AccessError(_("只有财务管理人员可以执行税务申报状态操作。"))

    def _invoice_domain(self):
        self.ensure_one()
        return [
            ("company_id", "=", self.company_id.id),
            ("invoice_date", ">=", self.period_start),
            ("invoice_date", "<=", self.period_end),
            ("state", "in", ("confirmed", "registered", "legacy_confirmed")),
        ]

    def _deduction_domain(self):
        self.ensure_one()
        return [
            ("company_id", "=", self.company_id.id),
            ("state", "in", ("confirmed", "deducted", "legacy_confirmed")),
            "|",
            "&", ("deduction_confirm_date", ">=", self.period_start), ("deduction_confirm_date", "<=", self.period_end),
            "&", ("deduction_confirm_date", "=", False), "&", ("document_date", ">=", self.period_start), ("document_date", "<=", self.period_end),
        ]

    def action_calculate(self):
        self._require_manager()
        for record in self:
            if record.state not in ("draft", "calculated"):
                raise UserError(_("只有草稿或已测算申报允许重新测算。"))
            invoices = self.env["sc.invoice.registration"].search(record._invoice_domain())
            deductions = self.env["sc.tax.deduction.registration"].search(record._deduction_domain())
            output_tax = sum(invoices.filtered(lambda item: item.direction == "output").mapped("tax_amount"))
            input_tax = sum(invoices.filtered(lambda item: item.direction == "input").mapped("tax_amount"))
            prepaid_tax = sum(invoices.filtered(lambda item: item.direction == "prepaid" or item.source_kind == "prepaid_tax").mapped("tax_amount"))
            deductible_tax = sum(deductions.filtered(lambda item: not item.is_transfer_out).mapped("deduction_tax_amount"))
            deductible_tax -= sum(deductions.filtered("is_transfer_out").mapped("deduction_tax_amount"))
            surcharge = sum(invoices.filtered(lambda item: item.direction in ("output", "prepaid")).mapped("surcharge_amount"))
            record.write({
                "state": "calculated", "output_tax_amount": output_tax, "input_tax_amount": input_tax,
                "deductible_tax_amount": deductible_tax, "prepaid_tax_amount": prepaid_tax,
                "surcharge_amount": surcharge, "vat_payable_amount": max(output_tax - deductible_tax - prepaid_tax, 0.0),
                "invoice_source_count": len(invoices), "deduction_source_count": len(deductions), "calculated_at": fields.Datetime.now(),
            })
        return True

    def action_submit(self):
        self._require_manager()
        if self.filtered(lambda record: record.state != "calculated"):
            raise UserError(_("请先完成本期税额测算。"))
        self.write({"state": "submitted", "submitted_at": fields.Datetime.now()})
        return True

    def action_accept(self):
        self._require_manager()
        if self.filtered(lambda record: record.state != "submitted"):
            raise UserError(_("只有已申报记录可以登记受理。"))
        self.write({"state": "accepted", "accepted_at": fields.Datetime.now()})
        return True

    def action_cancel(self):
        self._require_manager()
        if self.filtered(lambda record: record.state == "accepted"):
            raise UserError(_("已受理申报不能直接取消。"))
        self.write({"state": "cancelled"})
        return True

    def _source_action(self, name, model, domain):
        return {"type": "ir.actions.act_window", "name": name, "res_model": model, "view_mode": "tree,form", "domain": domain, "context": {"create": False}}

    def action_open_invoices(self):
        self.ensure_one()
        return self._source_action(_("申报期发票来源"), "sc.invoice.registration", self._invoice_domain())

    def action_open_deductions(self):
        self.ensure_one()
        return self._source_action(_("申报期抵扣来源"), "sc.tax.deduction.registration", self._deduction_domain())

    def unlink(self):
        if self.filtered(lambda record: record.state != "draft"):
            raise UserError(_("仅草稿税务申报允许删除。"))
        self._sc_raise_delete_blockers(action_label="删除税务申报")
        return super().unlink()
