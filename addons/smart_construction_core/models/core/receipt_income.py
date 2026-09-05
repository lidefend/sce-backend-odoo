# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare

from ..support.state_guard import raise_guard

_logger = logging.getLogger(__name__)
_RECEIPT_FACT_AUTHORITY_TOKEN = object()


class ScReceiptIncome(models.Model):
    _name = "sc.receipt.income"
    _description = "收款与收入登记"
    _inherit = ["mail.thread", "mail.activity.mixin", "tier.validation", "sc.company.contractor.responsibility.context.mixin"]
    _order = "date_receipt desc, id desc"

    name = fields.Char(string="单据号", required=True, default="新建", copy=False)
    source_origin = fields.Selection(
        [("manual", "新系统登记"), ("legacy", "历史迁移")],
        string="来源",
        default="manual",
        required=True,
        index=True,
    )
    source_kind = fields.Selection(
        [
            ("receipt_income", "收款收入"),
            ("residual_receipt", "残余收款"),
        ],
        string="业务类型",
        default="receipt_income",
        required=True,
        index=True,
    )
    source_family = fields.Char(string="来源类别", index=True, readonly=True)
    business_category_id = fields.Many2one(
        "sc.business.category",
        string="业务分类",
        index=True,
        ondelete="restrict",
        domain="[('target_model', '=', 'sc.receipt.income')]",
    )
    state = fields.Selection(
        [
            ("draft", "草稿"),
            ("confirmed", "已确认"),
            ("received", "已收款"),
            ("legacy_confirmed", "历史已确认"),
            ("cancel", "已取消"),
        ],
        string="状态",
        default="draft",
        required=True,
        index=True,
    )
    project_id = fields.Many2one("project.project", string="项目", required=True, index=True)
    legacy_project_name = fields.Char(string="历史项目名称", index=True, readonly=True)
    company_id = fields.Many2one(
        "res.company",
        string="公司",
        readonly=True,
        index=True,
    )
    finance_identity_state = fields.Selection(
        [
            ("normalized", "标准事实"),
            ("legacy_observed_identity", "历史冻结身份"),
            ("legacy_unresolved_identity", "历史身份待确认"),
        ],
        required=True,
        default="normalized",
        readonly=True,
        index=True,
        string="财务身份状态",
    )
    legacy_company_name = fields.Char(string="承包单位", index=True, readonly=True)
    operation_strategy = fields.Selection(
        related="project_id.operation_strategy",
        string="经营方式",
        store=True,
        readonly=True,
        index=True,
    )
    partner_id = fields.Many2one("res.partner", string="往来单位", index=True)
    legacy_partner_name = fields.Char(string="历史往来单位", index=True, readonly=True)
    contract_id = fields.Many2one(
        "construction.contract",
        string="合同",
        index=True,
        domain="[('project_id', '=', project_id)]",
    )
    legacy_contract_no = fields.Char(string="施工管理合同", index=True, readonly=True)
    payment_request_id = fields.Many2one(
        "payment.request",
        string="收款申请",
        index=True,
        ondelete="set null",
        domain="[('project_id', '=', project_id), ('type', '=', 'receive')]",
    )
    treasury_ledger_id = fields.Many2one("sc.treasury.ledger", string="资金台账", index=True, ondelete="set null")
    date_receipt = fields.Date(string="单据日期", default=fields.Date.context_today, index=True)
    document_no = fields.Char(string="来源单号", index=True)
    receipt_type = fields.Char(string="登记类型", index=True)
    legacy_receipt_type = fields.Char(string="收款类型", index=True)
    legacy_receipt_subtype = fields.Char(string="收款细分", index=True)
    income_category = fields.Char(string="收入类别", index=True)
    receipt_flow_label = fields.Char(string="办理事项", compute="_compute_receipt_flow_label")
    payment_method = fields.Char(string="收款方式", index=True)
    receiving_account = fields.Char(string="收款账户", index=True)
    receiving_account_name = fields.Char(string="收款账户名称", index=True)
    receiving_account_no = fields.Char(string="收款账号", index=True)
    receiving_bank_name = fields.Char(string="收款开户行", index=True)
    bill_no = fields.Char(string="票据号", index=True)
    invoice_ref = fields.Char(string="发票引用", index=True)
    amount = fields.Monetary(string="收款金额", currency_field="currency_id", required=True)
    deducted_invoice_amount = fields.Monetary(string="已抵发票金额", currency_field="currency_id")
    deducted_tax_amount = fields.Monetary(string="已抵税额", currency_field="currency_id")
    settlement_amount = fields.Monetary(string="结算金额", currency_field="currency_id")
    currency_id = fields.Many2one(
        "res.currency",
        string="币种",
        required=True,
        default=lambda self: (self.env.ref("base.CNY", raise_if_not_found=False) or self.env.company.currency_id).id,
    )
    legacy_source_model = fields.Char(string="历史来源模型", index=True, readonly=True)
    legacy_source_table = fields.Char(string="历史来源表", index=True, readonly=True)
    legacy_record_id = fields.Char(string="历史记录ID", index=True, readonly=True)
    legacy_document_state = fields.Char(string="历史状态", index=True, readonly=True)
    legacy_document_state_label = fields.Char(string="历史状态名称", index=True, readonly=True)
    legacy_note = fields.Text(string="历史备注", readonly=True)
    creator_name = fields.Char(string="历史录入人", index=True, readonly=True)
    created_time = fields.Datetime(string="历史录入时间", index=True, readonly=True)
    reject_reason = fields.Char(string="驳回原因", readonly=True, copy=False)
    note = fields.Text(string="备注")
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "sc_receipt_income_attachment_rel",
        "receipt_id",
        "attachment_id",
        string="附件",
    )
    active = fields.Boolean("有效", default=True, index=True)

    _sql_constraints = [
        (
            "finance_normalized_identity_present",
            "CHECK(finance_identity_state != 'normalized' OR (project_id IS NOT NULL AND company_id IS NOT NULL AND currency_id IS NOT NULL))",
            "标准收款事实必须固化项目、公司与币种身份。",
        ),
        (
            "legacy_source_unique",
            "unique(legacy_source_model, legacy_record_id)",
            "历史收款收入来源记录必须唯一。",
        ),
        (
            "amount_manual_nonnegative",
            "CHECK(source_origin = 'legacy' OR amount >= 0)",
            "Manual receipt amount must be non-negative.",
        ),
    ]

    @api.model
    def _context_project_id(self):
        project_id = self.env.context.get("default_project_id") or self.env.context.get("current_project_id")
        try:
            return int(project_id) if project_id else False
        except (TypeError, ValueError):
            return False

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        project_id = res.get("project_id") or self._context_project_id()
        if project_id and "project_id" in fields_list:
            res["project_id"] = project_id
        return res

    @api.onchange("payment_request_id")
    def _onchange_payment_request_id(self):
        for rec in self:
            request = rec.payment_request_id
            if not request:
                continue
            if request.type != "receive":
                rec.payment_request_id = False
                return {
                    "warning": {
                        "title": _("收款申请不匹配"),
                        "message": _("收款登记只能选择收款类型的申请。"),
                    }
                }
            if request.project_id and not rec.project_id:
                rec.project_id = request.project_id
            if request.contract_id and not rec.contract_id:
                rec.contract_id = request.contract_id
            if request.partner_id and not rec.partner_id:
                rec.partner_id = request.partner_id
            if request.amount and not rec.amount:
                rec.amount = request.amount
            if request.currency_id and not rec.currency_id:
                rec.currency_id = request.currency_id
            if request.receipt_type and not rec.receipt_type:
                rec.receipt_type = request.receipt_type
            if request.partner_account_name and not rec.receiving_account_name:
                rec.receiving_account_name = request.partner_account_name
            if request.partner_bank_account and not rec.receiving_account_no:
                rec.receiving_account_no = request.partner_bank_account
            if request.partner_bank_name and not rec.receiving_bank_name:
                rec.receiving_bank_name = request.partner_bank_name

    @api.onchange("project_id")
    def _onchange_project_id_clear_invalid_receipt_links(self):
        for rec in self:
            if not rec.project_id:
                continue
            if rec.payment_request_id and rec.payment_request_id.project_id != rec.project_id:
                rec.payment_request_id = False
            if rec.contract_id and rec.contract_id.project_id != rec.project_id:
                rec.contract_id = False

    @api.model
    def _caller_visible_relation_record(self, model_name, record_id, domain=None):
        if not record_id:
            return self.env[model_name]
        relation_domain = [("id", "=", record_id)]
        if domain:
            relation_domain.extend(domain)
        record = self.env[model_name].search(relation_domain, limit=1)
        if not record:
            raise ValidationError(_("收款归集关系不存在或当前用户无权访问。"))
        return record

    @api.model
    def _normalize_receipt_relation_values(self, vals, current=None):
        values = dict(vals)

        def relation_id(field_name):
            if field_name in values:
                return values.get(field_name) or False
            return current[field_name].id if current and current[field_name] else False

        request_id = relation_id("payment_request_id")
        contract_id = relation_id("contract_id")
        partner_id = relation_id("partner_id")
        project_id = relation_id("project_id")

        request = self.env["payment.request"]
        if request_id:
            request = self._caller_visible_relation_record(
                "payment.request",
                request_id,
                [("type", "=", "receive")],
            )
            if not request.contract_id:
                raise ValidationError(_("收款申请未唯一关联合同，不能作为收款归集依据。"))
            if request.project_id != request.contract_id.project_id:
                raise ValidationError(_("收款申请项目与其合同项目不一致。"))
            if request.partner_id != request.contract_id.partner_id:
                raise ValidationError(_("收款申请往来单位与其合同相对方不一致。"))
            contract_id = contract_id or request.contract_id.id

        contract = self.env["construction.contract"]
        if contract_id:
            contract = self._caller_visible_relation_record(
                "construction.contract",
                contract_id,
                [("type", "=", "out")],
            )
            if request and contract != request.contract_id:
                raise ValidationError(_("收款登记合同必须与收款申请合同一致。"))
            authoritative_partner = contract.partner_id
            self._caller_visible_relation_record("res.partner", authoritative_partner.id)
            if partner_id and partner_id != authoritative_partner.id:
                raise ValidationError(_("收款登记往来单位必须与合同收款相对方一致。"))
            if project_id and project_id != contract.project_id.id:
                raise ValidationError(_("收款登记项目必须与合同项目一致。"))
            values.setdefault("contract_id", contract.id)
            values.setdefault("partner_id", authoritative_partner.id)
            values.setdefault("project_id", contract.project_id.id)

        return values

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env["ir.sequence"]
        normalized_vals_list = []
        legacy_authority = self.env.context.get("sc_receipt_fact_authority_token") is _RECEIPT_FACT_AUTHORITY_TOKEN
        for incoming_vals in vals_list:
            vals = dict(incoming_vals)
            if vals.get("source_origin") == "legacy" and not legacy_authority:
                raise UserError(_("历史收款只能由受治理迁移载体创建。"))
            if vals.get("state") in {"received", "legacy_confirmed"} and not legacy_authority:
                raise UserError(_("新系统收款登记不能直接创建为已收款，必须执行正式收款动作。"))
            if vals.get("treasury_ledger_id") and not legacy_authority:
                raise UserError(_("收款资金台账只能由正式收款动作绑定。"))
            project_id = self._context_project_id()
            if project_id:
                vals.setdefault("project_id", project_id)
            if not (
                legacy_authority
                and vals.get("finance_identity_state") == "legacy_unresolved_identity"
            ):
                vals = self._normalize_receipt_relation_values(vals)
            project = self.env["project.project"].browse(vals.get("project_id")).exists()
            if not project or not project.company_id:
                raise UserError(_("收款登记必须关联已归属公司的有效项目。"))
            if vals.get("company_id") and vals["company_id"] != project.company_id.id:
                raise UserError(_("收款登记公司必须与项目公司一致。"))
            vals["company_id"] = project.company_id.id
            vals["finance_identity_state"] = vals.get("finance_identity_state") if legacy_authority else "normalized"
            vals.setdefault("business_category_id", self._resolve_business_category_id(vals))
            if vals.get("name", "新建") == "新建":
                vals["name"] = seq.next_by_code("sc.receipt.income") or _("Receipt Income")
            normalized_vals_list.append(vals)
        return super().create(normalized_vals_list)

    @api.model
    def _create_legacy_authoritative(self, vals):
        values = dict(vals, source_origin="legacy")
        project = self.env["project.project"].browse(values.get("project_id")).exists()
        evidence_complete = bool(
            project
            and values.get("company_id") == project.company_id.id
            and values.get("currency_id")
        )
        values["finance_identity_state"] = (
            "legacy_observed_identity" if evidence_complete else "legacy_unresolved_identity"
        )
        if (
            evidence_complete
            and values.get("payment_request_id")
            and values.get("state") in {"received", "legacy_confirmed"}
        ):
            candidate = self.new(values)
            if candidate.payment_request_id._terminal_cash_source_identity_errors(candidate):
                values["finance_identity_state"] = "legacy_unresolved_identity"
            else:
                candidate.payment_request_id._claim_terminal_cash_source(candidate)
        receipt = self.with_context(
            sc_receipt_fact_authority_token=_RECEIPT_FACT_AUTHORITY_TOKEN
        ).create(values)
        if receipt.payment_request_id and receipt.finance_identity_state == "legacy_observed_identity":
            receipt.payment_request_id._bind_terminal_cash_source(receipt)
        return receipt

    def unlink(self):
        terminal = self.filtered(lambda rec: rec.state in {"received", "legacy_confirmed"})
        claimed_ids = self.env["payment.request"].sudo().search(
            [
                ("terminal_cash_source_model", "=", self._name),
                ("terminal_cash_source_res_id", "in", self.ids),
            ]
        ).mapped("terminal_cash_source_res_id")
        if terminal or claimed_ids:
            raise UserError(_("终态或已被申请认领的收款事实不可删除；更正必须形成独立冲销事实。"))
        return super().unlink()

    @api.model
    def _resolve_business_category_code(self, vals):
        code = self.env.context.get("default_business_category_code") or self.env.context.get(
            "current_business_category_code"
        )
        if code:
            return code
        source_kind = vals.get("source_kind") or self.env.context.get("default_source_kind") or "receipt_income"
        source_family = vals.get("source_family") or self.env.context.get("default_source_family") or ""
        income_category = vals.get("income_category") or self.env.context.get("default_income_category") or ""
        receipt_type = vals.get("receipt_type") or self.env.context.get("default_receipt_type") or ""
        receipt_flow_label = vals.get("receipt_flow_label") or self.env.context.get("default_receipt_flow_label") or ""
        if source_kind == "residual_receipt" or receipt_type == "其他类型收款" or receipt_flow_label == "残余收款":
            return "finance.receipt.income.residual"
        if source_kind == "receipt_income" and (
            source_family == "engineering_progress_receipt_visible" or income_category == "工程进度款收入"
        ):
            return "finance.receipt.income.progress"
        if source_kind == "receipt_income":
            return "finance.receipt.income.project"
        return False

    @api.model
    def _resolve_business_category_id(self, vals):
        code = self._resolve_business_category_code(vals)
        if not code:
            return False
        category = self.env["sc.business.category"].sudo().search(
            [("code", "=", code), ("target_model", "=", self._name)],
            limit=1,
        )
        return category.id if category else False

    @api.depends(
        "source_kind",
        "source_family",
        "receipt_type",
        "legacy_receipt_type",
        "legacy_receipt_subtype",
        "income_category",
    )
    def _compute_receipt_flow_label(self):
        for rec in self:
            if rec.source_family == "engineering_progress_receipt_visible" or rec.income_category == "工程进度款收入":
                rec.receipt_flow_label = _("工程进度款收入")
            elif rec.source_kind == "residual_receipt":
                rec.receipt_flow_label = _("残余收款")
            elif rec.income_category:
                rec.receipt_flow_label = rec.income_category
            elif rec.receipt_type:
                rec.receipt_flow_label = rec.receipt_type
            elif rec.legacy_receipt_subtype:
                rec.receipt_flow_label = rec.legacy_receipt_subtype
            elif rec.legacy_receipt_type:
                rec.receipt_flow_label = rec.legacy_receipt_type
            else:
                rec.receipt_flow_label = _("收款收入")

    def _history_surface_allowed_write_fields(self):
        return {"attachment_ids"}

    def _received_surface_allowed_write_fields(self):
        return {"note", "attachment_ids"}

    def write(self, vals):
        authoritative = self.env.context.get("sc_receipt_fact_authority_token") is _RECEIPT_FACT_AUTHORITY_TOKEN
        if "treasury_ledger_id" in vals and not authoritative:
            raise UserError(_("收款资金台账只能由正式收款动作绑定。"))
        if not authoritative and (vals.get("state") in {"received", "legacy_confirmed"} or "finance_identity_state" in vals):
            raise UserError(_("收款终态及财务身份只能由正式业务动作或迁移写入。"))
        if any(rec.state == "received" for rec in self) and not authoritative:
            forbidden_fields = set(vals) - self._received_surface_allowed_write_fields()
            if forbidden_fields:
                raise UserError(_("已收款事实只允许补充备注和附件，其他终态事实不可改写。"))
        terminal_business_fields = {
            "project_id", "company_id", "currency_id", "partner_id", "contract_id",
            "payment_request_id", "treasury_ledger_id", "date_receipt", "amount",
            "deducted_invoice_amount", "deducted_tax_amount", "settlement_amount", "active",
        }
        if any(rec.state in {"received", "legacy_confirmed"} for rec in self) and not authoritative:
            if set(vals) & terminal_business_fields:
                raise UserError(_("已收款事实不可改写经济身份、金额、关联或有效性。"))
        if any(rec.source_origin == "legacy" and rec.state == "legacy_confirmed" for rec in self):
            allowed = {
                "payment_request_id",
                "treasury_ledger_id",
                "partner_id",
                "contract_id",
                "creator_name",
                "created_time",
                "note",
                "active",
                "write_uid",
                "write_date",
            } | self._history_surface_allowed_write_fields()
            if set(vals) - allowed:
                raise UserError(_("历史迁移收款/收入单据已确认，只允许补充业务锚点和备注。"))
        relation_fields = {"payment_request_id", "contract_id", "partner_id", "project_id"}
        if relation_fields.intersection(vals):
            result = True
            for rec in self:
                normalized_vals = rec._normalize_receipt_relation_values(vals, current=rec)
                if "project_id" in normalized_vals:
                    project = self.env["project.project"].browse(normalized_vals["project_id"]).exists()
                    normalized_vals["company_id"] = project.company_id.id
                result = super(ScReceiptIncome, rec).write(normalized_vals) and result
            return result
        return super().write(vals)

    def _write_finance_authority(self, vals):
        result = self.with_context(sc_receipt_fact_authority_token=_RECEIPT_FACT_AUTHORITY_TOKEN).write(vals)
        self.flush_recordset(list(vals))
        return result

    def action_confirm(self):
        policy = self.env["sc.approval.policy"]
        for rec in self:
            if rec.state != "draft":
                raise_guard(
                    "RECEIPT_INCOME_INVALID_TRANSITION",
                    f"收款收入[{rec.display_name}]",
                    _("确认收款收入"),
                    reasons=[_("只有草稿状态的收款收入可以确认")],
                )
            before = rec._snapshot_audit_payload()
            rec._check_business_anchor_or_raise()
            rec._check_payment_request_scope_or_raise()
            if policy.is_approval_required(rec._name, company=rec.company_id):
                company = rec.company_id or self.env.company
                rec.with_company(company).with_context(allowed_company_ids=[company.id])._request_document_approval()
                rec._audit_transition(
                    "receipt_income_submitted",
                    before,
                    rec._snapshot_audit_payload(),
                    "action_confirm",
                )
            else:
                rec.write({"state": "confirmed", "reject_reason": False})
                rec._audit_transition(
                    "receipt_income_confirmed",
                    before,
                    rec._snapshot_audit_payload(),
                    "action_confirm",
                )

    def action_received(self):
        self._assert_finance_confirm_access()
        policy = self.env["sc.approval.policy"]
        for rec in self:
            if rec.state not in ("draft", "confirmed"):
                raise_guard(
                    "RECEIPT_INCOME_INVALID_TRANSITION",
                    f"收款收入[{rec.display_name}]",
                    _("登记收款"),
                    reasons=[_("只有草稿或已确认状态的收款收入可以登记收款")],
                )
            rec._check_business_anchor_or_raise()
            rec._check_payment_request_scope_or_raise()
            if policy.is_approval_required(rec._name, company=rec.company_id) and rec.validation_status != "validated":
                raise UserError(_("收款收入尚未完成统一审批流程。"))
            before = rec._snapshot_audit_payload()
            with self.env.cr.savepoint():
                rec._write_finance_authority({"state": "received"})
                rec._sync_payment_request_done()
            rec._audit_transition(
                "receipt_income_received",
                before,
                rec._snapshot_audit_payload(),
                "action_received",
            )

    def _has_finance_confirm_access(self):
        return self.env.user.has_group("smart_construction_core.group_sc_cap_finance_manager")

    def _assert_finance_confirm_access(self):
        if not self._has_finance_confirm_access():
            raise UserError(_("你没有登记收款的财务确认权限。"))

    def action_cancel(self):
        for rec in self:
            if rec.source_origin == "legacy":
                raise UserError(_("历史迁移收款/收入单据不能在新系统取消。"))
            if rec.state in ("received", "legacy_confirmed", "cancel"):
                raise_guard(
                    "RECEIPT_INCOME_INVALID_TRANSITION",
                    f"收款收入[{rec.display_name}]",
                    _("取消收款收入"),
                    reasons=[_("已收款、历史已确认或已取消的收款收入不能取消")],
                )
            before = rec._snapshot_audit_payload()
            rec.write({"state": "cancel"})
            rec._audit_transition(
                "receipt_income_cancelled",
                before,
                rec._snapshot_audit_payload(),
                "action_cancel",
            )

    def _check_business_anchor_or_raise(self):
        for rec in self:
            if rec.source_origin == "legacy":
                continue
            if rec.finance_identity_state != "normalized" or rec.company_id != rec.project_id.company_id:
                raise UserError(_("收款登记财务身份已失配，请重建草稿后再办理。"))
            if not rec.project_id:
                raise_guard(
                    "RECEIPT_INCOME_MISSING_PROJECT",
                    f"收款收入[{rec.display_name}]",
                    _("办理收款收入"),
                    reasons=[_("收款收入必须关联项目")],
                )
            if not rec.payment_request_id:
                raise_guard(
                    "RECEIPT_INCOME_MISSING_REQUEST",
                    f"收款收入[{rec.display_name}]",
                    _("办理收款收入"),
                    reasons=[_("新系统收款收入必须关联已审批的收款申请")],
                )
            if not rec.contract_id:
                raise_guard(
                    "RECEIPT_INCOME_MISSING_CONTRACT",
                    f"收款收入[{rec.display_name}]",
                    _("办理收款收入"),
                    reasons=[_("新系统收款收入必须关联合同")],
                )
            if not rec.partner_id:
                raise_guard(
                    "RECEIPT_INCOME_MISSING_PARTNER",
                    f"收款收入[{rec.display_name}]",
                    _("办理收款收入"),
                    reasons=[_("收款收入必须选择往来单位")],
                )
            if (rec.amount or 0.0) <= 0:
                raise_guard(
                    "RECEIPT_INCOME_INVALID_AMOUNT",
                    f"收款收入[{rec.display_name}]",
                    _("办理收款收入"),
                    reasons=[_("收款金额必须大于0")],
                )
            # R10-v2: receiving-account completeness downgraded from hard guard
            # to logged advisory — spec tests confirm receipts without account
            # details (the account snapshot arrives with the payment request).
            receiving_account = rec.receiving_account_no or rec.receiving_account or rec.receiving_account_name
            if not receiving_account:
                _logger.warning(
                    "sc.receipt.income %s confirmed without receiving account info",
                    rec.display_name,
                )

    def _check_payment_request_scope_or_raise(self):
        for rec in self:
            request = rec.payment_request_id
            if not request:
                continue
            if rec.source_origin == "legacy" and rec.state == "legacy_confirmed":
                continue
            if request.type != "receive":
                raise UserError(_("收款收入只能关联收款类型的付款/收款申请。"))
            if rec.project_id and request.project_id and rec.project_id != request.project_id:
                raise UserError(_("收款收入项目必须与收款申请项目一致。"))
            if rec.partner_id and request.partner_id and rec.partner_id != request.partner_id:
                raise UserError(_("收款收入往来单位必须与收款申请往来单位一致。"))
            if rec.contract_id and request.contract_id and rec.contract_id != request.contract_id:
                raise UserError(_("收款收入合同必须与收款申请合同一致。"))
            if rec.currency_id != request.currency_id:
                raise UserError(_("收款收入币种必须与收款申请币种一致。"))
            rounding = rec.currency_id.rounding if rec.currency_id else 0.01
            if float_compare(rec.amount or 0.0, request.amount or 0.0, precision_rounding=rounding) == 1:
                raise UserError(_("收款金额不能超过收款申请金额。"))

    def _request_document_approval(self):
        self.ensure_one()
        if self.review_ids and self.validation_status == "rejected":
            self.restart_validation()
        elif not self.review_ids or self.validation_status == "no":
            reviews = self.request_validation()
            if not reviews:
                raise UserError(_("收款收入已启用审批，但没有匹配的统一审批规则，请检查业务审批配置。"))
        else:
            raise UserError(_("收款收入已经在统一审批流程中，请等待审批完成。"))

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
            if self.env.context.get("server_action_tier") and rec.validation_status != "validated":
                # OCA base_tier_validation_server_action fires this callback
                # after every approved level of a multi-level linear chain;
                # a mid-chain invocation must not advance the record. The
                # completed chain re-fires the callback and finishes it.
                continue
            if rec.state == "draft":
                before = rec._snapshot_audit_payload()
                rec.with_context(skip_validation_check=True).write({"state": "confirmed", "reject_reason": False})
                rec._audit_transition(
                    "receipt_income_confirmed",
                    before,
                    rec._snapshot_audit_payload(),
                    "action_on_tier_approved",
                )

    def action_on_tier_rejected(self, reason=None):
        for rec in self:
            if rec.state == "draft":
                before = rec._snapshot_audit_payload()
                rec.with_context(skip_validation_check=True).write(
                    {"reject_reason": reason or rec._get_tier_reject_reason()}
                )
                rec._audit_transition(
                    "receipt_income_rejected",
                    before,
                    rec._snapshot_audit_payload(),
                    "action_on_tier_rejected",
                )

    def _sync_payment_request_done(self):
        for rec in self:
            request = rec.payment_request_id
            if not request:
                continue
            rec._check_payment_request_scope_or_raise()
            request._claim_terminal_cash_source(rec)
            if request.type != "receive":
                raise UserError(_("收款收入只能关联收款类型的付款/收款申请。"))
            rounding = request.currency_id.rounding if request.currency_id else 0.01
            if float_compare(rec.amount or 0.0, request.amount or 0.0, precision_rounding=rounding) == -1:
                raise UserError(_("收款金额低于收款申请金额，不能自动完成收款申请。"))
            if request.state == "submit" and request.validation_status == "validated":
                request.with_context(tier_validation_callback=True).action_on_tier_approved()
            if request.state == "approve" and request.validation_status == "validated":
                request.action_set_approved()
            if request.state != "approved":
                raise UserError(_("收款申请尚未达到可入账状态，不能确认收款事实。"))
            before = request._snapshot_audit_payload()
            ledger = request.with_context(payment_soft_gate=True)._ensure_treasury_ledger(
                amount=request.amount or 0.0,
                date=rec.date_receipt,
                note=_("auto:receipt_income_received"),
            )
            rec._write_finance_authority({"treasury_ledger_id": ledger.id})
            request.with_context(allow_transition=True, payment_soft_gate=True).write({"state": "done"})
            after = request._snapshot_audit_payload()
            request._audit_transition("payment_paid", before, after, action_name="receipt_income_received")

    def _snapshot_audit_payload(self):
        self.ensure_one()
        return {
            "state": self.state,
            "source_origin": self.source_origin,
            "source_kind": self.source_kind,
            "source_family": self.source_family,
            "business_category_id": self.business_category_id.id,
            "business_category_code": self.business_category_id.code,
            "project_id": self.project_id.id,
            "company_id": self.company_id.id,
            "partner_id": self.partner_id.id,
            "contract_id": self.contract_id.id,
            "payment_request_id": self.payment_request_id.id,
            "treasury_ledger_id": self.treasury_ledger_id.id,
            "date_receipt": fields.Date.to_string(self.date_receipt) if self.date_receipt else False,
            "receipt_type": self.receipt_type,
            "income_category": self.income_category,
            "receiving_account_name": self.receiving_account_name,
            "receiving_account_no": self.receiving_account_no,
            "amount": self.amount,
            "currency_id": self.currency_id.id,
            "reject_reason": self.reject_reason,
            "validation_status": self.validation_status,
        }

    def _audit_transition(self, event_code, before, after, action_name):
        self.ensure_one()
        return self.env["sc.audit.log"].write_event(
            event_code,
            self._name,
            self.id,
            action=action_name,
            before=before,
            after=after,
            company_id=self.company_id,
            project_id=self.project_id,
        )

    def init(self):
        self.env.cr.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS sc_receipt_income_one_canonical_terminal_per_request_idx
                ON sc_receipt_income(payment_request_id)
             WHERE payment_request_id IS NOT NULL
               AND finance_identity_state IN ('normalized', 'legacy_observed_identity')
               AND state IN ('received', 'legacy_confirmed')
            """
        )
        self.env.cr.execute(
            """
            UPDATE sc_receipt_income receipt
               SET business_category_id = category.id
              FROM sc_business_category category
             WHERE receipt.business_category_id IS NULL
               AND category.target_model = 'sc.receipt.income'
               AND category.code = CASE
                   WHEN receipt.source_kind = 'receipt_income'
                        AND (
                            COALESCE(receipt.source_family, '') = 'engineering_progress_receipt_visible'
                            OR COALESCE(receipt.income_category, '') = '工程进度款收入'
                        )
                       THEN 'finance.receipt.income.progress'
                   WHEN receipt.source_kind = 'residual_receipt'
                        OR COALESCE(receipt.receipt_type, '') = '其他类型收款'
                       THEN 'finance.receipt.income.residual'
                   WHEN receipt.source_kind = 'receipt_income'
                       THEN 'finance.receipt.income.project'
                   ELSE NULL
               END
            """
        )
