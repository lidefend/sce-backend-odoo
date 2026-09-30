# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


_RED_FLUSH_STATE_TOKEN = object()


class ScOutputInvoiceAdjustment(models.Model):
    _name = "sc.output.invoice.adjustment"
    _description = "销项变更登记"
    _inherit = ["mail.thread", "mail.activity.mixin", "tier.validation"]
    _state_from = ["submitted"]
    _state_to = ["approved"]
    company_id = fields.Many2one(related="project_id.company_id", store=True, readonly=True)
    reject_reason = fields.Text("驳回原因", readonly=True, copy=False)
    _order = "adjustment_date desc, id desc"

    name = fields.Char(string="变更单号", required=True, default="新建", copy=False, tracking=True)
    adjustment_type = fields.Selection(
        [("red_flush", "红冲")],
        string="变更类型",
        default="red_flush",
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        [("draft", "草稿"), ("submitted", "待审批"), ("approved", "已通过"), ("rejected", "已驳回"), ("confirmed", "已确认"), ("cancel", "已取消")],
        string="状态",
        default="draft",
        required=True,
        index=True,
        tracking=True,
    )
    adjustment_date = fields.Date(string="变更日期", default=fields.Date.context_today, required=True, index=True)
    original_ledger_id = fields.Many2one(
        "sc.output.invoice.ledger",
        string="需红冲销项票",
        required=True,
        domain=[("active", "=", True), ("adjustment_kind", "=", "normal")],
        ondelete="restrict",
        tracking=True,
    )
    generated_invoice_id = fields.Many2one(
        "sc.invoice.registration",
        string="生成红冲销项票",
        readonly=True,
        copy=False,
        ondelete="restrict",
    )
    project_id = fields.Many2one("project.project", string="项目", readonly=True, index=True)
    partner_id = fields.Many2one("res.partner", string="往来单位", readonly=True, index=True)
    contract_id = fields.Many2one("construction.contract", string="合同", readonly=True, index=True)
    currency_id = fields.Many2one(
        "res.currency",
        string="币种",
        required=True,
        default=lambda self: self.env.company.currency_id.id,
    )
    original_source_model = fields.Selection(
        [
            ("sc.receipt.invoice.line", "收款发票明细"),
            ("sc.invoice.registration", "销项冲抵/红冲"),
        ],
        string="原票来源模型",
        readonly=True,
        index=True,
    )
    original_source_record_id = fields.Integer(string="原票来源ID", readonly=True, index=True)
    invoice_no = fields.Char(string="原发票号码", readonly=True, index=True)
    red_flush_invoice_no = fields.Char(string="红冲发票号码", index=True)
    invoice_issue_company = fields.Char(string="开票单位", readonly=True, index=True)
    invoice_party_name = fields.Char(string="开票抬头", readonly=True)
    original_invoice_amount = fields.Monetary(string="原发票金额", currency_field="currency_id", readonly=True)
    original_amount_no_tax = fields.Monetary(string="原不含税金额", currency_field="currency_id", readonly=True)
    original_tax_amount = fields.Monetary(string="原税额", currency_field="currency_id", readonly=True)
    original_surcharge_amount = fields.Monetary(string="原附加税", currency_field="currency_id", readonly=True)
    red_flush_invoice_amount = fields.Monetary(
        string="红冲价税合计",
        currency_field="currency_id",
        compute="_compute_red_flush_amounts",
        store=True,
    )
    red_flush_amount_no_tax = fields.Monetary(
        string="红冲不含税金额",
        currency_field="currency_id",
        compute="_compute_red_flush_amounts",
        store=True,
    )
    red_flush_tax_amount = fields.Monetary(
        string="红冲税额",
        currency_field="currency_id",
        compute="_compute_red_flush_amounts",
        store=True,
    )
    red_flush_surcharge_amount = fields.Monetary(
        string="红冲附加税",
        currency_field="currency_id",
        compute="_compute_red_flush_amounts",
        store=True,
    )
    reason = fields.Text(string="红冲原因")
    note = fields.Text(string="备注")

    @api.model_create_multi
    def create(self, vals_list):
        if any(vals.get("state", self.env.context.get("default_state", "draft")) != "draft" for vals in vals_list):
            raise UserError(_("销项变更必须从草稿提交审批。"))
        seq = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", "新建") == "新建":
                vals["name"] = seq.next_by_code("sc.output.invoice.adjustment") or _("销项变更登记")
        records = super().create(vals_list)
        records._sync_original_invoice_snapshot()
        return records

    def write(self, vals):
        if "state" in vals and self.env.context.get("sc_red_flush_state_token") is not _RED_FLUSH_STATE_TOKEN:
            raise UserError(_("状态只能通过提交、审批和确认红冲动作产生。"))
        reviewed = {"original_ledger_id", "adjustment_date", "adjustment_type", "red_flush_invoice_no", "reason", "project_id", "partner_id", "contract_id", "currency_id", "original_source_model", "original_source_record_id", "invoice_no", "invoice_issue_company", "invoice_party_name", "original_invoice_amount", "original_amount_no_tax", "original_tax_amount", "original_surcharge_amount"}
        if reviewed.intersection(vals) and any(rec.state not in ("draft", "rejected") for rec in self):
            raise UserError(_("在审或已通过红冲申请不能修改审批内容。"))
        if any(rec.state == "confirmed" for rec in self) and set(vals) - {"note", "message_follower_ids"}:
            raise UserError(_("已确认的销项变更登记不能修改。"))
        res = super().write(vals)
        if "original_ledger_id" in vals:
            self._sync_original_invoice_snapshot()
        return res

    @api.onchange("original_ledger_id")
    def _onchange_original_ledger_id(self):
        self._sync_original_invoice_snapshot()

    @api.depends(
        "original_invoice_amount",
        "original_amount_no_tax",
        "original_tax_amount",
        "original_surcharge_amount",
    )
    def _compute_red_flush_amounts(self):
        for rec in self:
            rec.red_flush_invoice_amount = rec._negative(rec.original_invoice_amount)
            rec.red_flush_amount_no_tax = rec._negative(rec.original_amount_no_tax or rec.original_invoice_amount)
            rec.red_flush_tax_amount = rec._negative(rec.original_tax_amount)
            rec.red_flush_surcharge_amount = rec._negative(rec.original_surcharge_amount)

    @api.model
    def _negative(self, amount):
        return -abs(amount or 0.0)

    def _sync_original_invoice_snapshot(self):
        for rec in self:
            ledger = rec.original_ledger_id
            if not ledger:
                continue
            source = rec._original_source_record(ledger)
            rec.project_id = ledger.project_id or getattr(source, "project_id", False)
            rec.partner_id = ledger.partner_id or getattr(source, "partner_id", False)
            rec.contract_id = ledger.contract_id or getattr(source, "contract_id", False)
            rec.currency_id = (
                ledger.currency_id
                or getattr(source, "currency_id", False)
                or rec.currency_id
                or self.env.company.currency_id
            )
            rec.original_source_model = ledger.source_model
            rec.original_source_record_id = ledger.source_record_id
            rec.invoice_no = ledger.invoice_no
            rec.red_flush_invoice_no = rec.red_flush_invoice_no or ledger.invoice_no
            rec.invoice_issue_company = ledger.invoice_issue_company
            rec.invoice_party_name = ledger.invoice_party_name
            rec.original_invoice_amount = ledger.invoice_amount
            rec.original_amount_no_tax = ledger.amount_no_tax
            rec.original_tax_amount = ledger.tax_amount
            rec.original_surcharge_amount = ledger.surcharge_amount

    def _original_source_record(self, ledger):
        if not ledger.source_model or not ledger.source_record_id:
            return self.env["sc.receipt.invoice.line"].browse()
        return self.env[ledger.source_model].browse(ledger.source_record_id)

    def _write_approval_state(self, values):
        return self.with_context(sc_red_flush_state_token=_RED_FLUSH_STATE_TOKEN).write(values)

    def action_submit(self):
        if any(rec.state not in ("draft", "submitted", "rejected") for rec in self):
            raise UserError(_("只有草稿、驳回或待重新提交的红冲申请可以提交。"))
        for rec in self:
            if rec.state in ("draft", "rejected"):
                rec._sync_original_invoice_snapshot()
            rec._validate_red_flush_ready()
        self.with_context(skip_validation_check=True)._write_approval_state({"state": "submitted"})
        for rec in self:
            if not self.env["sc.approval.policy"]._start_submission_review(rec):
                rec._write_approval_state({"state": "approved", "reject_reason": False})
        return True

    def action_on_tier_approved(self):
        for rec in self:
            if rec.state == "submitted" and rec.review_ids and rec.validation_status == "validated":
                rec._validate_red_flush_ready()
                rec._write_approval_state({"state": "approved", "reject_reason": False})

    def action_on_tier_rejected(self):
        for rec in self:
            if rec.state == "submitted" and rec.review_ids and rec.validation_status == "rejected":
                reviews = rec.review_ids.filtered(lambda review: review.status == "rejected" and review.comment)
                reason = reviews.sorted(lambda review: review.write_date or review.create_date, reverse=True)[:1].comment if reviews else "统一审批驳回（未填写原因）"
                rec.with_context(skip_validation_check=True)._write_approval_state({"state": "rejected", "reject_reason": reason})

    def _assert_original_snapshot_unchanged(self):
        self.ensure_one()
        ledger = self.original_ledger_id
        pairs = {"original_source_model": "source_model", "original_source_record_id": "source_record_id", "invoice_no": "invoice_no", "invoice_issue_company": "invoice_issue_company", "invoice_party_name": "invoice_party_name", "original_invoice_amount": "invoice_amount", "original_amount_no_tax": "amount_no_tax", "original_tax_amount": "tax_amount", "original_surcharge_amount": "surcharge_amount"}
        if any(self[field] != ledger[source] for field, source in pairs.items()):
            raise UserError(_("原票信息已变化，不能按旧审批内容确认红冲。"))
        source = self._original_source_record(ledger)
        for field in ("project_id", "partner_id", "contract_id", "currency_id"):
            expected = ledger[field] or getattr(source, field, False)
            if expected and self[field] != expected:
                raise UserError(_("原票业务身份已变化，不能确认红冲。"))

    def action_confirm(self):
        for rec in self:
            self.env["sc.approval.policy"]._assert_submission_approved(rec, ("approved",))
            rec._assert_original_snapshot_unchanged()
            rec._validate_red_flush_ready()
            generated = rec._create_red_flush_invoice_registration()
            rec._write_approval_state({"generated_invoice_id": generated.id, "state": "confirmed"})

    def action_cancel(self):
        for rec in self:
            if rec.generated_invoice_id:
                raise UserError(_("已生成红冲销项票的变更登记不能取消。"))
            if rec.state not in ("draft", "rejected"):
                raise UserError(_("只有草稿或驳回的销项变更登记可以取消。"))
        self.with_context(skip_validation_check=True)._write_approval_state({"state": "cancel"})

    def _validate_red_flush_ready(self):
        self.ensure_one()
        if not self.original_ledger_id:
            raise UserError(_("请先选择需要红冲的销项票。"))
        if self.original_ledger_id.adjustment_kind != "normal":
            raise UserError(_("只能对正常开票记录做红冲，不能重复红冲红冲记录。"))
        if self.generated_invoice_id:
            raise UserError(_("该变更登记已经生成红冲销项票。"))
        if not (self.red_flush_invoice_no or "").strip():
            raise UserError(_("请填写红冲发票号码。"))
        if (self.red_flush_invoice_no or "").strip() == (self.invoice_no or "").strip():
            raise UserError(_("红冲发票号码不能与原发票号码相同。"))
        existing = self.search(
            [
                ("id", "!=", self.id),
                ("state", "=", "confirmed"),
                ("original_ledger_id", "=", self.original_ledger_id.id),
            ],
            limit=1,
        )
        if existing:
            raise UserError(_("该销项票已在变更登记 %s 中完成红冲。") % existing.display_name)
        if not self.project_id:
            raise UserError(_("原销项票缺少项目，不能生成红冲销项票。"))
        if not self.red_flush_invoice_amount:
            raise UserError(_("原销项票金额为 0，不能生成红冲销项票。"))

    def _create_red_flush_invoice_registration(self):
        self.ensure_one()
        note_parts = [
            _("由销项变更登记 %s 确认红冲自动生成。") % self.name,
            _("原票来源：%s#%s，原发票号码：%s。")
            % (self.original_source_model, self.original_source_record_id, self.invoice_no or ""),
        ]
        if self.reason:
            note_parts.append(_("红冲原因：%s") % self.reason)
        if self.note:
            note_parts.append(self.note)
        return self.env["sc.invoice.registration"]._create_registered_red_flush(
            self,
            {
                "source_origin": "manual",
                "source_kind": "output_invoice_tax",
                "direction": "output",
                "state": "registered",
                "project_id": self.project_id.id,
                "partner_id": self.partner_id.id,
                "contract_id": self.contract_id.id,
                "document_no": self.name,
                "document_date": self.adjustment_date,
                "invoice_date": self.adjustment_date,
                "invoice_no": self.red_flush_invoice_no or self.invoice_no,
                "invoice_issue_company": self.invoice_issue_company,
                "amount_no_tax": self.red_flush_amount_no_tax,
                "tax_amount": self.red_flush_tax_amount,
                "amount_total": self.red_flush_invoice_amount,
                "surcharge_amount": self.red_flush_surcharge_amount,
                "currency_id": self.currency_id.id,
                "red_flush_adjustment_id": self.id,
                "red_flush_origin_source_model": self.original_source_model,
                "red_flush_origin_source_record_id": self.original_source_record_id,
                "red_flush_origin_invoice_no": self.invoice_no,
                "note": "\n".join(note_parts),
            }
        )
