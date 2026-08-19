# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare
from psycopg2.errors import UniqueViolation

from ..support.state_guard import raise_guard


class ScPaymentExecution(models.Model):
    _name = "sc.payment.execution"
    _description = "付款执行"
    _inherit = ["mail.thread", "mail.activity.mixin", "tier.validation", "sc.company.contractor.responsibility.context.mixin"]
    _order = "date_payment desc, id desc"

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
            ("outflow_request", "付款申请"),
            ("actual_outflow", "实际付款"),
        ],
        string="业务类型",
        default="outflow_request",
        required=True,
        index=True,
    )
    execution_flow_label = fields.Char(string="办理事项", compute="_compute_execution_flow_label")
    business_category_id = fields.Many2one(
        "sc.business.category",
        string="业务分类",
        index=True,
        ondelete="restrict",
        domain="[('target_model', '=', 'sc.payment.execution')]",
    )
    state = fields.Selection(
        [
            ("draft", "草稿"),
            ("confirmed", "已确认"),
            ("paid", "已付款"),
            ("legacy_confirmed", "历史已确认"),
            ("cancel", "已取消"),
        ],
        string="状态",
        default="draft",
        required=True,
        index=True,
        tracking=True,
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
    operation_strategy = fields.Selection(
        related="project_id.operation_strategy",
        string="经营方式",
        store=True,
        readonly=True,
        index=True,
    )
    partner_id = fields.Many2one("res.partner", string="往来单位", index=True)
    contract_id = fields.Many2one(
        "construction.contract",
        string="合同",
        index=True,
        domain="[('project_id', '=', project_id)]",
    )
    payment_request_id = fields.Many2one(
        "payment.request",
        string="付款申请",
        index=True,
        ondelete="set null",
        domain="[('project_id', '=', project_id), ('type', '=', 'pay')]",
    )
    payment_request_partner_id = fields.Many2one(
        "res.partner",
        string="申请往来单位",
        related="payment_request_id.partner_id",
        store=True,
        readonly=True,
        index=True,
    )
    actual_payee_partner_id = fields.Many2one(
        "res.partner",
        string="实际收款单位",
        related="partner_id",
        store=True,
        readonly=True,
        index=True,
    )
    payment_request_partner_relation = fields.Selection(
        [
            ("no_request", "未关联付款申请"),
            ("same_partner", "申请方与收款方一致"),
            ("actual_payee_differs", "实际收款方不同"),
            ("missing_request_partner", "申请方为空"),
            ("missing_actual_payee", "实际收款方为空"),
        ],
        string="申请/收款方关系",
        compute="_compute_payment_request_partner_relation",
        store=True,
        readonly=True,
        index=True,
    )
    date_payment = fields.Date(string="单据日期", default=fields.Date.context_today, index=True)
    document_no = fields.Char(string="来源单号", index=True)
    payment_family = fields.Char(string="付款族", index=True)
    payment_method = fields.Char(string="付款方式", index=True)
    bank_account = fields.Char(string="付款账户", index=True)
    payment_account_name = fields.Char(string="付款账户名称", index=True)
    payment_account_no = fields.Char(string="付款账号", index=True)
    payment_bank_name = fields.Char(string="付款开户行", index=True)
    receipt_account_name = fields.Char(string="收款账户名称", index=True)
    receipt_account_no = fields.Char(string="收款账号", index=True)
    receipt_bank_name = fields.Char(string="收款开户行", index=True)
    handler_name = fields.Char(string="经办人", index=True)
    planned_amount = fields.Monetary(string="申请/计划金额", currency_field="currency_id")
    paid_amount = fields.Monetary(string="实付金额", currency_field="currency_id")
    invoice_amount = fields.Monetary(string="发票金额", currency_field="currency_id")
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
    push_result = fields.Char(string="推送结果", index=True, readonly=True)
    kingdee_document_no = fields.Char(string="金蝶单据编号", index=True, readonly=True)
    creator_name = fields.Char(string="历史录入人", index=True, readonly=True)
    created_time = fields.Datetime(string="历史录入时间", index=True, readonly=True)
    reject_reason = fields.Char(string="驳回原因", readonly=True, copy=False)
    cancellation_kind = fields.Selection(
        [
            ("cancelled_before_payment", "付款前取消"),
            ("payment_reversed", "已付款冲销"),
        ],
        string="撤销类型",
        readonly=True,
        copy=False,
        tracking=True,
    )
    reversal_reason = fields.Text(
        string="冲销原因",
        copy=False,
        tracking=True,
        help="已付款记录办理冲销时必须由财务经理填写，原文同步保留到付款台账。",
    )
    note = fields.Text(string="备注")
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "sc_payment_execution_attachment_rel",
        "execution_id",
        "attachment_id",
        string="附件",
    )
    active = fields.Boolean(string="有效", default=True, index=True)
    partner_payment_status_display = fields.Char(string="单据状态", compute="_compute_partner_payment_visible_fields", store=True, readonly=True)
    partner_payment_date_display = fields.Char(string="付款日期", compute="_compute_partner_payment_visible_fields", store=True, readonly=True)
    partner_payment_payee_unit = fields.Char(string="收款单位", compute="_compute_partner_payment_visible_fields", store=True, readonly=True)
    partner_payment_actual_payee_unit = fields.Char(string="实际收款单位", compute="_compute_partner_payment_visible_fields", store=True, readonly=True)
    partner_payment_amount_display = fields.Char(string="付款金额", compute="_compute_partner_payment_visible_fields", store=True, readonly=True)
    partner_payment_category_display = fields.Char(string="支付类别", compute="_compute_partner_payment_visible_fields", store=True, readonly=True)
    partner_payment_content_display = fields.Char(string="付款内容", compute="_compute_partner_payment_visible_fields", store=True, readonly=True)
    partner_payment_method_display = fields.Char(string="付款方式名称", compute="_compute_partner_payment_visible_fields", store=True, readonly=True)
    partner_payment_cost_type_display = fields.Char(string="类型（成本）", compute="_compute_partner_payment_visible_fields", store=True, readonly=True)
    partner_payment_account_name_display = fields.Char(string="付款账户名称", compute="_compute_partner_payment_visible_fields", store=True, readonly=True)
    partner_payment_attachment_text = fields.Char(string="附件", compute="_compute_partner_payment_visible_fields", store=True, readonly=True)
    partner_payment_voucher_no = fields.Char(string="凭证号", compute="_compute_partner_payment_visible_fields", store=True, readonly=True)
    partner_payment_writer = fields.Char(string="填写人", compute="_compute_partner_payment_visible_fields", store=True, readonly=True)
    partner_payment_source_created_by = fields.Char(string="录入人", compute="_compute_partner_payment_visible_fields", store=True, readonly=True)
    partner_payment_project_name = fields.Char(string="项目名称", compute="_compute_partner_payment_visible_fields", store=True, readonly=True)
    partner_payment_source_text = fields.Char(string="付款单关联来源", compute="_compute_partner_payment_visible_fields", store=True, readonly=True)
    partner_payment_document_no = fields.Char(string="单据编号", compute="_compute_partner_payment_visible_fields", store=True, readonly=True)
    company_finance_status_display = fields.Char(string="单据状态", compute="_compute_company_finance_visible_fields", store=True, readonly=True)
    company_finance_push_result = fields.Char(string="推送结果", compute="_compute_company_finance_visible_fields", store=True, readonly=True)
    company_finance_document_no = fields.Char(string="单据编号", compute="_compute_company_finance_visible_fields", store=True, readonly=True)
    company_finance_amount_display = fields.Char(string="付款金额", compute="_compute_company_finance_visible_fields", store=True, readonly=True)
    company_finance_cost_type_display = fields.Char(string="成本类别", compute="_compute_company_finance_visible_fields", store=True, readonly=True)
    company_finance_payee_unit = fields.Char(string="收款单位名称", compute="_compute_company_finance_visible_fields", store=True, readonly=True)
    company_finance_payment_account_name = fields.Char(string="付款账户名称", compute="_compute_company_finance_visible_fields", store=True, readonly=True)
    company_finance_note_display = fields.Char(string="备注", compute="_compute_company_finance_visible_fields", store=True, readonly=True)
    company_finance_source_created_by = fields.Char(string="录入人", compute="_compute_company_finance_visible_fields", store=True, readonly=True)
    company_finance_source_created_at = fields.Char(string="录入时间", compute="_compute_company_finance_visible_fields", store=True, readonly=True)
    company_finance_attachment_text = fields.Char(string="附件", compute="_compute_company_finance_visible_fields", store=True, readonly=True)

    _sql_constraints = [
        (
            "legacy_source_unique",
            "unique(legacy_source_model, legacy_record_id)",
            "历史付款执行来源记录必须唯一。",
        ),
        ("planned_amount_nonnegative", "CHECK(planned_amount >= 0)", "Planned amount must be non-negative."),
        ("paid_amount_nonnegative", "CHECK(paid_amount >= 0)", "Paid amount must be non-negative."),
        ("invoice_amount_nonnegative", "CHECK(invoice_amount >= 0)", "Invoice amount must be non-negative."),
    ]

    @api.depends("payment_request_id", "payment_request_partner_id", "actual_payee_partner_id")
    def _compute_payment_request_partner_relation(self):
        for record in self:
            if not record.payment_request_id:
                record.payment_request_partner_relation = "no_request"
            elif not record.payment_request_partner_id:
                record.payment_request_partner_relation = "missing_request_partner"
            elif not record.actual_payee_partner_id:
                record.payment_request_partner_relation = "missing_actual_payee"
            elif record.payment_request_partner_id == record.actual_payee_partner_id:
                record.payment_request_partner_relation = "same_partner"
            else:
                record.payment_request_partner_relation = "actual_payee_differs"

    @api.depends("source_kind", "payment_family", "payment_method")
    def _compute_execution_flow_label(self):
        for record in self:
            family = (record.payment_family or "").strip()
            method = (record.payment_method or "").strip()
            if family:
                record.execution_flow_label = family
            elif record.source_kind == "actual_outflow":
                record.execution_flow_label = _("实际付款登记")
            elif method:
                record.execution_flow_label = _("付款执行：%s") % method
            else:
                record.execution_flow_label = _("付款执行")

    @staticmethod
    def _partner_payment_state_label(value):
        return {
            "-1": "已作废",
            "0": "未审核",
            "1": "审核中",
            "2": "审核通过",
            "3": "已驳回",
            "4": "已作废",
            "draft": "草稿",
            "confirmed": "已确认",
            "paid": "已付款",
            "legacy_confirmed": "历史已确认",
            "cancel": "已取消",
        }.get(str(value or ""), str(value or ""))

    def _partner_payment_attachment_label(self):
        self.ensure_one()
        count = len(self.attachment_ids)
        return "附件(%s)" % count if count else ""

    @api.depends(
        "state",
        "date_payment",
        "partner_id",
        "receipt_account_name",
        "paid_amount",
        "payment_family",
        "source_kind",
        "payment_method",
        "note",
        "business_category_id",
        "payment_account_name",
        "attachment_ids",
        "kingdee_document_no",
        "handler_name",
        "creator_name",
        "project_id",
        "payment_request_id",
        "document_no",
        "name",
    )
    def _compute_partner_payment_visible_fields(self):
        for record in self:
            record.partner_payment_status_display = record._partner_payment_state_label(record.state)
            record.partner_payment_date_display = fields.Date.to_string(record.date_payment) if record.date_payment else ""
            record.partner_payment_payee_unit = record.partner_id.display_name or record.receipt_account_name or ""
            record.partner_payment_actual_payee_unit = record.receipt_account_name or record.partner_id.display_name or ""
            record.partner_payment_amount_display = str(record.paid_amount or "")
            record.partner_payment_category_display = record.payment_family or record.payment_method or ""
            record.partner_payment_content_display = record.note or ""
            record.partner_payment_method_display = record.payment_family or record.payment_method or ""
            record.partner_payment_cost_type_display = record.business_category_id.display_name or record.payment_family or record.payment_method or ""
            record.partner_payment_account_name_display = record.payment_account_name or ""
            record.partner_payment_attachment_text = record._partner_payment_attachment_label()
            record.partner_payment_voucher_no = record.kingdee_document_no or ""
            record.partner_payment_writer = record.handler_name or record.creator_name or ""
            record.partner_payment_source_created_by = record.creator_name or ""
            record.partner_payment_project_name = record.project_id.display_name or ""
            record.partner_payment_source_text = record.payment_request_id.display_name or record.document_no or record.name or ""
            record.partner_payment_document_no = record.document_no or record.name or ""

    @api.depends(
        "state",
        "legacy_document_state",
        "push_result",
        "document_no",
        "name",
        "paid_amount",
        "payment_family",
        "payment_method",
        "business_category_id",
        "receipt_account_name",
        "partner_id",
        "payment_account_name",
        "note",
        "creator_name",
        "created_time",
        "attachment_ids",
    )
    def _compute_company_finance_visible_fields(self):
        for record in self:
            status_value = record.state
            record.company_finance_status_display = record._partner_payment_state_label(status_value)
            record.company_finance_push_result = record.push_result or ""
            record.company_finance_document_no = record.document_no or record.name or ""
            record.company_finance_amount_display = (
                str(record.paid_amount) if record.paid_amount is not False and record.paid_amount is not None else ""
            )
            record.company_finance_cost_type_display = (
                record.payment_method
                or record.payment_family
                or record.business_category_id.display_name
                or ""
            )
            record.company_finance_payee_unit = record.receipt_account_name or record.partner_id.display_name or ""
            record.company_finance_payment_account_name = record.payment_account_name or ""
            record.company_finance_note_display = record.note or ""
            record.company_finance_source_created_by = record.creator_name or ""
            record.company_finance_source_created_at = (
                fields.Datetime.to_string(record.created_time) if record.created_time else ""
            )
            record.company_finance_attachment_text = record._partner_payment_attachment_label()

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

    def _payment_request_values(self, request):
        if not request:
            return {}
        receipt_account_name = request.payment_account_name or request.partner_account_name or ""
        receipt_bank_name = request.payment_bank_name or request.partner_bank_name or ""
        receipt_account_no = request.payment_account_no or request.partner_bank_account or ""
        payment_account_name = request.payer_unit or request.legacy_payment_account_name or ""
        payment_account_no = request.legacy_payment_account_no or ""
        return {
            "project_id": request.project_id.id,
            "partner_id": request.partner_id.id,
            "contract_id": request.contract_id.id,
            "payment_request_id": request.id,
            "source_kind": "actual_outflow",
            "payment_family": "往来单位付款",
            "document_no": request.name,
            "planned_amount": request.amount or 0.0,
            "paid_amount": request.unpaid_amount or request.amount or 0.0,
            "currency_id": request.currency_id.id,
            "receipt_account_name": receipt_account_name,
            "receipt_bank_name": receipt_bank_name,
            "receipt_account_no": receipt_account_no,
            "payment_account_name": payment_account_name,
            "payment_account_no": payment_account_no,
            "note": request.note or "",
        }

    @api.onchange("payment_request_id")
    def _onchange_payment_request_id(self):
        if not self.payment_request_id:
            return
        for field_name, value in self._payment_request_values(self.payment_request_id).items():
            setattr(self, field_name, value)

    @api.model
    def _caller_visible_payment_relation(self, model_name, record_id, domain=None):
        if not record_id:
            return self.env[model_name]
        relation_domain = [("id", "=", record_id)]
        if domain:
            relation_domain.extend(domain)
        record = self.env[model_name].search(relation_domain, limit=1)
        if not record:
            raise ValidationError(_("付款归集关系不存在或当前用户无权访问。"))
        return record

    @api.model
    def _payment_basis_contracts(self, request):
        contracts = self.env["construction.contract"]
        lines = self.env["payment.request.line"].search(
            [
                ("request_id", "=", request.id),
                ("active", "=", True),
                "|",
                ("settlement_id", "!=", False),
                ("contract_id", "!=", False),
            ]
        )
        line_settlement_ids = set(lines.mapped("settlement_id").ids)

        if lines:
            if request.material_settlement_id:
                raise ValidationError(_("付款申请的材料结算头部依据与结算明细依据冲突。"))
            if request.settlement_id and request.settlement_id.id not in line_settlement_ids:
                raise ValidationError(_("付款申请头部结算不属于其权威结算明细集合。"))
            for line in lines:
                line_contract = self.env["construction.contract"]
                if line.settlement_id:
                    settlement = self._caller_visible_payment_relation(
                        "sc.settlement.order",
                        line.settlement_id.id,
                    )
                    if settlement.project_id != request.project_id:
                        raise ValidationError(_("付款申请结算明细项目与申请项目不一致。"))
                    if settlement.contract_id:
                        line_contract = self._caller_visible_payment_relation(
                            "construction.contract",
                            settlement.contract_id.id,
                        )
                if line.contract_id:
                    explicit_line_contract = self._caller_visible_payment_relation(
                        "construction.contract",
                        line.contract_id.id,
                    )
                    if line_contract and explicit_line_contract != line_contract:
                        raise ValidationError(_("付款申请明细合同与其结算合同不一致。"))
                    line_contract = explicit_line_contract
                if line_contract:
                    if line_contract.project_id != request.project_id:
                        raise ValidationError(_("付款申请明细合同项目与申请项目不一致。"))
                    contracts |= line_contract
        else:
            if request.settlement_id and request.material_settlement_id:
                raise ValidationError(_("付款申请不能同时使用标准结算与材料结算作为头部依据。"))
            if request.settlement_id:
                settlement = self._caller_visible_payment_relation(
                    "sc.settlement.order",
                    request.settlement_id.id,
                )
                if settlement.project_id != request.project_id:
                    raise ValidationError(_("付款申请结算项目与申请项目不一致。"))
                if settlement.contract_id:
                    contracts |= self._caller_visible_payment_relation(
                        "construction.contract",
                        settlement.contract_id.id,
                    )
            elif request.material_settlement_id:
                material_settlement = self._caller_visible_payment_relation(
                    "sc.material.settlement",
                    request.material_settlement_id.id,
                )
                if material_settlement.project_id != request.project_id:
                    raise ValidationError(_("付款申请材料结算项目与申请项目不一致。"))
        if request.contract_id:
            request_contract = self._caller_visible_payment_relation(
                "construction.contract",
                request.contract_id.id,
            )
            if len(contracts) > 1:
                raise ValidationError(_("多合同付款申请不得压缩到单值合同字段。"))
            if not contracts:
                # 合同本身是预付款、保证金等未结算付款的有效业务依据。
                contracts |= request_contract
            if request_contract != contracts:
                raise ValidationError(_("付款申请合同与其有效来源合同不一致。"))
        return contracts

    @api.model
    def _normalize_payment_relation_values(self, vals, current=None):
        values = dict(vals)

        def relation_id(field_name):
            if field_name in values:
                return values.get(field_name) or False
            return current[field_name].id if current and current[field_name] else False

        request_id = relation_id("payment_request_id")
        execution_contract_id = relation_id("contract_id")
        project_id = relation_id("project_id")
        actual_payee_id = relation_id("partner_id")
        if not request_id:
            return values

        request = self._caller_visible_payment_relation("payment.request", request_id)
        request._assert_payment_execution_ready(require_authorized_actor=current is None)
        contracts = self._payment_basis_contracts(request)
        if project_id and project_id != request.project_id.id:
            raise ValidationError(_("付款执行项目必须与付款申请项目一致。"))
        if len(contracts) == 1:
            unique_contract = contracts
            if execution_contract_id and execution_contract_id != unique_contract.id:
                raise ValidationError(_("付款执行合同必须与申请的唯一来源合同一致。"))
            values.setdefault("contract_id", unique_contract.id)
        elif len(contracts) > 1:
            if execution_contract_id:
                raise ValidationError(_("多合同付款依据不得写入任意单一执行合同。"))
            values["contract_id"] = False
        elif execution_contract_id:
            raise ValidationError(_("付款执行合同没有对应的有效申请来源依据。"))

        values.setdefault("project_id", request.project_id.id)
        if actual_payee_id:
            self._caller_visible_payment_relation("res.partner", actual_payee_id)
        else:
            values.setdefault("partner_id", request.partner_id.id)
        return values

    @api.model
    def _assert_unique_request_anchors(self, request_ids):
        """Reject known duplicates; the partial unique index closes races."""
        request_ids = [int(request_id) for request_id in request_ids if request_id]
        if not request_ids:
            return
        if len(request_ids) != len(set(request_ids)):
            raise ValidationError(_("同一付款申请不能在一次操作中生成多条付款登记。"))
        visible_request_ids = set(
            self.env["payment.request"].search([("id", "in", request_ids)]).ids
        )
        if visible_request_ids != set(request_ids):
            raise ValidationError(_("付款申请不存在或已被删除。"))
        existing = self.sudo().search(
            [
                ("payment_request_id", "in", request_ids),
                ("state", "in", ("draft", "confirmed")),
            ],
            limit=1,
        )
        if existing:
            raise ValidationError(
                _("该付款申请已存在办理中的付款登记：%(execution)s")
                % {"execution": existing.display_name}
            )

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env["ir.sequence"]
        normalized_vals_list = []
        self._assert_unique_request_anchors(
            [vals.get("payment_request_id") for vals in vals_list]
        )
        for incoming_vals in vals_list:
            vals = dict(incoming_vals)
            project_id = self._context_project_id()
            if project_id:
                vals.setdefault("project_id", project_id)
            vals = self._normalize_payment_relation_values(vals)
            if vals.get("payment_request_id"):
                request = self._caller_visible_payment_relation("payment.request", vals["payment_request_id"])
                request._assert_payment_execution_ready(require_authorized_actor=True)
                request_values = self._payment_request_values(request)
                for field_name in (
                    "receipt_account_name",
                    "receipt_bank_name",
                    "receipt_account_no",
                ):
                    if field_name in vals and (vals.get(field_name) or "") != (
                        request_values.get(field_name) or ""
                    ):
                        raise ValidationError(_("收款账户必须来自付款申请的权威账户快照，不允许改写。"))
                    vals[field_name] = request_values.get(field_name) or ""
                for field_name, value in request_values.items():
                    vals.setdefault(field_name, value)
            vals.setdefault("business_category_id", self._resolve_business_category_id(vals))
            if vals.get("name", "新建") == "新建":
                vals["name"] = seq.next_by_code("sc.payment.execution") or _("Payment Execution")
            normalized_vals_list.append(vals)
        try:
            with self.env.cr.savepoint(flush=False):
                records = super().create(normalized_vals_list)
                records.flush_recordset(["payment_request_id", "state"])
                return records
        except UniqueViolation as error:
            if error.diag.constraint_name == "sc_payment_execution_one_active_per_request_idx":
                raise ValidationError(_("该付款申请已存在办理中的付款登记，请刷新后查看。")) from error
            raise

    @api.model
    def _resolve_business_category_code(self, vals):
        code = self.env.context.get("default_business_category_code") or self.env.context.get(
            "current_business_category_code"
        )
        if code:
            return code
        payment_family = vals.get("payment_family") or self.env.context.get("default_payment_family") or ""
        if payment_family in ("公司财务支出", "actual_outflow"):
            return "finance.payment.execution.company"
        return "finance.payment.execution.partner"

    @api.model
    def _resolve_business_category_id(self, vals):
        code = self._resolve_business_category_code(vals)
        category = self.env["sc.business.category"].sudo().search(
            [("code", "=", code), ("target_model", "=", self._name)],
            limit=1,
        )
        return category.id if category else False

    def _history_surface_allowed_write_fields(self):
        return {"attachment_ids"}

    def _business_fact_fields(self):
        """Facts frozen once the execution leaves its correction state.

        State transitions, approval metadata and chatter remain managed by their
        authoritative workflows.  The facts that determine who is paid, how
        much is paid and through which accounts must not drift after submit.
        """
        return {
            "business_category_id",
            "date_payment",
            "document_no",
            "payment_family",
            "payment_method",
            "bank_account",
            "payment_account_name",
            "payment_account_no",
            "payment_bank_name",
            "receipt_account_name",
            "receipt_account_no",
            "receipt_bank_name",
            "handler_name",
            "planned_amount",
            "paid_amount",
            "invoice_amount",
            "currency_id",
            "note",
            "attachment_ids",
        }

    def _assert_payment_relation_anchors_immutable(self, vals):
        """Keep an execution's authoritative request chain from being rebound."""
        relation_fields = {"payment_request_id", "contract_id", "partner_id", "project_id"}
        changed_fields = relation_fields.intersection(vals)
        if not changed_fields:
            return True
        controlled_history_fill = bool(
            self.env.context.get("history_surface_sync") and self.env.su
        )
        for rec in self:
            for field_name in changed_fields:
                current_id = rec[field_name].id if rec[field_name] else False
                incoming = vals.get(field_name)
                incoming_id = incoming.id if isinstance(incoming, models.BaseModel) else (incoming or False)
                if current_id == incoming_id:
                    continue
                if self.env.su and (not current_id or not incoming_id):
                    # R10-v2: superuser maintenance may clear or back-fill an
                    # anchor (e.g. repairing a draft chain); regular users can
                    # never rebind. Downstream state guards still keep records
                    # with a broken chain from progressing.
                    continue
                if (
                    controlled_history_fill
                    and rec.source_origin == "legacy"
                    and not current_id
                    and incoming_id
                ):
                    continue
                raise UserError(
                    _("付款执行一经建立，不允许改绑付款申请、合同、项目或往来单位；历史同步仅可补充空锚点。")
                )
        return True

    def write(self, vals):
        cancellation_metadata = {"cancellation_kind", "reversal_reason"}.intersection(vals)
        if cancellation_metadata and not self.env.context.get("allow_payment_cancel_metadata"):
            if "cancellation_kind" in vals:
                raise UserError(_("撤销类型只能由付款执行的受控取消流程维护。"))
            if any(rec.state != "paid" for rec in self):
                raise UserError(_("只有已付款记录可以填写冲销原因。"))
        if (
            any(rec.source_origin == "legacy" and rec.state == "legacy_confirmed" for rec in self)
            and not self.env.context.get("history_surface_sync")
        ):
            projection_fields = {
                name
                for name in self._fields
                if name.startswith("partner_payment_") or name.startswith("company_finance_")
            }
            allowed = {
                "payment_request_id",
                "partner_id",
                "contract_id",
                "creator_name",
                "created_time",
                "note",
                "active",
                "write_uid",
                "write_date",
            } | projection_fields | self._history_surface_allowed_write_fields()
            if set(vals) - allowed:
                raise UserError(_("历史迁移付款执行单据已确认，只允许补充业务锚点和备注。"))
        changed_business_facts = self._business_fact_fields().intersection(vals)
        if changed_business_facts and any(
            rec.source_origin != "legacy" and rec.state != "draft" for rec in self
        ):
            raise UserError(_("付款执行提交后业务事实不可直接修改；请先按合法流程撤销，再重新办理。"))
        immutable_receipt_fields = {
            "receipt_account_name",
            "receipt_bank_name",
            "receipt_account_no",
        }.intersection(vals)
        for rec in self.filtered("payment_request_id"):
            request_values = rec._payment_request_values(rec.payment_request_id)
            if any(
                (vals.get(field_name) or "") != (request_values.get(field_name) or "")
                for field_name in immutable_receipt_fields
            ):
                raise UserError(_("收款账户来自付款申请的权威账户快照，付款登记中不可改写。"))
        relation_fields = {"payment_request_id", "contract_id", "partner_id", "project_id"}
        if relation_fields.intersection(vals):
            result = True
            for rec in self:
                rec._assert_payment_relation_anchors_immutable(vals)
                normalized_vals = rec._normalize_payment_relation_values(
                    vals,
                    current=rec,
                )
                rec._assert_payment_relation_anchors_immutable(normalized_vals)
                result = super(ScPaymentExecution, rec).write(normalized_vals) and result
            return result
        return super().write(vals)

    def action_confirm(self):
        self._assert_finance_handling_access()
        policy = self.env["sc.approval.policy"]
        for rec in self:
            if rec.state != "draft":
                raise_guard(
                    "PAYMENT_EXECUTION_INVALID_TRANSITION",
                    f"付款执行[{rec.display_name}]",
                    _("确认付款执行"),
                    reasons=[_("只有草稿状态的付款执行可以确认")],
                )
            rec._check_business_anchor_or_raise()
            rec._check_payment_request_scope_or_raise()
            rec._check_company_contractor_payment_responsibility_or_raise()
            if policy.is_approval_required(rec._name, company=rec.company_id):
                company = rec.company_id or self.env.company
                rec.with_company(company).with_context(allowed_company_ids=[company.id])._request_document_approval()
            else:
                rec.write({"state": "confirmed", "reject_reason": False})

    def action_paid(self):
        self._assert_finance_confirm_access()
        policy = self.env["sc.approval.policy"]
        for rec in self:
            if rec.state != "confirmed":
                raise_guard(
                    "PAYMENT_EXECUTION_INVALID_TRANSITION",
                    f"付款执行[{rec.display_name}]",
                    _("登记付款"),
                    reasons=[_("只有完成审批并处于已确认状态的付款执行可以登记付款")],
                )
            rec._check_business_anchor_or_raise()
            rec._check_payment_request_scope_or_raise()
            rec._check_company_contractor_payment_responsibility_or_raise()
            if policy.is_approval_required(rec._name, company=rec.company_id) and rec.validation_status != "validated":
                raise UserError(_("付款执行尚未完成统一审批流程。"))
            rec.state = "paid"
            rec._sync_payment_request_done()
            rec.message_post(body=_("付款登记已完成，付款申请、付款台账与审计状态已同步。"))

    def _has_finance_confirm_access(self):
        return self.env.user.has_group("smart_construction_core.group_sc_cap_finance_manager")

    def _has_finance_handling_access(self):
        return self.env.user.has_group("smart_construction_core.group_sc_cap_finance_user")

    def _assert_finance_handling_access(self):
        if not self._has_finance_handling_access():
            raise UserError(_("你没有提交付款登记的财务办理权限。"))

    def _assert_finance_confirm_access(self):
        if not self._has_finance_confirm_access():
            raise UserError(_("你没有登记付款的财务确认权限。"))

    def _assert_finance_cancel_access(self):
        if not self._has_finance_confirm_access():
            raise UserError(_("你没有取消或撤销付款执行的财务权限。"))

    def _sync_payment_request_done(self):
        for rec in self:
            request = rec.payment_request_id
            if not request or request.state == "done":
                continue
            rec._check_payment_request_scope_or_raise()
            if request.state == "approve" and request.validation_status == "validated":
                request.action_set_approved()
                request.invalidate_recordset()
            if request.state != "approved":
                continue
            rounding = request.currency_id.rounding if request.currency_id else 0.01
            remaining_before = request.unpaid_amount or 0.0
            if float_compare(rec.paid_amount or 0.0, remaining_before, precision_rounding=rounding) == 1:
                raise UserError(_("本次实付金额超过付款申请剩余可付金额。"))
            before = request._snapshot_audit_payload()
            request.with_context(payment_soft_gate=True)._ensure_payment_ledger(
                amount=rec.paid_amount or 0.0,
                ref=rec.name,
                note=_("auto:payment_execution_paid"),
                execution=rec,
            )
            request.invalidate_recordset(["paid_amount_total", "unpaid_amount", "is_fully_paid"])
            if request.is_fully_paid:
                request.with_context(allow_transition=True, payment_soft_gate=True).write({"state": "done"})
            after = request._snapshot_audit_payload()
            request._audit_transition(
                "payment_paid" if request.is_fully_paid else "payment_partially_paid",
                before,
                after,
                action_name="payment_execution_paid",
            )

    def action_cancel(self):
        self._assert_finance_cancel_access()
        for rec in self:
            if rec.source_origin == "legacy":
                raise UserError(_("历史迁移付款执行单据不能在新系统取消。"))
            if rec.state == "paid":
                rec.action_reverse_payment()
                continue
            if rec.state in ("legacy_confirmed", "cancel"):
                raise_guard(
                    "PAYMENT_EXECUTION_INVALID_TRANSITION",
                    f"付款执行[{rec.display_name}]",
                    _("取消付款执行"),
                    reasons=[_("历史已确认或已取消的付款执行不能取消")],
                )
            rec.with_context(allow_payment_cancel_metadata=True).write(
                {"state": "cancel", "cancellation_kind": "cancelled_before_payment"}
            )

    def action_reverse_payment(self):
        """Reverse a posted payment without conflating it with pre-payment cancel."""
        self._assert_finance_cancel_access()
        for rec in self:
            if rec.source_origin == "legacy":
                raise UserError(_("历史迁移付款执行单据不能在新系统冲销。"))
            if rec.state != "paid":
                raise_guard(
                    "PAYMENT_EXECUTION_REVERSAL_INVALID_STATE",
                    f"付款执行[{rec.display_name}]",
                    _("冲销已付款"),
                    reasons=[_("只有已付款的付款执行才能冲销")],
                )
            if not (rec.reversal_reason or "").strip():
                raise UserError(_("撤销已付款记录前必须填写冲销原因。"))
            rec._reverse_paid_execution()

    def _reverse_paid_execution(self):
        for rec in self:
            request = rec.payment_request_id
            if not request:
                raise_guard(
                    "PAYMENT_EXECUTION_MISSING_REQUEST",
                    f"付款执行[{rec.display_name}]",
                    _("撤销已付款"),
                    reasons=[_("已付款执行必须关联付款申请才能撤销")],
                )
            ledger = self.env["payment.ledger"].sudo().search(
                [
                    ("payment_request_id", "=", request.id),
                    ("payment_execution_id", "=", rec.id),
                    ("state", "=", "posted"),
                ],
                limit=1,
            )
            if not ledger:
                ledger = self.env["payment.ledger"].sudo().search(
                    [
                        ("payment_request_id", "=", request.id),
                        ("payment_execution_id", "=", False),
                        ("state", "=", "posted"),
                    ],
                    limit=1,
                )
            if not ledger:
                raise_guard(
                    "PAYMENT_LEDGER_NOT_FOUND",
                    f"付款执行[{rec.display_name}]",
                    _("撤销已付款"),
                    reasons=[_("未找到对应付款台账，不能自动撤销")],
                )
            before = request._snapshot_audit_payload()
            reversal_reason = (rec.reversal_reason or "").strip()
            if not reversal_reason:
                raise UserError(_("撤销已付款记录前必须填写冲销原因。"))
            ledger.action_reverse(rec, reason=reversal_reason)
            if request.state == "done":
                request.with_context(allow_transition=True, payment_soft_gate=True).write({"state": "approved"})
            rec.with_context(allow_payment_cancel_metadata=True).write(
                {"state": "cancel", "cancellation_kind": "payment_reversed"}
            )
            after = request._snapshot_audit_payload()
            request._audit_transition("payment_reversed", before, after, action_name="payment_execution_cancel")
            rec.message_post(body=_("已撤销付款登记，并将付款申请退回已批准状态。"))

    def _check_business_anchor_or_raise(self):
        for rec in self:
            if rec.source_origin == "legacy":
                continue
            if not rec.project_id:
                raise_guard(
                    "PAYMENT_EXECUTION_MISSING_PROJECT",
                    f"付款执行[{rec.display_name}]",
                    _("办理付款执行"),
                    reasons=[_("付款执行必须关联项目")],
                )
            if not rec.payment_request_id:
                raise_guard(
                    "PAYMENT_EXECUTION_MISSING_REQUEST",
                    f"付款执行[{rec.display_name}]",
                    _("办理付款执行"),
                    reasons=[_("新系统付款执行必须关联已审批的付款申请")],
                )
            request = rec.payment_request_id
            material_settlement = request.material_settlement_id if request else False
            if not rec.contract_id and not material_settlement and not (request and request._has_payment_basis()):
                raise_guard(
                    "PAYMENT_EXECUTION_MISSING_CONTRACT",
                    f"付款执行[{rec.display_name}]",
                    _("办理付款执行"),
                    reasons=[_("新系统付款执行必须关联合同或结算依据")],
                )
            if not rec.partner_id:
                raise_guard(
                    "PAYMENT_EXECUTION_MISSING_PARTNER",
                    f"付款执行[{rec.display_name}]",
                    _("办理付款执行"),
                    reasons=[_("付款执行必须选择往来单位")],
                )
            if (rec.paid_amount or 0.0) <= 0:
                raise_guard(
                    "PAYMENT_EXECUTION_INVALID_AMOUNT",
                    f"付款执行[{rec.display_name}]",
                    _("办理付款执行"),
                    reasons=[_("实付金额必须大于0")],
                )
            request = rec.payment_request_id
            rounding = rec.currency_id.rounding if rec.currency_id else 0.01
            if request and float_compare(
                rec.paid_amount or 0.0,
                request.unpaid_amount or 0.0,
                precision_rounding=rounding,
            ) == 1:
                raise_guard(
                    "PAYMENT_EXECUTION_AMOUNT_EXCEEDS_REQUEST",
                    f"付款执行[{rec.display_name}]",
                    _("办理付款执行"),
                    reasons=[_("本次实付金额不得超过付款申请剩余可付金额")],
                )
            payer_fields = (
                rec.payment_account_name,
                rec.payment_bank_name,
                rec.payment_account_no or rec.bank_account,
            )
            payee_fields = (
                rec.receipt_account_name,
                rec.receipt_bank_name,
                rec.receipt_account_no,
            )
            # R10-v2: accounts inherited verbatim from the payment request's
            # authoritative snapshot are accepted as-is (legacy chains may
            # only carry payer name/account-no, and the snapshot carries no
            # payment method). Any manually entered account data must be
            # complete — full payer/payee triples plus a payment method.
            request_snapshot = (
                rec._payment_request_values(rec.payment_request_id)
                if rec.payment_request_id
                else {}
            )

            def _matches_snapshot(field_names):
                if not request_snapshot:
                    return False
                return all(
                    (getattr(rec, name) or "") == (request_snapshot.get(name) or "")
                    for name in field_names
                )

            payer_from_snapshot = _matches_snapshot(
                ("payment_account_name", "payment_bank_name", "payment_account_no")
            )
            payee_from_snapshot = _matches_snapshot(
                ("receipt_account_name", "receipt_bank_name", "receipt_account_no")
            )
            if not payer_from_snapshot:
                if not all(payer_fields):
                    raise_guard(
                        "PAYMENT_EXECUTION_MISSING_PAYER_ACCOUNT",
                        f"付款执行[{rec.display_name}]",
                        _("办理付款执行"),
                        reasons=[_("新系统付款执行必须完整填写付款户名、开户行和账号")],
                    )
                if not (rec.payment_method or "").strip():
                    raise_guard(
                        "PAYMENT_EXECUTION_MISSING_PAYMENT_METHOD",
                        f"付款执行[{rec.display_name}]",
                        _("办理付款执行"),
                        reasons=[_("付款执行必须选择付款方式")],
                    )
            if not payee_from_snapshot and not all(payee_fields):
                raise_guard(
                    "PAYMENT_EXECUTION_MISSING_PAYEE_ACCOUNT",
                    f"付款执行[{rec.display_name}]",
                    _("办理付款执行"),
                    reasons=[_("新系统付款执行必须具备完整收款户名、开户行和账号")],
                )

    def _check_payment_request_scope_or_raise(self):
        for rec in self:
            request = rec.payment_request_id
            if not request:
                continue
            if rec.source_origin == "legacy" and rec.state == "legacy_confirmed":
                continue
            if request.type != "pay":
                raise UserError(_("付款登记只能关联付款类型的付款申请。"))
            if rec.project_id and request.project_id and rec.project_id != request.project_id:
                raise UserError(_("付款登记项目必须与付款申请项目一致。"))
            if rec.contract_id and request.contract_id and rec.contract_id != request.contract_id:
                raise UserError(_("付款登记合同必须与付款申请合同一致。"))

    @api.constrains("payment_request_id", "project_id", "partner_id", "contract_id")
    def _check_payment_request_scope_consistency(self):
        """Reject forged execution anchors at ORM create/write, not only at actions."""
        for rec in self:
            rec._normalize_payment_relation_values({}, current=rec)
        self._check_payment_request_scope_or_raise()

    def _company_contractor_payment_responsibility_failures(self, summary, paid_amount):
        return self._company_contractor_responsibility_balance_failures(summary, paid_amount, _("本次实付金额"))

    def _check_company_contractor_payment_responsibility_or_raise(self):
        for rec in self:
            if rec.source_origin == "legacy" and rec.state == "legacy_confirmed":
                continue
            summary = rec.company_contractor_responsibility_summary_id
            if not summary:
                continue
            failures = rec._company_contractor_payment_responsibility_failures(summary, rec.paid_amount or 0.0)
            if failures:
                raise_guard(
                    "PAYMENT_EXECUTION_RESPONSIBILITY_BALANCE_BLOCKED",
                    f"付款执行[{rec.display_name}]",
                    _("办理付款执行"),
                    reasons=failures,
                    hints=[_("打开公司-承包人责任余额，核对到款确认、自筹、拨付和扣款明细后再继续办理。")],
                )

    def _request_document_approval(self):
        self.ensure_one()
        if self.review_ids and self.validation_status == "rejected":
            self.restart_validation()
        elif not self.review_ids or self.validation_status == "no":
            reviews = self.request_validation()
            if not reviews:
                raise UserError(_("付款执行已启用审批，但没有匹配的统一审批规则，请检查业务审批配置。"))
        else:
            raise UserError(_("付款执行已经在统一审批流程中，请等待审批完成。"))

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
            if rec.state == "draft":
                rec.with_context(skip_validation_check=True).write({"state": "confirmed", "reject_reason": False})

    def action_on_tier_rejected(self, reason=None):
        for rec in self:
            if rec.state == "draft":
                rec.with_context(skip_validation_check=True).write(
                    {"reject_reason": reason or rec._get_tier_reject_reason()}
                )

    def init(self):
        self.env.cr.execute(
            "DROP INDEX IF EXISTS sc_payment_execution_one_active_per_request_idx"
        )
        self.env.cr.execute(
            "CREATE UNIQUE INDEX "
            "sc_payment_execution_one_active_per_request_idx "
            "ON sc_payment_execution (payment_request_id) "
            "WHERE payment_request_id IS NOT NULL AND state IN ('draft', 'confirmed')"
        )
        self.env.cr.execute(
            """
            UPDATE sc_payment_execution execution
               SET business_category_id = category.id
              FROM sc_business_category category
             WHERE execution.business_category_id IS NULL
               AND category.target_model = 'sc.payment.execution'
               AND category.code = CASE
                   WHEN COALESCE(execution.payment_family, '') IN ('公司财务支出', 'actual_outflow')
                       THEN 'finance.payment.execution.company'
                   ELSE 'finance.payment.execution.partner'
               END
            """
        )
