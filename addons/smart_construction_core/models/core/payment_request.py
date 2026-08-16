# -*- coding: utf-8 -*-
import logging
import re
from decimal import Decimal, ROUND_HALF_UP

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError, UserError
from odoo.tools.float_utils import float_compare

from ..support import operating_metrics as opm
from ..support.state_guard import raise_guard
from ..support.state_machine import ScStateMachine

_logger = logging.getLogger(__name__)

PAYMENT_REQUEST_DOCUMENT_STATE_LABELS = {
    "-1": "已作废",
    "0": "未审核",
    "1": "审批中",
    "2": "审核通过",
}

PAYMENT_APPLY_ACCEPTANCE_VISIBLE_INDEXES = {
    "单据状态": 1,
    "单据编号": 2,
    "申请日期": 3,
    "项目名称": 4,
    "收款单位": 5,
    "实际收款单位": 6,
    "付款单位": 7,
    "申请付款金额": 8,
    "实际付款金额": 9,
    "类型（成本）": 11,
    "备注": 12,
    "是否关联单据": 13,
    "付款账号": 14,
    "金额大写": 15,
    "户名": 16,
    "开户行": 17,
    "账号": 18,
    "录入人": 20,
    "录入时间": 21,
}


def _amount_to_chinese_upper(value):
    amount = Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if amount == 0:
        return "零元整"
    prefix = "负" if amount < 0 else ""
    cents = int(abs(amount) * 100)
    integer = cents // 100
    jiao = cents // 10 % 10
    fen = cents % 10
    digits = "零壹贰叁肆伍陆柒捌玖"
    units = ["", "拾", "佰", "仟"]
    section_units = ["", "万", "亿", "兆"]

    def section_to_text(section):
        text = ""
        zero = False
        for index, char in enumerate(f"{section:04d}"):
            digit = int(char)
            if digit:
                if zero:
                    text += digits[0]
                    zero = False
                text += digits[digit] + units[3 - index]
            elif text:
                zero = True
        return text

    parts = []
    section_index = 0
    need_zero = False
    while integer:
        section = integer % 10000
        if section:
            text = section_to_text(section) + section_units[section_index]
            if need_zero:
                parts.insert(0, digits[0])
            parts.insert(0, text)
            need_zero = section < 1000
        elif parts:
            need_zero = True
        integer //= 10000
        section_index += 1

    result = prefix + "".join(parts).rstrip(digits[0]) + "元"
    if jiao:
        result += digits[jiao] + "角"
    if fen:
        result += digits[fen] + "分"
    if not jiao and not fen:
        result += "整"
    return result


class PaymentRequest(models.Model):
    _name = "payment.request"
    _description = "付款/收款申请"
    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
        "tier.validation",
        "sc.delete.guard.mixin",
        "sc.company.contractor.responsibility.context.mixin",
    ]
    _order = "id desc"
    _rec_names_search = [
        "name",
        "project_id.name",
        "partner_id.name",
        "actual_payee_unit",
        "payer_unit",
        "payment_account_name",
        "contract_id.subject",
        "contract_id.legacy_contract_no",
        "contract_id.legacy_document_no",
    ]
    _sc_delete_guard_blocker_models = (
        "sc.material.rental.order",
    )

    name = fields.Char(string="申请单号", required=True, default="New", copy=False, tracking=True)
    type = fields.Selection(
        [("pay", "付款"), ("receive", "收款")],
        string="类型",
        default="pay",
        required=True,
        tracking=True,
    )
    payment_flow_label = fields.Char(string="办理事项", compute="_compute_payment_flow_label")
    business_category_id = fields.Many2one(
        "sc.business.category",
        string="业务分类",
        index=True,
        ondelete="restrict",
        domain="[('target_model', '=', 'payment.request')]",
    )
    receipt_type = fields.Char(
        string="登记类型",
        index=True,
        tracking=True,
        help="收款申请的产品登记类型。",
    )
    # 兼容部分搜索条件（有时被带入 account.move 的 move_type 过滤）
    move_type = fields.Selection(
        [("pay", "付款"), ("receive", "收款")],
        string="单据类型",
        compute="_compute_move_type",
        store=False,
    )
    project_id = fields.Many2one(
        "project.project",
        string="项目",
        required=True,
        index=True,
        tracking=True,
    )
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
    contract_id = fields.Many2one(
        "construction.contract",
        string="合同",
        domain="[('project_id', '=', project_id)]",
        tracking=True,
    )
    contract_currency_id = fields.Many2one(
        "res.currency",
        string="合同币种",
        related="contract_id.currency_id",
        readonly=True,
    )
    contract_payment_terms = fields.Text(
        string="合同付款条件",
        related="contract_id.contract_payment_method_text",
        readonly=True,
    )
    contract_change_amount = fields.Monetary(
        string="合同累计变更",
        currency_field="contract_currency_id",
        related="contract_id.amount_change",
        readonly=True,
    )
    contract_final_amount = fields.Monetary(
        string="最终合同价",
        currency_field="contract_currency_id",
        related="contract_id.amount_final",
        readonly=True,
    )
    contract_settlement_amount = fields.Monetary(
        string="合同累计结算",
        currency_field="contract_currency_id",
        related="contract_id.settlement_amount",
        readonly=True,
    )
    contract_invoice_amount = fields.Monetary(
        string="合同累计开票",
        currency_field="contract_currency_id",
        related="contract_id.invoice_amount",
        readonly=True,
    )
    contract_paid_amount = fields.Monetary(
        string="合同累计付款",
        currency_field="contract_currency_id",
        related="contract_id.paid_amount",
        readonly=True,
    )
    contract_unpaid_amount = fields.Monetary(
        string="合同未付余额",
        currency_field="contract_currency_id",
        related="contract_id.unpaid_amount",
        readonly=True,
    )
    settlement_id = fields.Many2one(
        "sc.settlement.order",
        string="结算单",
        domain="[('project_id', '=', project_id), ('state', '=', 'approve')]",
        tracking=True,
    )
    material_settlement_id = fields.Many2one(
        "sc.material.settlement",
        string="材料结算单",
        domain="[('project_id', '=', project_id), ('state', '=', 'confirmed')]",
        index=True,
        tracking=True,
        ondelete="set null",
    )
    settlement_currency_id = fields.Many2one(
        "res.currency",
        string="结算币种",
        related="settlement_id.currency_id",
        store=True,
        readonly=True,
    )
    settlement_amount_total = fields.Monetary(
        string="结算总额",
        currency_field="settlement_currency_id",
        related="settlement_id.amount_total",
        store=True,
        readonly=True,
    )
    settlement_period_start = fields.Date(
        string="结算期间开始",
        related="settlement_id.settlement_period_start",
        readonly=True,
    )
    settlement_period_end = fields.Date(
        string="结算期间结束",
        related="settlement_id.settlement_period_end",
        readonly=True,
    )
    settlement_submitted_amount = fields.Monetary(
        string="结算送审金额",
        currency_field="settlement_currency_id",
        related="settlement_id.submitted_amount",
        readonly=True,
    )
    settlement_approved_amount = fields.Monetary(
        string="结算审定金额",
        currency_field="settlement_currency_id",
        related="settlement_id.approved_amount",
        readonly=True,
    )
    settlement_deduction_amount = fields.Monetary(
        string="结算扣款金额",
        currency_field="settlement_currency_id",
        related="settlement_id.deduction_amount",
        readonly=True,
    )
    settlement_paid_amount = fields.Monetary(
        string="结算已付款",
        currency_field="settlement_currency_id",
        related="settlement_id.paid_amount",
        store=True,
        readonly=True,
    )
    settlement_remaining_amount = fields.Monetary(
        string="剩余额度",
        currency_field="settlement_currency_id",
        related="settlement_id.remaining_amount",
        store=True,
        readonly=True,
    )
    settlement_amount_payable = fields.Monetary(
        string="可付余额",
        currency_field="settlement_currency_id",
        related="settlement_id.amount_payable",
        store=True,
        readonly=True,
    )
    is_overpay_risk = fields.Boolean(
        string="超付风险",
        compute="_compute_is_overpay_risk",
        store=False,
        help="用于列表高亮：当申请金额超过结算可付余额时为 True。",
    )
    line_settlement_count = fields.Integer(
        string="明细结算单数",
        compute="_compute_line_settlement_summary",
        store=True,
        compute_sudo=True,
    )
    line_settlement_summary = fields.Char(
        string="明细结算依据",
        compute="_compute_line_settlement_summary",
        store=True,
        compute_sudo=True,
    )
    legacy_relation_count = fields.Integer(
        string="历史关联依据数",
        compute="_compute_legacy_relation_summary",
        store=True,
        compute_sudo=True,
    )
    legacy_relation_summary = fields.Char(
        string="历史关联依据",
        compute="_compute_legacy_relation_summary",
        store=True,
        compute_sudo=True,
    )
    payment_basis_type = fields.Selection(
        [
            ("standard_settlement", "标准结算单"),
            ("line_settlement", "明细结算单"),
            ("material_settlement", "材料结算单"),
            ("contract", "合同依据"),
            ("legacy_relation", "历史关联依据"),
            ("none", "无可解释依据"),
        ],
        string="依据口径",
        compute="_compute_payment_basis_type",
        store=True,
        compute_sudo=True,
        index=True,
    )
    settlement_compliance_state = fields.Selection(
        related="settlement_id.compliance_state",
        string="匹配状态",
        readonly=True,
        store=True,
    )
    settlement_compliance_message = fields.Text(
        related="settlement_id.compliance_message",
        string="匹配提示",
        readonly=True,
        store=True,
    )
    settlement_match_blocked = fields.Boolean(
        string="匹配阻断",
        compute="_compute_settlement_match_flags",
        store=False,
    )
    settlement_match_warn = fields.Boolean(
        string="匹配警告",
        compute="_compute_settlement_match_flags",
        store=False,
    )
    settlement_amount_insufficient = fields.Boolean(
        string="结算额度不足",
        compute="_compute_settlement_amount_insufficient",
        store=False,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="往来单位",
        required=True,
        tracking=True,
    )
    partner_transaction_eligibility = fields.Selection(
        related="partner_id.sc_transaction_eligibility",
        string="往来单位可办理性",
        readonly=True,
    )
    partner_transaction_eligibility_reason = fields.Char(
        related="partner_id.sc_transaction_eligibility_reason",
        string="往来单位办理提示",
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="币种",
        required=True,
        default=lambda self: self.env.ref("base.CNY", raise_if_not_found=False) or self.env.company.currency_id,
    )
    amount = fields.Monetary(
        string="申请金额",
        currency_field="currency_id",
        required=True,
        tracking=True,
    )
    amount_uppercase = fields.Char(
        string="金额大写",
        compute="_compute_amount_uppercase",
        store=True,
        readonly=True,
        index=True,
    )
    accepted_amount_uppercase = fields.Char(
        string="用户确认金额大写",
        index=True,
        tracking=True,
        help="用户确认验收口径的金额大写；用于历史数据延续和后续业务办理。",
    )
    document_status_display = fields.Char(
        string="单据状态",
        compute="_compute_payment_apply_formal_visible_fields",
        store=True,
        readonly=True,
    )
    project_name_display = fields.Char(
        string="项目名称",
        compute="_compute_payment_apply_formal_visible_fields",
        store=True,
        readonly=True,
    )
    payee_unit_display = fields.Char(
        string="收款单位",
        compute="_compute_payment_apply_formal_visible_fields",
        store=True,
        readonly=True,
    )
    actual_payee_unit_display = fields.Char(
        string="实际收款单位",
        compute="_compute_payment_apply_formal_visible_fields",
        store=True,
        readonly=True,
    )
    payer_unit_display = fields.Char(
        string="付款单位",
        compute="_compute_payment_apply_formal_visible_fields",
        store=True,
        readonly=True,
    )
    request_amount_display = fields.Monetary(
        string="申请付款金额",
        currency_field="currency_id",
        compute="_compute_payment_apply_formal_visible_fields",
        store=True,
        readonly=True,
    )
    actual_paid_amount_display = fields.Monetary(
        string="实际付款金额",
        currency_field="currency_id",
        compute="_compute_payment_apply_formal_visible_fields",
        store=True,
        readonly=True,
    )
    cost_type_display = fields.Char(
        string="类型（成本）",
        compute="_compute_payment_apply_formal_visible_fields",
        store=True,
        readonly=True,
    )
    note_display = fields.Char(
        string="备注",
        compute="_compute_payment_apply_formal_visible_fields",
        store=True,
        readonly=True,
    )
    related_document_text = fields.Char(
        string="是否关联单据",
        compute="_compute_payment_apply_formal_visible_fields",
        store=True,
        readonly=True,
    )
    payment_account_no_display = fields.Char(
        string="付款账号",
        compute="_compute_payment_apply_formal_visible_fields",
        store=True,
        readonly=True,
    )
    amount_uppercase_display = fields.Char(
        string="金额大写",
        compute="_compute_payment_apply_formal_visible_fields",
        store=True,
        readonly=True,
    )
    payee_account_name_display = fields.Char(
        string="户名",
        compute="_compute_payment_apply_formal_visible_fields",
        store=True,
        readonly=True,
    )
    payee_bank_name_display = fields.Char(
        string="开户行",
        compute="_compute_payment_apply_formal_visible_fields",
        store=True,
        readonly=True,
    )
    payee_account_no_display = fields.Char(
        string="账号",
        compute="_compute_payment_apply_formal_visible_fields",
        store=True,
        readonly=True,
    )
    source_created_by = fields.Char(
        string="录入人",
        compute="_compute_payment_apply_formal_visible_fields",
        store=True,
        readonly=True,
    )
    source_created_at = fields.Datetime(
        string="录入时间",
        compute="_compute_payment_apply_formal_visible_fields",
        store=True,
        readonly=True,
    )
    cost_category_name = fields.Char(
        string="成本分类名称",
        compute="_compute_reconciliation_summary",
        store=True,
        readonly=True,
        index=True,
    )
    legacy_payment_account_name = fields.Char(
        string="历史付款户名",
        readonly=True,
        index=True,
    )
    legacy_payment_account_no = fields.Char(
        string="历史付款账号",
        readonly=True,
        index=True,
    )
    legacy_payee_account_name = fields.Char(
        string="历史收款户名",
        readonly=True,
        index=True,
    )
    legacy_payee_bank_name = fields.Char(
        string="历史收款开户行",
        readonly=True,
        index=True,
    )
    legacy_payee_account_no = fields.Char(
        string="历史收款账号",
        readonly=True,
        index=True,
    )
    actual_payee_unit = fields.Char(
        string="实际收款单位",
        index=True,
        tracking=True,
        help="付款申请自身确认的实际收款单位；历史迁移数据来自用户验收面。",
    )
    payer_unit = fields.Char(
        string="付款单位",
        index=True,
        tracking=True,
        help="付款申请自身确认的付款单位；历史迁移数据来自用户验收面。",
    )
    payment_account_name = fields.Char(
        string="收款户名",
        index=True,
        tracking=True,
        help="付款申请自身确认的收款户名；不覆盖往来单位主数据。",
    )
    payment_bank_name = fields.Char(
        string="收款开户行",
        index=True,
        tracking=True,
        help="付款申请自身确认的收款开户行；不覆盖往来单位主数据。",
    )
    payment_account_no = fields.Char(
        string="收款账号",
        index=True,
        tracking=True,
        help="付款申请自身确认的收款账号；不覆盖往来单位主数据。",
    )
    partner_account_name = fields.Char(
        string="往来单位默认户名",
        related="partner_id.sc_account_name",
        store=True,
        readonly=True,
        index=True,
    )
    partner_bank_name = fields.Char(
        string="往来单位默认开户行",
        related="partner_id.sc_bank_name",
        store=True,
        readonly=True,
        index=True,
    )
    partner_bank_account = fields.Char(
        string="往来单位默认账号",
        related="partner_id.sc_bank_account",
        store=True,
        readonly=True,
        index=True,
    )
    payee_account_completeness = fields.Selection(
        [("complete", "账户信息完整"), ("incomplete", "账户信息待补充")],
        string="收款账户完整度",
        compute="_compute_payee_account_completeness",
        store=True,
    )
    payee_account_source_display = fields.Char(
        string="收款账户来源",
        compute="_compute_payment_handling_summary",
    )
    payment_execution_ids = fields.One2many(
        "sc.payment.execution",
        "payment_request_id",
        string="付款登记",
        readonly=True,
    )
    has_active_payment_execution = fields.Boolean(
        string="已有有效付款登记",
        compute="_compute_payment_handling_summary",
        readonly=True,
    )
    payment_execution_status_display = fields.Char(
        string="付款执行状态",
        compute="_compute_payment_handling_summary",
    )
    legal_next_action_display = fields.Char(
        string="下一步办理",
        compute="_compute_legal_next_action_display",
    )
    payment_blocking_reason_display = fields.Char(
        string="办理阻断与修复",
        compute="_compute_payment_blocking_reason_display",
        store=True,
    )
    reject_reason = fields.Text(
        string="当前驳回原因",
        readonly=True,
        copy=False,
        tracking=True,
        help="仅保留当前待修正的驳回原因；历次原因以不可变审计记录为准。",
    )
    date_request = fields.Date(
        string="单据日期",
        default=fields.Date.context_today,
    )
    legacy_source_table = fields.Char(string="历史来源表", index=True, readonly=True)
    legacy_record_id = fields.Char(string="历史记录ID", index=True, readonly=True)
    legacy_document_state = fields.Char(string="历史单据状态", index=True, readonly=True)
    creator_name = fields.Char(string="历史录入人", index=True, readonly=True)
    created_time = fields.Datetime(string="历史录入时间", index=True, readonly=True)
    note = fields.Text(string="备注")
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "payment_request_attachment_rel",
        "request_id",
        "attachment_id",
        string="附件",
    )
    ledger_line_ids = fields.One2many(
        "payment.ledger",
        "payment_request_id",
        string="付款记录",
    )
    outflow_line_ids = fields.One2many(
        "payment.request.line",
        "request_id",
        string="付款申请明细",
    )
    receipt_invoice_line_ids = fields.One2many(
        "sc.receipt.invoice.line",
        "request_id",
        string="收款发票明细",
    )
    paid_amount_total = fields.Monetary(
        string="已付款合计",
        currency_field="currency_id",
        compute="_compute_payment_totals",
        store=False,
    )

    unpaid_amount = fields.Monetary(
        string="未付款金额",
        currency_field="currency_id",
        compute="_compute_payment_totals",
        store=False,
    )
    is_fully_paid = fields.Boolean(
        string="已结清",
        compute="_compute_payment_totals",
        store=False,
    )

    state = fields.Selection(
        ScStateMachine.selection(ScStateMachine.PAYMENT_REQUEST),
        string="状态",
        default="draft",
        tracking=True,
    )

    _business_fact_fields = frozenset(
        {
            "type",
            "business_category_id",
            "project_id",
            "contract_id",
            "settlement_id",
            "material_settlement_id",
            "partner_id",
            "currency_id",
            "amount",
            "date_request",
            "actual_payee_unit",
            "payer_unit",
            "payment_account_name",
            "payment_bank_name",
            "payment_account_no",
            "note",
            "attachment_ids",
            "outflow_line_ids",
            "receipt_invoice_line_ids",
        }
    )

    @api.depends("type", "receipt_type", "cost_category_name", "material_settlement_id", "business_category_id.code")
    def _compute_payment_flow_label(self):
        for record in self:
            if record.type == "receive":
                record.payment_flow_label = record.receipt_type or _("收款申请")
            elif record.material_settlement_id:
                record.payment_flow_label = _("材料结算付款申请")
            elif (
                record.business_category_id
                and record.business_category_id.target_model == "payment.request"
                and record.business_category_id.name
            ):
                record.payment_flow_label = record.business_category_id.name
            elif record.cost_category_name:
                record.payment_flow_label = _("付款申请：%s") % record.cost_category_name
            else:
                record.payment_flow_label = _("付款申请")

    @api.depends(
        "name",
        "type",
        "amount",
        "currency_id.symbol",
        "project_id.display_name",
        "partner_id.display_name",
        "actual_payee_unit",
        "payer_unit",
    )
    def _compute_display_name(self):
        for record in self:
            flow = _("收款申请") if record.type == "receive" else _("付款申请")
            project_name = (
                record.project_id.display_name
                or ""
            ).strip()
            partner_name = (
                record.actual_payee_unit
                or record.payer_unit
                or record.partner_id.display_name
                or ""
            ).strip()
            amount_text = record._display_amount_label()
            document_no = (
                record.name
                or ""
            ).strip()
            parts = [part for part in (flow, project_name, partner_name, amount_text, document_no) if part]
            record.display_name = " / ".join(parts) or flow

    def _display_amount_label(self):
        self.ensure_one()
        if self.amount:
            symbol = (self.currency_id.symbol or "").strip()
            return "%s%s" % (symbol, "{:,.2f}".format(self.amount))
        return ""

    @api.depends("outflow_line_ids.source_line_type")
    def _compute_reconciliation_summary(self):
        for record in self:
            line_types = [
                line_type
                for line_type in record.outflow_line_ids.mapped("source_line_type")
                if line_type
            ]
            unique_types = sorted(set(line_types))
            record.cost_category_name = " / ".join(unique_types[:5])

    @api.depends("amount")
    def _compute_amount_uppercase(self):
        for record in self:
            record.amount_uppercase = _amount_to_chinese_upper(record.amount)

    @api.depends(
        "legacy_document_state",
        "state",
        "project_id",
        "partner_id",
        "actual_payee_unit",
        "payer_unit",
        "amount",
        "cost_category_name",
        "note",
        "settlement_id",
        "line_settlement_summary",
        "legacy_relation_summary",
        "material_settlement_id",
        "contract_id",
        "payment_account_no",
        "legacy_payment_account_no",
        "partner_bank_account",
        "accepted_amount_uppercase",
        "amount_uppercase",
        "payment_account_name",
        "legacy_payee_account_name",
        "partner_account_name",
        "payment_bank_name",
        "legacy_payee_bank_name",
        "partner_bank_name",
        "legacy_payee_account_no",
        "creator_name",
        "created_time",
        "name",
    )
    def _compute_payment_apply_formal_visible_fields(self):
        state_labels = dict(self._fields["state"].selection)
        for record in self:
            state_text = ""
            has_related = any(
                (
                    record.settlement_id,
                    record.line_settlement_summary,
                    record.material_settlement_id,
                    record.contract_id,
                )
            )
            record.document_status_display = state_text or state_labels.get(record.state) or ""
            record.project_name_display = record.project_id.display_name or ""
            record.payee_unit_display = record.partner_id.display_name or ""
            record.actual_payee_unit_display = record.actual_payee_unit or record.partner_id.display_name or ""
            record.payer_unit_display = record.payer_unit or ""
            record.request_amount_display = record.amount or 0.0
            record.actual_paid_amount_display = record.paid_amount_total
            record.cost_type_display = record.cost_category_name or ""
            record.note_display = record.note or ""
            record.related_document_text = "是" if has_related else "否"
            record.payment_account_no_display = record.payment_account_no or record.partner_bank_account or ""
            record.amount_uppercase_display = record.accepted_amount_uppercase or record.amount_uppercase or ""
            record.payee_account_name_display = record.payment_account_name or record.partner_account_name or ""
            record.payee_bank_name_display = record.payment_bank_name or record.partner_bank_name or ""
            record.payee_account_no_display = record.payment_account_no or record.partner_bank_account or ""
            record.source_created_by = record.creator_name or ""
            record.source_created_at = record.created_time or False

    @api.model
    def _parse_legacy_amount(self, value):
        text = str(value or "").replace(",", "").replace("￥", "").replace("¥", "").strip()
        if not text:
            return None
        match = re.search(r"-?\d+(?:\.\d+)?", text)
        if not match:
            return None
        try:
            return float(match.group(0))
        except ValueError:
            return None

    @api.model
    def _strip_legacy_file_suffix(self, value):
        text = str(value or "").strip()
        if " | legacy-file-id://" in text:
            return text.split(" | legacy-file-id://", 1)[0].strip()
        return text

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
        if project_id and "operation_strategy" in fields_list and not res.get("operation_strategy"):
            project = self.env["project.project"].browse(project_id).exists()
            if project:
                res["operation_strategy"] = project.operation_strategy

        # A payment request opened from an authoritative contract or
        # settlement must present the carried business facts before the first
        # save.  Related fields are computed automatically for persisted
        # records, but Odoo's default_get does not materialize them for a new
        # virtual form.  Derive the preview from the same authoritative
        # records used by create/onchange; do not duplicate values in the
        # route or ask the client to infer financial facts.
        seed = dict(res)
        for field_name in (
            "type",
            "settlement_id",
            "material_settlement_id",
            "contract_id",
            "partner_id",
        ):
            seed.setdefault(field_name, self.env.context.get("default_%s" % field_name))
        basis_values = self._basis_payment_request_values(seed)
        for field_name, value in basis_values.items():
            if field_name in fields_list and not res.get(field_name):
                res[field_name] = value

        settlement_id = res.get("settlement_id") or seed.get("settlement_id")
        settlement = self.env["sc.settlement.order"].browse(settlement_id).exists() if settlement_id else False
        contract_id = res.get("contract_id") or basis_values.get("contract_id") or seed.get("contract_id")
        contract = self.env["construction.contract"].browse(contract_id).exists() if contract_id else False
        preview_values = {}
        if contract:
            preview_values.update(
                {
                    "contract_currency_id": contract.currency_id.id,
                    "contract_payment_terms": contract.contract_payment_method_text,
                    "contract_change_amount": contract.amount_change,
                    "contract_final_amount": contract.amount_final,
                    "contract_settlement_amount": contract.settlement_amount,
                    "contract_invoice_amount": contract.invoice_amount,
                    "contract_paid_amount": contract.paid_amount,
                    "contract_unpaid_amount": contract.unpaid_amount,
                }
            )
        if settlement:
            preview_values.update(
                {
                    "settlement_currency_id": settlement.currency_id.id,
                    "settlement_amount_total": settlement.amount_total,
                    "settlement_period_start": settlement.settlement_period_start,
                    "settlement_period_end": settlement.settlement_period_end,
                    "settlement_submitted_amount": settlement.submitted_amount,
                    "settlement_approved_amount": settlement.approved_amount,
                    "settlement_deduction_amount": settlement.deduction_amount,
                    "settlement_paid_amount": settlement.paid_amount,
                    "settlement_remaining_amount": settlement.remaining_amount,
                    "settlement_amount_payable": settlement.amount_payable,
                }
            )
        for field_name, value in preview_values.items():
            if field_name in fields_list:
                res[field_name] = value
        return res

    def _message_post_non_blocking(self, body):
        for rec in self:
            try:
                rec.message_post(body=body)
            except Exception as exc:
                _logger.warning(
                    "Skip payment.request chatter message for %s: %s",
                    rec.display_name,
                    exc,
                )

    @api.model
    def _partner_payment_defaults(self, partner, request_type="pay"):
        if not partner:
            return {}
        vals = {}
        if request_type == "pay":
            vals.update(
                {
                    "actual_payee_unit": partner.display_name or partner.name or "",
                    "payment_account_name": partner.sc_account_name or "",
                    "payment_bank_name": partner.sc_bank_name or "",
                    "payment_account_no": partner.sc_bank_account or "",
                }
            )
        elif request_type == "receive":
            vals["payer_unit"] = partner.display_name or partner.name or ""
        return {key: value for key, value in vals.items() if value}

    @api.depends(
        "type",
        "payment_account_name",
        "payment_bank_name",
        "payment_account_no",
        "partner_account_name",
        "partner_bank_name",
        "partner_bank_account",
    )
    def _compute_payee_account_completeness(self):
        for record in self:
            if record.type != "pay":
                record.payee_account_completeness = "complete"
                continue
            values = (
                record.payment_account_name or record.partner_account_name,
                record.payment_bank_name or record.partner_bank_name,
                record.payment_account_no or record.partner_bank_account,
            )
            record.payee_account_completeness = "complete" if all(values) else "incomplete"

    @api.depends(
        "type",
        "state",
        "payment_account_name",
        "payment_bank_name",
        "payment_account_no",
        "partner_account_name",
        "partner_bank_name",
        "partner_bank_account",
        "payee_account_completeness",
        "reject_reason",
    )
    def _compute_payment_blocking_reason_display(self):
        labels = (("户名", "payment_account_name", "partner_account_name"),
                  ("开户行", "payment_bank_name", "partner_bank_name"),
                  ("账号", "payment_account_no", "partner_bank_account"))
        for record in self:
            if record.state == "rejected":
                record.payment_blocking_reason_display = _(
                    "审批已驳回：%s。请修正业务事实后重新提交审批。"
                ) % (record.reject_reason or _("未提供原因"))
                continue
            if record.type != "pay" or record.payee_account_completeness == "complete":
                record.payment_blocking_reason_display = _("无业务阻断")
                continue
            missing = [
                label
                for label, snapshot_field, partner_field in labels
                if not (record[snapshot_field] or record[partner_field])
            ]
            record.payment_blocking_reason_display = _(
                "阻断付款执行：缺少%s。请维护往来单位默认结算账户，或在草稿申请中补全。"
            ) % "、".join(missing)

    @api.depends(
        "state",
        "type",
        "payment_account_name",
        "payment_bank_name",
        "payment_account_no",
        "partner_account_name",
        "partner_bank_name",
        "partner_bank_account",
        "payee_account_completeness",
        "payment_execution_ids.state",
        "payment_execution_ids.active",
    )
    def _compute_payment_handling_summary(self):
        execution_state_labels = dict(self.env["sc.payment.execution"]._fields["state"].selection)
        for record in self:
            if record.payment_account_name and record.payment_bank_name and record.payment_account_no:
                record.payee_account_source_display = _("本次申请账户快照")
            elif record.partner_account_name and record.partner_bank_name and record.partner_bank_account:
                record.payee_account_source_display = _("往来单位默认结算账户")
            else:
                record.payee_account_source_display = _("未配置完整收款账户")

            execution_history = record.payment_execution_ids.filtered(
                lambda execution: execution.active and execution.state != "cancel"
            ).sorted(
                key=lambda row: row.id,
                reverse=True,
            )
            open_executions = execution_history.filtered(
                lambda execution: execution.state in ("draft", "confirmed")
            )
            record.has_active_payment_execution = bool(open_executions)
            if execution_history:
                latest = execution_history[0]
                record.payment_execution_status_display = _("已生成：%s") % execution_state_labels.get(
                    latest.state,
                    latest.state,
                )
            else:
                cancelled = record.payment_execution_ids.filtered(
                    lambda execution: execution.active and execution.state == "cancel"
                )
                record.payment_execution_status_display = (
                    _("最近付款登记已取消或冲销，尚无有效付款登记")
                    if cancelled
                    else _("尚未生成")
                )

    @api.depends(
        "state",
        "type",
        "payee_account_completeness",
        "payment_execution_ids.state",
        "payment_execution_ids.active",
    )
    def _compute_legal_next_action_display(self):
        user = self.env.user
        can_submit = user.has_group("smart_construction_core.group_sc_cap_finance_user") or user.has_group(
            "smart_construction_core.group_sc_cap_business_initiator"
        )
        can_manage = user.has_group("smart_construction_core.group_sc_cap_finance_manager")
        can_approve = can_manage or user.has_group("smart_construction_core.group_sc_role_executive")
        for record in self:
            executions = record.payment_execution_ids.filtered(
                lambda execution: execution.active and execution.state in ("draft", "confirmed")
            ).sorted(
                key=lambda row: row.id,
                reverse=True,
            )
            if record.state == "draft":
                record.legal_next_action_display = _("提交审批") if can_submit else _("等待有提交能力的人员办理")
            elif record.state == "rejected":
                record.legal_next_action_display = _("重新提交审批") if can_submit else _("等待经办人修正后重新提交")
            elif record.state == "submit":
                record.legal_next_action_display = _("审批处理") if can_approve else _("等待审批")
            elif record.state == "approved" and executions:
                record.legal_next_action_display = _("查看付款登记")
            elif record.state == "approved" and record.type == "pay" and record.payee_account_completeness != "complete":
                record.legal_next_action_display = _("补全收款账户")
            elif record.state == "approved" and record.type == "pay":
                record.legal_next_action_display = _("生成付款登记") if can_manage else _("等待财务确认")
            elif record.state == "approved":
                record.legal_next_action_display = _("确认办结") if can_manage else _("等待财务确认")
            elif record.state == "done":
                record.legal_next_action_display = _("已办结")
            elif record.state == "cancel":
                record.legal_next_action_display = _("已取消")
            else:
                record.legal_next_action_display = _("等待办理")

    @api.model
    def _basis_payment_request_values(self, vals):
        values = {}
        request_type = vals.get("type") or self.env.context.get("default_type") or "pay"
        settlement = self.env["sc.settlement.order"].browse(vals.get("settlement_id")).exists() if vals.get("settlement_id") else False
        material_settlement = (
            self.env["sc.material.settlement"].browse(vals.get("material_settlement_id")).exists()
            if vals.get("material_settlement_id")
            else False
        )
        contract = self.env["construction.contract"].browse(vals.get("contract_id")).exists() if vals.get("contract_id") else False
        partner = self.env["res.partner"].browse(vals.get("partner_id")).exists() if vals.get("partner_id") else False

        if settlement:
            values.update(
                {
                    "project_id": settlement.project_id.id,
                    "contract_id": settlement.contract_id.id,
                    "partner_id": (settlement.settlement_unit_id or settlement.partner_id).id,
                    "amount": settlement.amount_payable or settlement.remaining_amount or settlement.settlement_amount or settlement.amount_total,
                    "currency_id": settlement.currency_id.id,
                }
            )
            partner = settlement.settlement_unit_id or settlement.partner_id or partner
        elif material_settlement:
            values.update(
                {
                    "project_id": material_settlement.project_id.id,
                    "partner_id": material_settlement.supplier_id.id,
                    "amount": material_settlement.payment_remaining_amount or material_settlement.amount_total,
                    "currency_id": material_settlement.currency_id.id,
                }
            )
            partner = material_settlement.supplier_id or partner
        elif contract:
            values.update(
                {
                    "project_id": contract.project_id.id,
                    "partner_id": contract.partner_id.id,
                    "currency_id": contract.currency_id.id,
                }
            )
            partner = contract.partner_id or partner

        if partner:
            values.update(self._partner_payment_defaults(partner, request_type=request_type))
        return {key: value for key, value in values.items() if value not in (False, None, "")}

    def _apply_payment_request_basis_values(self, values, *, only_empty=False):
        for field_name, value in values.items():
            if field_name not in self._fields:
                continue
            if only_empty and self[field_name]:
                continue
            setattr(self, field_name, value)

    @api.onchange("settlement_id", "material_settlement_id", "contract_id", "partner_id", "type")
    def _onchange_payment_request_basis(self):
        for record in self:
            vals = {
                "type": record.type,
                "settlement_id": record.settlement_id.id,
                "material_settlement_id": record.material_settlement_id.id,
                "contract_id": record.contract_id.id,
                "partner_id": record.partner_id.id,
            }
            record._apply_payment_request_basis_values(
                record._basis_payment_request_values(vals),
                only_empty=True,
            )

    def action_create_payment_execution(self):
        self.ensure_one()
        self._assert_payment_execution_ready(require_authorized_actor=True)
        action = self.env.ref("smart_construction_core.action_sc_payment_execution").read()[0]
        action["name"] = _("新建付款登记")
        action["view_mode"] = "form"
        action["views"] = [(False, "form")]
        # This is a continuation of the approved request, not a detour to the
        # payment execution ledger.  Make the create-form destination explicit
        # so every client consumes the same authoritative handling step.
        action["target"] = "new"
        continuation_context = dict(self.env.context or {})
        for key in (
            "current_business_category_code",
            "current_business_category_label",
            "default_business_category_code",
            "default_business_category_label",
            "default_business_category_id",
        ):
            continuation_context.pop(key, None)
        execution_category = self.env.ref(
            "smart_construction_core.business_category_finance_payment_execution_partner"
        )
        action["context"] = {
            **continuation_context,
            "current_business_category_code": execution_category.code,
            "current_business_category_label": execution_category.name,
            "default_business_category_code": execution_category.code,
            "default_business_category_label": execution_category.name,
            "default_business_category_id": execution_category.id,
            "default_payment_request_id": self.id,
            "default_payment_request_id_label": self.display_name,
            "default_source_kind": "actual_outflow",
            "default_payment_family": "往来单位付款",
            "default_project_id": self.project_id.id,
            "default_project_id_label": self.project_id.display_name,
            "default_partner_id": self.partner_id.id,
            "default_partner_id_label": self.partner_id.display_name,
            "default_contract_id": self.contract_id.id,
            "default_contract_id_label": self.contract_id.display_name,
            "default_document_no": self.name,
            "default_planned_amount": self.amount or 0.0,
            "default_paid_amount": self.unpaid_amount or self.amount or 0.0,
            "default_currency_id": self.currency_id.id,
            "default_receipt_account_name": self.payment_account_name or self.partner_account_name,
            "default_receipt_bank_name": self.payment_bank_name or self.partner_bank_name,
            "default_receipt_account_no": self.payment_account_no or self.partner_bank_account,
            "default_payment_account_name": self.payer_unit,
            "default_payment_account_no": self.legacy_payment_account_no,
            "default_note": self.note,
        }
        return action

    def action_view_payment_execution(self):
        """Open the existing execution continuation for this request."""
        self.ensure_one()
        if not self.env.user.has_group(
            "smart_construction_core.group_sc_cap_finance_manager"
        ):
            raise UserError(_("你没有查看付款登记续接页的财务确认权限。"))
        executions = self.payment_execution_ids.filtered(
            lambda execution: execution.active and execution.state != "cancel"
        ).sorted(key=lambda execution: execution.id, reverse=True)
        if not executions:
            raise UserError(_("该付款申请尚未生成有效的付款登记。"))
        action = self.env.ref("smart_construction_core.action_sc_payment_execution").read()[0]
        action.update(
            {
                "name": _("查看付款登记"),
                "view_mode": "form",
                "views": [(False, "form")],
                "res_id": executions[0].id,
                "target": "current",
            }
        )
        return action

    def _assert_payment_execution_ready(self, *, require_authorized_actor=False):
        """Fail closed before a payment request can anchor an execution record."""
        for record in self:
            if record.type != "pay":
                raise UserError(_("只有付款申请可以生成付款登记。"))
            if record.state != "approved":
                raise UserError(_("付款申请必须处于已批准状态才能生成付款登记。"))
            if record.payee_account_completeness != "complete":
                raise UserError(_("收款户名、开户行和账号必须完整后才能生成付款登记。"))
            if require_authorized_actor and not self.env.user.has_group(
                "smart_construction_core.group_sc_cap_finance_manager"
            ):
                raise UserError(_("你没有生成付款登记的财务确认权限。"))
        return True

    def unlink(self):
        locked = self.filtered(lambda rec: rec.state not in ("draft", "cancel"))
        if locked:
            raise UserError("仅草稿或已取消的付款申请允许删除。")
        ledger_count = self.env["payment.ledger"].sudo().search_count(
            [("payment_request_id", "in", self.ids)]
        )
        if ledger_count:
            raise UserError(_("存在有效或已冲销付款台账的申请不得删除，必须保留财务追溯链。"))
        self._sc_raise_delete_blockers(action_label="删除付款申请")
        return super().unlink()

    def _get_active_funding_baseline(self, project, evaluation_cache=None):
        cache = evaluation_cache if isinstance(evaluation_cache, dict) else None
        cache_key = ("active_funding_baseline", int(project.id or 0))
        baseline = cache.get(cache_key) if cache is not None else None
        if baseline is None:
            baseline = self.env["project.funding.baseline"].sudo().search(
                [
                    ("project_id", "=", project.id),
                    ("state", "=", "active"),
                ],
                limit=2,
            )
            if cache is not None:
                cache[cache_key] = baseline
        if len(baseline) != 1:
            raise_guard(
                "P0_PAYMENT_FUNDING_BASELINE_INVALID",
                f"项目[{project.display_name}]",
                "提交付款申请",
                reasons=["项目必须且只能有一个生效中的资金基准"],
                hints=["请先修正项目资金基准后再提交付款申请"],
            )
        return baseline

    def _get_reserved_amount(self, project, exclude_ids=None, evaluation_cache=None):
        domain = [
            ("project_id", "=", project.id),
            ("type", "=", "pay"),
            ("state", "in", ["submit", "approve", "approved"]),
        ]
        cache = evaluation_cache if isinstance(evaluation_cache, dict) else None
        excluded = {int(item) for item in (exclude_ids or []) if int(item or 0) > 0}
        current_ids = {int(item) for item in self.ids if int(item or 0) > 0}
        can_subtract_current = bool(cache is not None and len(self) == 1 and excluded == current_ids)
        if can_subtract_current:
            cache_key = ("reserved_amount", int(project.id or 0))
            if cache_key not in cache:
                data = self.sudo().read_group(domain, ["amount:sum"], [])
                cache[cache_key] = data[0].get("amount_sum", data[0].get("amount", 0.0)) if data else 0.0
            reserved = cache[cache_key]
            current_is_reserved = (
                self.project_id.id == project.id
                and self.type == "pay"
                and self.state in ("submit", "approve", "approved")
            )
            excluded_amount = (self.amount or 0.0) if current_is_reserved else 0.0
            return max(0.0, (reserved or 0.0) - excluded_amount)
        if exclude_ids:
            domain.append(("id", "not in", exclude_ids))
        data = self.sudo().read_group(domain, ["amount:sum"], [])
        return data[0].get("amount_sum", data[0].get("amount", 0.0)) if data else 0.0

    def _check_project_funding_gate(self, project, amount, exclude_ids=None, evaluation_cache=None):
        if not project or not project.is_funding_ready():
            raise_guard(
                "P0_PAYMENT_FUNDING_NOT_READY",
                f"项目[{project.display_name if project else '-'}]",
                "提交付款申请",
                reasons=["项目未满足资金承载条件"],
                hints=["请先完成项目资金承载设置后再提交付款申请"],
            )
        baseline = self._get_active_funding_baseline(project, evaluation_cache=evaluation_cache)
        cap = baseline.total_amount or 0.0
        if cap <= 0.0:
            raise_guard(
                "P0_PAYMENT_FUNDING_BASELINE_INVALID",
                f"项目[{project.display_name}]",
                "提交付款申请",
                reasons=["项目资金基准上限必须大于 0"],
                hints=["请先修正项目资金基准后再提交付款申请"],
            )
        if (amount or 0.0) <= 0.0:
            raise UserError("申请金额必须大于 0。")
        used = self._get_reserved_amount(
            project,
            exclude_ids=exclude_ids,
            evaluation_cache=evaluation_cache,
        )
        rounding = project.company_currency_id.rounding if project.company_currency_id else 0.01
        if float_compare((used or 0.0) + (amount or 0.0), cap, precision_rounding=rounding) == 1:
            raise_guard(
                "P0_PAYMENT_FUNDING_CAP_EXCEEDED",
                f"项目[{project.display_name}]",
                "提交付款申请",
                reasons=[
                    _("付款申请金额累计超出资金基准上限"),
                    _("已提交/审批金额：%(used)s") % {"used": used},
                    _("本次申请：%(amount)s") % {"amount": amount},
                    _("资金上限：%(cap)s") % {"cap": cap},
                ],
                hints=["请调整付款金额或项目资金基准后再提交付款申请"],
            )

    def _enforce_funding_gate(self, vals=None):
        if self.env.context.get("payment_soft_gate") and not (
            self._payment_force_block_enabled("P0_PAYMENT_FUNDING_NOT_READY")
            or self._payment_force_block_enabled("P0_PAYMENT_FUNDING_BASELINE_INVALID")
            or self._payment_force_block_enabled("P0_PAYMENT_FUNDING_CAP_EXCEEDED")
        ):
            return
        vals = vals or {}
        for rec in self:
            req_type = vals.get("type", rec.type)
            project_id = vals.get("project_id", rec.project_id.id)
            project = self.env["project.project"].browse(project_id) if project_id else rec.project_id
            amount = vals.get("amount", rec.amount)
            state = vals.get("state", rec.state)
            if req_type == "pay" and state in ("submit", "approve", "approved"):
                self._check_project_funding_gate(project, amount, exclude_ids=rec.ids)

    def _check_project_lifecycle(self, project, target_state):
        if not project:
            return
        if target_state in ("submit", "approve", "approved", "done"):
            if project.lifecycle_state in ("warranty", "closed"):
                raise_guard(
                    "P0_PROJECT_TERMINAL_BLOCKED",
                    f"项目[{project.display_name}]",
                    "提交/审批付款申请",
                    reasons=[f"当前项目状态为 {project.lifecycle_state}"],
                    hints=["请先调整项目状态或完成保修/关闭流程"],
                )

    def _check_settlement_state(self, settlement):
        if not settlement:
            return
        if settlement.state not in ("approve", "done"):
            raise_guard(
                "P0_PAYMENT_SETTLEMENT_NOT_READY",
                f"结算单[{settlement.display_name}]",
                "提交/审批付款申请",
                reasons=[f"结算单状态为 {settlement.state}"],
                hints=["请先完成结算单审批后再提交付款申请"],
            )

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env["ir.sequence"]
        for vals in vals_list:
            project_id = self._context_project_id()
            if project_id:
                vals.setdefault("project_id", project_id)
            for field_name, value in self._basis_payment_request_values(vals).items():
                vals.setdefault(field_name, value)
            vals.setdefault("business_category_id", self._resolve_business_category_id(vals))
            if not vals.get("name") or vals.get("name") == "New":
                vals["name"] = seq.next_by_code("payment.request") or _("Payment Request")
        records = super().create(vals_list)
        audited_history_import = bool(
            self.env.context.get("sc_tenant_payload_import")
        )
        if audited_history_import:
            self.env["sc.tenant.payload.adapter"].assert_import_operator()
        if not audited_history_import:
            records.filtered(
                lambda r: r.type == "pay" and r.state in ("submit", "approve", "approved")
            )._enforce_funding_gate()
        return records

    @api.model
    def _resolve_business_category_code(self, vals):
        code = self.env.context.get("default_business_category_code") or self.env.context.get(
            "current_business_category_code"
        )
        if code:
            return code
        request_type = vals.get("type") or self.env.context.get("default_type") or "pay"
        if request_type == "receive":
            return "finance.payment.apply.receive"
        return "finance.payment.apply.pay"

    @api.model
    def _resolve_business_category_id(self, vals):
        code = self._resolve_business_category_code(vals)
        category = self.env["sc.business.category"].sudo().search(
            [("code", "=", code), ("target_model", "=", self._name)],
            limit=1,
        )
        return category.id if category else False

    def write(self, vals):
        changed_business_facts = self._business_fact_fields.intersection(vals)
        locked = self.filtered(lambda rec: rec.state not in ("draft", "rejected", "cancel"))
        if changed_business_facts and locked and not self.env.context.get("allow_payment_business_fact_write"):
            raise UserError(
                _("付款/收款申请进入审批后，项目、依据、对象、金额和账户等业务事实不可直接修改；请取消后重新发起。")
            )
        if "state" in vals and not self.env.context.get("allow_transition"):
            sample = self[:1]
            raise_guard(
                "PAYMENT_GUARD_DIRECT_STATE_WRITE",
                f"付款申请[{sample.display_name if sample else ''}]",
                "状态变更",
                reasons=["state change must use transition methods"],
            )
        if vals.get("state") == "done":
            self._check_can_done()
        tier_validation_callback = self.env.context.get("tier_validation_callback")
        if vals.get("state") in ("approved", "done") and not tier_validation_callback:
            for rec in self:
                if rec.validation_status != "validated":
                    raise_guard(
                        "P0_PAYMENT_STATE_BYPASS_BLOCKED",
                        f"付款申请[{rec.display_name}]",
                        "状态变更",
                        reasons=["未完成审批流程"],
                        hints=["请先完成审批后再进入已批准/已完成状态"],
                    )
        res = super().write(vals)
        if any(key in vals for key in ("state", "type", "project_id", "amount")):
            self._enforce_funding_gate(vals)
        return res

    def _get_attachment_count(self):
        self.ensure_one()
        if "message_attachment_count" in self._fields:
            return self.message_attachment_count or 0
        if "attachment_ids" in self._fields:
            return len(self.attachment_ids)
        return self.env["ir.attachment"].search_count(
            [("res_model", "=", self._name), ("res_id", "=", self.id)]
        )

    def _snapshot_audit_payload(self):
        self.ensure_one()
        business_category = self.business_category_id.sudo()
        return {
            "state": self.state,
            "amount": self.amount,
            "partner_id": self.partner_id.id if self.partner_id else False,
            "business_category_id": business_category.id if business_category else False,
            "business_category_code": business_category.code if business_category else False,
            "attachment_count": self._get_attachment_count(),
            "validation_status": self.validation_status,
        }

    def _audit_transition(self, event_code, before, after, reason=None, require_reason=False, action_name=None):
        self.ensure_one()
        return self.env["sc.audit.log"].write_event(
            event_code=event_code,
            model=self._name,
            res_id=self.id,
            action=action_name or event_code,
            before=before,
            after=after,
            reason=reason,
            require_reason=require_reason,
            company_id=self.company_id,
            project_id=self.project_id,
        )

    def init(self):
        self.env.cr.execute(
            """
            UPDATE payment_request request
               SET business_category_id = category.id
              FROM sc_business_category category
             WHERE request.business_category_id IS NULL
               AND category.target_model = 'payment.request'
               AND category.code = CASE
                   WHEN request.type = 'receive'
                       THEN 'finance.payment.apply.receive'
                   ELSE 'finance.payment.apply.pay'
               END
            """
        )

    def _has_submit_access(self):
        return (
            self.env.user.has_group("smart_construction_core.group_sc_cap_business_initiator")
            or self.env.user.has_group("smart_construction_core.group_sc_cap_finance_user")
        )

    def _has_finance_approve_access(self):
        return any(
            self.env.user.has_group(xmlid)
            for xmlid in (
                "smart_construction_core.group_sc_cap_finance_manager",
                "smart_core.group_smart_core_finance_approver",
                "smart_construction_core.group_sc_role_executive",
            )
        )

    def _assert_finance_approve_access(self):
        if not self._has_finance_approve_access():
            raise ValidationError(_("你没有审批付款/收款申请的权限。"))

    @api.depends("settlement_id", "settlement_remaining_amount", "amount")
    def _compute_settlement_amount_insufficient(self):
        for rec in self:
            if not rec.settlement_id:
                rec.settlement_amount_insufficient = False
                continue
            remaining = rec.settlement_remaining_amount or 0.0
            request_amount = rec.amount or 0.0
            rec.settlement_amount_insufficient = remaining <= 0 or request_amount > remaining

    @api.depends("settlement_id", "settlement_id.compliance_state")
    def _compute_settlement_match_flags(self):
        for rec in self:
            state = rec.settlement_id.compliance_state if rec.settlement_id else False
            rec.settlement_match_blocked = state == "block"
            rec.settlement_match_warn = state == "warn"

    @api.depends("outflow_line_ids.settlement_id", "outflow_line_ids.settlement_id.name")
    def _compute_line_settlement_summary(self):
        for rec in self:
            settlements = rec.outflow_line_ids.mapped("settlement_id").exists()
            rec.line_settlement_count = len(settlements)
            names = settlements.mapped("name")
            if len(names) > 3:
                rec.line_settlement_summary = "%s 等%s张" % ("、".join(names[:3]), len(names))
            else:
                rec.line_settlement_summary = "、".join(names)

    @api.depends(
        "outflow_line_ids.import_batch",
        "outflow_line_ids.source_line_type",
        "outflow_line_ids.source_document_no",
    )
    def _compute_legacy_relation_summary(self):
        for rec in self:
            lines = rec.outflow_line_ids.filtered(lambda line: line.import_batch and (line.source_document_no or line.source_line_type))
            rec.legacy_relation_count = len(lines)
            labels = []
            seen = set()
            for line in lines:
                line_type = (line.source_line_type or "历史关联").strip() or "历史关联"
                document_no = (line.source_document_no or "").strip()
                label = "%s:%s" % (line_type, document_no) if document_no else line_type
                if label in seen:
                    continue
                seen.add(label)
                labels.append(label)
            if len(labels) > 3:
                rec.legacy_relation_summary = "%s 等%s项" % ("、".join(labels[:3]), len(labels))
            else:
                rec.legacy_relation_summary = "、".join(labels)

    @api.depends(
        "settlement_id",
        "line_settlement_count",
        "material_settlement_id",
        "contract_id",
        "legacy_relation_count",
    )
    def _compute_payment_basis_type(self):
        for rec in self:
            if rec.settlement_id:
                rec.payment_basis_type = "standard_settlement"
            elif rec.line_settlement_count:
                rec.payment_basis_type = "line_settlement"
            elif rec.material_settlement_id:
                rec.payment_basis_type = "material_settlement"
            elif rec.contract_id:
                rec.payment_basis_type = "contract"
            elif rec.legacy_relation_count:
                rec.payment_basis_type = "legacy_relation"
            else:
                rec.payment_basis_type = "none"

    def _get_bool_param(self, key, default=True):
        val = self.env["ir.config_parameter"].sudo().get_param(key)
        if val is None:
            return default
        return str(val).strip().lower() in ("1", "true", "yes", "y", "on")

    def _payment_force_block_enabled(self, reason_code):
        code = str(reason_code or "").strip().upper()
        if not code:
            return False
        if self._get_bool_param("sc.payment.force_block_all", False):
            return True
        return self._get_bool_param("sc.payment.force_block.%s" % code.lower(), False)

    def _payment_advisory(self, reason_code, message, suggested_action="", reasons=None, hints=None):
        code = str(reason_code or "BUSINESS_RULE_FAILED").strip().upper()
        return {
            "reason_code": code,
            "message": str(message or code),
            "suggested_action": str(suggested_action or ""),
            "reasons": [str(item) for item in (reasons or []) if str(item or "").strip()],
            "hints": [str(item) for item in (hints or []) if str(item or "").strip()],
            "force_block_enabled": self._payment_force_block_enabled(code),
        }

    def _payment_advisory_from_exception(self, exc, fallback_code="BUSINESS_RULE_FAILED"):
        if isinstance(exc, AccessError):
            return self._payment_advisory(
                "RELATED_INFORMATION_RESTRICTED",
                _("部分关联信息当前无权读取，不影响本次操作结果。"),
                hints=[_("如需核对完整关联信息，请联系相应业务负责人。")],
            )
        text = str(exc or "").strip()
        match = re.search(r"\[SC_GUARD:([A-Z0-9_]+)\]", text)
        code = str(match.group(1) if match else fallback_code).strip().upper()
        suggested = {
            "PAYMENT_ATTACHMENTS_REQUIRED": "upload_attachment",
            "P0_PAYMENT_SETTLEMENT_NOT_READY": "complete_settlement_approval",
            "P0_PAYMENT_FUNDING_NOT_READY": "setup_project_funding",
            "P0_PAYMENT_FUNDING_BASELINE_INVALID": "fix_project_funding_baseline",
            "P0_PAYMENT_FUNDING_CAP_EXCEEDED": "adjust_payment_amount_or_funding",
            "P0_PAYMENT_NOT_FULLY_PAID": "complete_payment_execution",
        }.get(code, "")
        return self._payment_advisory(code, text or code, suggested_action=suggested)

    def _collect_payment_advisories(self, action_name, evaluation_cache=None):
        self.ensure_one()
        action_key = str(action_name or "").strip().lower()
        advisories = []
        if action_key in ("submit", "approve") and self.type == "pay" and self.payee_account_completeness == "incomplete":
            advisories.append(
                self._payment_advisory(
                    "PAYEE_ACCOUNT_INCOMPLETE",
                    _("收款户名、开户行或账号尚未补充完整，付款执行前必须补齐。"),
                    suggested_action="complete_payee_account",
                    reasons=["payee account snapshot is incomplete"],
                    hints=[_("请从往来单位默认账户带入，或核对付款依据后填写本次收款账户快照。")],
                )
            )
        if (
            action_key in ("submit", "approve")
            and self.type == "pay"
            and self.actual_payee_unit
            and self.partner_id
            and self.actual_payee_unit.strip() not in {self.partner_id.name or "", self.partner_id.display_name or ""}
            and self._get_attachment_count() <= 0
        ):
            advisories.append(
                self._payment_advisory(
                    "THIRD_PARTY_PAYEE_EVIDENCE_REQUIRED",
                    _("实际收款单位与合同往来单位不同，需补充委托付款等授权依据。"),
                    suggested_action="upload_third_party_authorization",
                    reasons=["actual payee differs from contractual counterparty"],
                    hints=[_("请上传委托付款书或其他可追溯的第三方收款授权。")],
                )
            )
        if action_key == "submit" and self._get_attachment_count() <= 0:
            advisories.append(
                self._payment_advisory(
                    "PAYMENT_ATTACHMENTS_REQUIRED",
                    _("付款申请未上传附件，建议补充附件后再提交。"),
                    suggested_action="upload_attachment",
                    reasons=["attachments are missing"],
                    hints=["请补充合同、结算或付款依据附件"],
                )
            )
        if action_key == "done" and not self.is_fully_paid:
            advisories.append(
                self._payment_advisory(
                    "P0_PAYMENT_NOT_FULLY_PAID",
                    _("付款申请尚未登记足额付款，完成时将自动生成付款记录。"),
                    suggested_action="complete_payment_execution",
                    reasons=["payment ledger is not fully paid"],
                    hints=["请确认审批风险后完成付款办理"],
                )
            )
        for check in (
            lambda: self._check_project_lifecycle(self.project_id, action_key),
            lambda: self._check_settlement_state(self.settlement_id),
            lambda: self._check_project_funding_gate(
                self.project_id,
                self.amount,
                exclude_ids=self.ids,
                evaluation_cache=evaluation_cache,
            ),
            self._check_settlement_remaining_amount,
            self._check_material_settlement_remaining_amount,
            self._check_not_overpay_settlement,
            self._check_settlement_consistency,
            lambda: self._check_settlement_compliance_or_raise(strict=False),
        ):
            try:
                check()
            except Exception as exc:
                advisories.append(self._payment_advisory_from_exception(exc))
        return advisories

    def _handle_payment_advisories(self, action_name, advisories):
        blocking = [item for item in (advisories or []) if item.get("force_block_enabled")]
        if blocking:
            first = blocking[0]
            raise_guard(
                first.get("reason_code") or "BUSINESS_RULE_FAILED",
                f"付款申请[{self.display_name}]",
                str(action_name or "办理付款申请"),
                reasons=first.get("reasons") or [first.get("message") or ""],
                hints=first.get("hints") or [],
            )
        if advisories:
            lines = [
                "- %s" % str(item.get("message") or item.get("reason_code") or "").strip()
                for item in advisories
                if str(item.get("message") or item.get("reason_code") or "").strip()
            ]
            if lines:
                self._message_post_non_blocking(_("付款申请风险提示：\n%s") % "\n".join(lines))
        return advisories

    def _compute_move_type(self):
        for rec in self:
            rec.move_type = rec.type

    @api.depends(
        "ledger_line_ids.amount",
        "ledger_line_ids.currency_id",
        "ledger_line_ids.state",
        "amount",
        "currency_id",
    )
    def _compute_payment_totals(self):
        paid_map = {}
        if self.ids:
            data = self.env["payment.ledger"].read_group(
                [("payment_request_id", "in", self.ids), ("state", "=", "posted")],
                ["amount:sum"],
                ["payment_request_id"],
            )
            for rec in data:
                req_id = rec["payment_request_id"][0]
                paid_map[req_id] = rec.get("amount_sum", rec.get("amount", 0.0)) or 0.0
        for req in self:
            paid_total = paid_map.get(req.id, 0.0)
            req.paid_amount_total = paid_total
            unpaid = (req.amount or 0.0) - paid_total
            req.unpaid_amount = unpaid
            rounding = req.currency_id.rounding if req.currency_id else 0.01
            req.is_fully_paid = float_compare(unpaid, 0.0, precision_rounding=rounding) <= 0

    def _check_can_done(self):
        for rec in self:
            if rec.state != "approved":
                raise ValidationError(_("仅已批准的付款申请可以完成。"))
            rounding = rec.currency_id.rounding if rec.currency_id else 0.01
            ledger_model = "sc.treasury.ledger" if rec.type == "receive" else "payment.ledger"
            domain = [("payment_request_id", "=", rec.id)]
            if ledger_model == "payment.ledger":
                domain.append(("state", "=", "posted"))
            data = self.env[ledger_model].read_group(domain, ["amount:sum"], [])
            paid_total = data[0].get("amount_sum", data[0].get("amount", 0.0)) if data else 0.0
            unpaid = (rec.amount or 0.0) - paid_total
            if float_compare(unpaid, 0.0, precision_rounding=rounding) == 1:
                raise ValidationError(_("付款/收款未结清，无法完成。"))

    def _settlement_domain_for_payment_request(self):
        self.ensure_one()
        settlement_type = "in" if self.type == "receive" else "out"
        domain = [
            ("state", "=", "approve"),
            ("settlement_type", "=", settlement_type),
        ]
        if self.project_id:
            domain.append(("project_id", "=", self.project_id.id))
        if self.contract_id:
            domain.append(("contract_id", "=", self.contract_id.id))
        return domain

    def _material_settlement_domain_for_payment_request(self):
        self.ensure_one()
        domain = [("state", "=", "confirmed")]
        if self.project_id:
            domain.append(("project_id", "=", self.project_id.id))
        if self.partner_id:
            domain.append(("supplier_id", "=", self.partner_id.id))
        return domain

    def _settlement_matches_payment_context(self, settlement):
        self.ensure_one()
        if not settlement:
            return True
        settlement_partner = settlement.settlement_unit_id or settlement.partner_id
        expected_type = "in" if self.type == "receive" else "out"
        if settlement.state != "approve" or settlement.settlement_type != expected_type:
            return False
        if self.project_id and settlement.project_id and settlement.project_id != self.project_id:
            return False
        if self.contract_id and settlement.contract_id and settlement.contract_id != self.contract_id:
            return False
        if self.partner_id and settlement_partner and settlement_partner != self.partner_id:
            return False
        return True

    def _material_settlement_matches_payment_context(self, settlement):
        self.ensure_one()
        if not settlement:
            return True
        if settlement.state != "confirmed":
            return False
        if self.project_id and settlement.project_id and settlement.project_id != self.project_id:
            return False
        if self.partner_id and settlement.supplier_id and settlement.supplier_id != self.partner_id:
            return False
        return True

    @api.onchange("type", "project_id", "contract_id", "partner_id")
    def _onchange_type_set_contract_domain(self):
        domain = {}
        expected_contract_type = "in" if self.type == "pay" else "out"
        contract_domain = [("type", "=", expected_contract_type)]
        if self.project_id:
            contract_domain.append(("project_id", "=", self.project_id.id))
        domain["contract_id"] = contract_domain
        for record in self:
            if record.contract_id and record.contract_id.type != expected_contract_type:
                record.contract_id = False
            if record.settlement_id and not record._settlement_matches_payment_context(record.settlement_id):
                record.settlement_id = False
            if (
                record.material_settlement_id
                and not record._material_settlement_matches_payment_context(record.material_settlement_id)
            ):
                record.material_settlement_id = False
            domain["settlement_id"] = record._settlement_domain_for_payment_request()
            domain["material_settlement_id"] = record._material_settlement_domain_for_payment_request()
        return {"domain": domain}

    def _check_settlement_compliance_or_raise(self, strict=True):
        self.ensure_one()
        if not self.settlement_id:
            return
        block_on_block = self._get_bool_param("sc.payment.block_on_settlement_block", True)
        block_on_warn = self._get_bool_param("sc.payment.block_on_settlement_warn", False)
        state = self.settlement_id.compliance_state
        msg = self.settlement_id.compliance_message or ""
        if state == "block" and block_on_block:
            raise ValidationError(_("结算单来源匹配未通过，禁止继续：\n%s") % msg)
        if state == "warn" and strict and block_on_warn:
            raise ValidationError(_("结算单来源匹配存在缺失/提示，按策略禁止继续：\n%s") % msg)

    def _linked_settlement_orders(self):
        """Return settlement orders linked either on the request or legacy detail lines."""
        self.ensure_one()
        settlements = self.settlement_id
        if self.outflow_line_ids:
            settlements |= self.outflow_line_ids.mapped("settlement_id")
        return settlements.exists()

    def _has_payment_basis(self):
        self.ensure_one()
        return bool(
            self.contract_id
            or self.settlement_id
            or self.material_settlement_id
            or self.outflow_line_ids.filtered("settlement_id")
        )

    def _has_legacy_relation_basis(self):
        return False

    @api.constrains("settlement_id", "type", "project_id", "partner_id", "contract_id", "currency_id")
    def _check_settlement_consistency(self):
        for rec in self:
            settle = rec.settlement_id
            if not settle:
                continue
            if settle.settlement_type == "out" and rec.type != "pay":
                raise ValidationError(_("结算单类型必须与付款申请类型一致。"))
            if settle.settlement_type == "in" and rec.type != "receive":
                raise ValidationError(_("结算单类型必须与付款申请类型一致。"))
            if settle.project_id and rec.project_id and settle.project_id != rec.project_id:
                raise ValidationError(_("结算单项目必须与付款申请项目一致。"))
            settlement_partner = settle.settlement_unit_id or settle.partner_id
            if settlement_partner and rec.partner_id and settlement_partner != rec.partner_id:
                raise ValidationError(_("结算单往来单位必须与付款申请一致。"))
            if settle.contract_id and rec.contract_id and settle.contract_id != rec.contract_id:
                raise ValidationError(_("结算单合同必须与付款申请一致。"))
            opm.ensure_payment_settlement_currency_consistency(rec, settle)
            # 已进入流程的记录在字段更改时仍要守住额度
            if rec.state in ("submit", "approve", "approved", "done"):
                rec._check_settlement_remaining_amount()

    @api.constrains("material_settlement_id", "type", "project_id", "partner_id", "amount", "state")
    def _check_material_settlement_consistency(self):
        for rec in self:
            settlement = rec.material_settlement_id
            if not settlement:
                continue
            if rec.type != "pay":
                raise ValidationError(_("材料结算只能生成付款申请。"))
            if settlement.project_id and rec.project_id and settlement.project_id != rec.project_id:
                raise ValidationError(_("材料结算项目必须与付款申请项目一致。"))
            if settlement.supplier_id and rec.partner_id and settlement.supplier_id != rec.partner_id:
                raise ValidationError(_("材料结算供应商必须与付款申请往来单位一致。"))
            if rec.state in ("submit", "approve", "approved", "done"):
                rec._check_material_settlement_remaining_amount()

    @api.constrains("contract_id", "type")
    def _check_contract_direction(self):
        for rec in self:
            if not rec.contract_id:
                continue
            expected = "in" if rec.type == "pay" else "out"
            if rec.contract_id.type != expected:
                raise ValidationError(_("合同类型必须与申请类型一致。"))

    @api.constrains("contract_id", "project_id", "partner_id", "currency_id", "type")
    def _check_contract_business_identity(self):
        for rec in self:
            contract = rec.contract_id
            if not contract:
                continue
            if contract.project_id and rec.project_id and contract.project_id != rec.project_id:
                raise ValidationError(_("合同项目必须与付款/收款申请项目一致。"))
            settlement_partner = (
                rec.settlement_id.settlement_unit_id or rec.settlement_id.partner_id
                if rec.settlement_id
                else self.env["res.partner"]
            )
            if (
                contract.partner_id
                and rec.partner_id
                and contract.partner_id != rec.partner_id
                and settlement_partner != rec.partner_id
            ):
                raise ValidationError(_("合同往来单位必须与付款/收款申请往来单位一致；结算单明确指定结算单位的除外。"))
            if contract.currency_id and rec.currency_id and contract.currency_id != rec.currency_id:
                raise ValidationError(_("合同币种必须与付款/收款申请币种一致。"))

    @api.constrains(
        "contract_id",
        "settlement_id",
        "material_settlement_id",
        "project_id",
        "outflow_line_ids",
    )
    def _check_payment_execution_basis_contract(self):
        execution_model = self.env["sc.payment.execution"]
        for request in self.filtered(lambda rec: rec.type == "pay"):
            execution_model._payment_basis_contracts(request)
            executions = execution_model.search(
                [("payment_request_id", "=", request.id)]
            )
            for execution in executions:
                execution._normalize_payment_relation_values({}, current=execution)

    def _check_settlement_remaining_amount(self):
        """防超付额度硬校验：提交/审批前必须满足结算额度（排除本申请）。"""
        for rec in self:
            settle = rec.settlement_id
            if rec.type != "pay" or not settle:
                continue
            metrics = opm.compute_payment_payable_excluding_self(rec)
            payable = metrics["payable"]
            precision = metrics["precision"]
            amount = rec.amount or 0.0
            if float_compare(payable, 0.0, precision_rounding=precision) <= 0:
                raise_guard(
                    "P0_PAYMENT_OVER_BALANCE",
                    f"付款申请[{rec.display_name}]",
                    "提交/审批付款申请",
                    reasons=[f"结算单剩余额度不足（剩余额度：{payable}）"],
                    hints=["请先调整结算金额或降低付款金额"],
                )
            if float_compare(amount, payable, precision_rounding=precision) == 1:
                raise_guard(
                    "P0_PAYMENT_OVER_BALANCE",
                    f"付款申请[{rec.display_name}]",
                    "提交/审批付款申请",
                    reasons=[f"申请金额 {amount} 超过结算单剩余额度 {payable}"],
                    hints=["请降低付款金额或拆分付款申请"],
                )

    def _check_not_overpay_settlement(self):
        """
        防超付硬校验：付款金额不得超过结算单可付余额。
        """
        for rec in self:
            if rec.type != "pay":
                continue
            if rec.settlement_id:
                metrics = opm.compute_payment_payable_excluding_self(rec)
                payable = metrics["payable"]
                precision = metrics["precision"]
                amount = rec.amount or 0.0
                if float_compare(amount, payable, precision_rounding=precision) == 1:
                    raise_guard(
                        "P0_PAYMENT_OVER_BALANCE",
                        f"付款申请[{rec.display_name}]",
                        "提交/审批付款申请",
                        reasons=[f"付款金额 {amount} 超出结算单可付余额 {payable}"],
                        hints=["请降低付款金额或先调整结算单余额"],
                    )
                continue
            settlement_amounts = {}
            for line in rec.outflow_line_ids.filtered("settlement_id"):
                settlement_amounts[line.settlement_id.id] = (
                    settlement_amounts.get(line.settlement_id.id, 0.0) + (line.current_pay_amount or 0.0)
                )
            if not settlement_amounts:
                continue
            for settlement in rec.env["sc.settlement.order"].browse(settlement_amounts.keys()):
                amount = settlement_amounts.get(settlement.id, 0.0)
                metrics = opm.compute_settlement_reservable_excluding_request(rec, settlement, amount)
                payable = metrics["payable"]
                precision = metrics["precision"]
                if float_compare(amount, payable, precision_rounding=precision) == 1:
                    raise_guard(
                        "P0_PAYMENT_OVER_BALANCE",
                        f"付款申请[{rec.display_name}]",
                        "提交/审批付款申请",
                        reasons=[f"明细结算单[{settlement.display_name}]付款金额 {amount} 超出可付余额 {payable}"],
                        hints=["请降低付款金额或先调整结算单余额"],
                    )

    def _material_settlement_requested_amount_excluding_self(self):
        self.ensure_one()
        settlement = self.material_settlement_id
        if not settlement:
            return 0.0
        domain = [
            ("material_settlement_id", "=", settlement.id),
            ("type", "=", "pay"),
            ("state", "not in", ("draft", "rejected", "cancel")),
            ("id", "!=", self.id),
        ]
        data = self.sudo().read_group(domain, ["amount:sum"], [])
        return data[0].get("amount_sum", data[0].get("amount", 0.0)) if data else 0.0

    def _check_material_settlement_remaining_amount(self):
        for rec in self:
            settlement = rec.material_settlement_id
            if rec.type != "pay" or not settlement:
                continue
            if settlement.state != "confirmed":
                raise_guard(
                    "P0_MATERIAL_SETTLEMENT_NOT_CONFIRMED",
                    f"付款申请[{rec.display_name}]",
                    "提交/审批材料付款申请",
                    reasons=[_("材料结算单未确认")],
                    hints=[_("请先确认材料结算单")],
                )
            precision = rec.currency_id.rounding if rec.currency_id else 0.01
            requested = rec._material_settlement_requested_amount_excluding_self()
            payable = (settlement.amount_total or 0.0) - (requested or 0.0)
            amount = rec.amount or 0.0
            if float_compare(payable, 0.0, precision_rounding=precision) <= 0:
                raise_guard(
                    "P0_MATERIAL_PAYMENT_OVER_BALANCE",
                    f"付款申请[{rec.display_name}]",
                    "提交/审批材料付款申请",
                    reasons=[f"材料结算剩余可申请金额不足（剩余：{payable}）"],
                    hints=[_("请先撤销多余付款申请或调整本次申请金额")],
                )
            if float_compare(amount, payable, precision_rounding=precision) == 1:
                raise_guard(
                    "P0_MATERIAL_PAYMENT_OVER_BALANCE",
                    f"付款申请[{rec.display_name}]",
                    "提交/审批材料付款申请",
                    reasons=[f"本次申请金额 {amount} 超过材料结算剩余可申请金额 {payable}"],
                    hints=[_("请降低付款金额或拆分到后续付款申请")],
                )

    def _compute_is_overpay_risk(self):
        """用于 UI 高亮：金额 > 可付余额 时标记风险。"""
        for rec in self:
            if rec.type != "pay":
                rec.is_overpay_risk = False
                continue
            if rec.material_settlement_id:
                precision = rec.currency_id.rounding if rec.currency_id else 0.01
                payable = (rec.material_settlement_id.amount_total or 0.0) - (
                    rec._material_settlement_requested_amount_excluding_self() or 0.0
                )
                rec.is_overpay_risk = float_compare(rec.amount or 0.0, payable, precision_rounding=precision) == 1
                continue
            if not rec.settlement_id:
                settlement_amounts = {}
                for line in rec.outflow_line_ids.filtered("settlement_id"):
                    settlement_amounts[line.settlement_id.id] = (
                        settlement_amounts.get(line.settlement_id.id, 0.0) + (line.current_pay_amount or 0.0)
                    )
                if not settlement_amounts:
                    rec.is_overpay_risk = False
                    continue
                risk = False
                for settlement in rec.env["sc.settlement.order"].browse(settlement_amounts.keys()):
                    amount = settlement_amounts.get(settlement.id, 0.0)
                    try:
                        metrics = opm.compute_settlement_reservable_excluding_request(rec, settlement, amount)
                    except ValidationError:
                        risk = True
                        break
                    payable = metrics["payable"]
                    precision = metrics["precision"]
                    if float_compare(amount, payable, precision_rounding=precision) == 1:
                        risk = True
                        break
                rec.is_overpay_risk = risk
                continue
            try:
                metrics = opm.compute_payment_payable_excluding_self(rec)
            except ValidationError:
                rec.is_overpay_risk = True
                continue
            payable = metrics["payable"]
            precision = metrics["precision"]
            rec.is_overpay_risk = float_compare(rec.amount or 0.0, payable, precision_rounding=precision) == 1

    def action_submit(self):
        if not self._has_submit_access():
            raise ValidationError(_("你没有提交付款/收款申请的权限。"))
        advisory_result = {}
        for rec in self:
            if rec.state not in ("draft", "rejected"):
                raise UserError(
                    _("只有草稿或已驳回的付款/收款申请可以提交审批。")
                )
            if (rec.amount or 0.0) <= 0:
                raise UserError(_("申请金额必须大于 0。"))
            rec.partner_id._sc_assert_transaction_eligible(
                _("付款申请") if rec.type == "pay" else _("收款申请")
            )
            if not rec._has_payment_basis():
                raise UserError("请先选择关联合同或结算单后再提交付款/收款申请。")
            if rec.contract_id and rec.contract_id.state == "cancel":
                raise UserError("关联合同已取消，不能提交付款/收款申请。")
            rec._check_settlement_remaining_amount()
            rec._check_material_settlement_remaining_amount()
            advisory_result[rec.id] = rec._handle_payment_advisories(
                "提交付款申请",
                rec._collect_payment_advisories("submit"),
            )
        for rec in self:
            before = rec._snapshot_audit_payload()
            # The action has already enforced submit capability, record readability,
            # business scope and all business guards.  Keep the authoritative state
            # change, audit and tier initialization in one elevated service segment;
            # sudo mode preserves the initiating uid while avoiding a post-transition
            # record-rule intersection from breaking the approved workflow action.
            submitted = rec.sudo()
            submitted.with_context(allow_transition=True, payment_soft_gate=True).write(
                {"state": "submit", "reject_reason": False}
            )
            after = submitted._snapshot_audit_payload()
            submitted._audit_transition("payment_submitted", before, after, action_name="action_submit")
        submitted_records = self.sudo()
        submitted_records.invalidate_recordset()
        for rec in submitted_records:
            company = rec.company_id or self.env.company
            rec.with_company(company).with_context(
                allowed_company_ids=[company.id],
            ).request_validation()
        submitted_records._message_post_non_blocking(_("付款/收款申请已提交，进入审批流程。"))
        return {"warnings": advisory_result}

    def action_approve(self):
        self._assert_finance_approve_access()
        advisory_result = {}
        for rec in self:
            if rec.state != "submit":
                continue
            if rec.validation_status != "validated" and not rec.env.context.get("tier_validation_callback"):
                raise_guard(
                    "PAYMENT_TIER_INCOMPLETE",
                    f"付款申请[{rec.display_name}]",
                    "审批付款申请",
                    reasons=["tier validation not complete"],
                )
            rec._check_settlement_remaining_amount()
            rec._check_material_settlement_remaining_amount()
            advisory_result[rec.id] = rec._handle_payment_advisories(
                "审批付款申请",
                rec._collect_payment_advisories("approve"),
            )
        result = None
        for rec in self:
            if rec.state != "submit":
                continue
            rec.with_context(allow_transition=True, payment_soft_gate=True).write({"state": "approve"})
            action = rec.validate_tier()
            if action:
                result = action
        return result or {"warnings": advisory_result}

    def action_approval_decision(self):
        """Execute the current approval step without forcing the frontend to know tier state."""
        self._assert_finance_approve_access()
        result = None
        advisory_result = {}
        for rec in self:
            if rec.state != "submit":
                continue
            if rec.validation_status in ("waiting", "pending"):
                rec._check_settlement_remaining_amount()
                rec._check_material_settlement_remaining_amount()
                advisory_result[rec.id] = rec._handle_payment_advisories(
                    "审批付款申请",
                    rec._collect_payment_advisories("approve"),
                )
                action = rec.validate_tier()
                if action:
                    result = action
                continue
            if rec.validation_status == "validated":
                return rec.action_approve()
            if rec.validation_status in ("no", False) and not rec.review_ids:
                rec._check_settlement_remaining_amount()
                rec._check_material_settlement_remaining_amount()
                advisory_result[rec.id] = rec._handle_payment_advisories(
                    "审批付款申请",
                    rec._collect_payment_advisories("approve"),
                )
                before = rec._snapshot_audit_payload()
                rec.write({"validation_status": "validated"})
                rec.with_context(allow_transition=True, payment_soft_gate=True).write({"state": "approved"})
                after = rec._snapshot_audit_payload()
                rec._audit_transition("payment_approved", before, after, action_name="action_approval_decision")
                continue
            raise_guard(
                "PAYMENT_TIER_INCOMPLETE",
                f"付款申请[{rec.display_name}]",
                "审批付款申请",
                reasons=[f"validation_status={rec.validation_status}"],
            )
        return result or {"warnings": advisory_result}

    def action_set_approved(self):
        self._assert_finance_approve_access()
        advisory_result = {}
        result = None
        for rec in self:
            rec._check_settlement_remaining_amount()
            rec._check_material_settlement_remaining_amount()
            advisory_result[rec.id] = rec._handle_payment_advisories(
                "批准付款申请",
                rec._collect_payment_advisories("approve"),
            )
            if rec.state == "approve" and rec.validation_status == "validated":
                before = rec._snapshot_audit_payload()
                rec.with_context(allow_transition=True, payment_soft_gate=True).write({"state": "approved"})
                after = rec._snapshot_audit_payload()
                rec._audit_transition("payment_approved", before, after, action_name="action_set_approved")
                continue
            action = rec.validate_tier()
            if action:
                result = action
                continue
        return result or {"warnings": advisory_result}

    def action_done(self):
        has_finance_done_access = self.env.user.has_group("smart_construction_core.group_sc_cap_finance_manager")
        if not has_finance_done_access:
            raise ValidationError(_("你没有完成付款/收款申请的权限。"))
        advisory_result = {}
        for rec in self:
            if rec.type == "pay":
                raise UserError(
                    _(
                        "付款申请必须通过专业付款登记完成实付；请生成付款登记，完成审批、付款账户确认和已付款登记。"
                    )
                )
            approved_reviews = rec.review_ids.filtered(lambda review: review.status == "approved")
            open_reviews = rec.review_ids.filtered(
                lambda review: review.status not in ("approved", "rejected")
            )
            tier_callback_complete = bool(approved_reviews) and not open_reviews
            if rec.validation_status != "validated" and not tier_callback_complete:
                raise_guard(
                    "PAYMENT_TIER_INCOMPLETE",
                    f"付款申请[{rec.display_name}]",
                    "完成付款申请",
                    reasons=["tier validation not complete"],
                )
            if rec.state != "approved":
                raise_guard(
                    "PAYMENT_GUARD_NOT_READY",
                    f"付款申请[{rec.display_name}]",
                    "完成付款申请",
                    reasons=[f"当前状态为 {rec.state}"],
                )
            rec._check_settlement_remaining_amount()
            rec._check_material_settlement_remaining_amount()
            advisory_result[rec.id] = rec._handle_payment_advisories(
                "完成付款申请",
                rec._collect_payment_advisories("done"),
            )
        for rec in self:
            before = rec._snapshot_audit_payload()
            if rec.type == "receive":
                rec.with_context(payment_soft_gate=True)._ensure_treasury_ledger(note="auto:payment_request_done")
            rec.with_context(allow_transition=True, payment_soft_gate=True).write({"state": "done"})
            after = rec._snapshot_audit_payload()
            rec._audit_transition("payment_paid", before, after, action_name="action_done")
        return {"warnings": advisory_result}

    def _ensure_payment_ledger(self, amount=None, paid_at=None, ref=None, note=None, execution=None):
        self.ensure_one()
        if not self.env.su and not (
            self.env.user.has_group("smart_construction_core.group_sc_cap_finance_user")
            or self.env.user.has_group("smart_construction_core.group_sc_cap_finance_manager")
        ):
            raise AccessError(_("你没有通过付款执行生成付款台账的能力。"))
        Ledger = self.env["payment.ledger"].sudo().with_context(
            _sc_payment_ledger_internal_create=True,
            payment_soft_gate=bool(self.env.context.get("payment_soft_gate")),
        )
        existing_domain = [("payment_request_id", "=", self.id), ("state", "=", "posted")]
        if execution:
            if execution.payment_request_id != self:
                raise UserError(_("付款登记与付款申请不一致，不能生成台账。"))
            existing_domain.append(("payment_execution_id", "=", execution.id))
        else:
            existing_domain.append(("payment_execution_id", "=", False))
        existing = Ledger.search(existing_domain, limit=1)
        if existing:
            return existing
        vals = {
            "payment_request_id": self.id,
            "amount": amount if amount is not None else (self.amount or 0.0),
            "paid_at": paid_at or fields.Datetime.now(),
            "payment_execution_id": execution.id if execution else False,
        }
        if ref:
            vals["ref"] = ref
        if note:
            vals["note"] = note
        return Ledger.create(vals)

    def _ensure_treasury_ledger(self, amount=None, date=None, note=None):
        self.ensure_one()
        if self.type != "receive":
            raise UserError(_("只有收款申请可以生成收入资金台账。"))
        Ledger = self.env["sc.treasury.ledger"].with_context(allow_ledger_auto=True)
        existing = Ledger.search([("payment_request_id", "=", self.id)], limit=1)
        if existing:
            return existing
        partner = self.partner_id
        if not partner:
            raise UserError(_("收款申请未选择往来单位，不能生成资金台账。"))
        vals = {
            "date": date or fields.Date.context_today(self),
            "project_id": self.project_id.id,
            "partner_id": partner.id,
            "settlement_id": self.settlement_id.id or False,
            "payment_request_id": self.id,
            "direction": "in",
            "amount": amount if amount is not None else (self.amount or 0.0),
            "currency_id": self.currency_id.id,
            "note": note,
        }
        return Ledger.create(vals)

    def action_cancel(self):
        has_finance_cancel_access = self.env.user.has_group("smart_construction_core.group_sc_cap_finance_manager")
        if not has_finance_cancel_access:
            raise ValidationError(_("你没有取消付款/收款申请的权限。"))
        for rec in self:
            if rec.state in ("done", "cancel"):
                raise_guard(
                    "PAYMENT_CANCEL_INVALID_STATE",
                    f"付款/收款申请[{rec.display_name}]",
                    _("取消付款/收款申请"),
                    reasons=[_("已完成或已取消的付款/收款申请不能直接取消。")],
                    hints=[_("已付款执行请先从付款执行单撤销；已收款入账需走后续冲销/红冲流程。")],
                )
            payment_ledger_count = self.env["payment.ledger"].sudo().search_count(
                [("payment_request_id", "=", rec.id), ("state", "=", "posted")]
            )
            treasury_ledger_count = self.env["sc.treasury.ledger"].sudo().search_count(
                [("payment_request_id", "=", rec.id), ("state", "!=", "void")]
            )
            if payment_ledger_count or treasury_ledger_count:
                raise_guard(
                    "PAYMENT_CANCEL_LEDGER_EXISTS",
                    f"付款/收款申请[{rec.display_name}]",
                    _("取消付款/收款申请"),
                    reasons=[_("当前申请已生成付款或资金台账，不能直接取消。")],
                    hints=[_("请先按对应业务链路撤销付款执行或办理收款冲销，保持台账可追溯。")],
                )
            before = rec._snapshot_audit_payload()
            rec.with_context(allow_transition=True).write({"state": "cancel"})
            after = rec._snapshot_audit_payload()
            rec._audit_transition("payment_cancelled", before, after, action_name="action_cancel")

    def _check_state_from_condition(self):
        self.ensure_one()
        parent = getattr(super(), "_check_state_from_condition", None)
        base_ok = parent() if parent else False
        return base_ok or self.state == "submit"

    def action_on_tier_approved(self):
        for rec in self:
            if rec.state != "submit":
                continue
            rec._check_settlement_remaining_amount()
            rec._check_material_settlement_remaining_amount()
            advisories = rec._collect_payment_advisories("approve")
            if advisories:
                lines = [
                    "- %s" % str(item.get("message") or item.get("reason_code") or "").strip()
                    for item in advisories
                    if str(item.get("message") or item.get("reason_code") or "").strip()
                ]
                if lines:
                    rec._message_post_non_blocking(_("付款申请审批风险提示：\n%s") % "\n".join(lines))
            before = rec._snapshot_audit_payload()
            rec.with_context(
                allow_transition=True,
                payment_soft_gate=True,
                tier_validation_callback=True,
            ).write({"state": "approved"})
            after = rec._snapshot_audit_payload()
            rec._audit_transition("payment_approved", before, after, action_name="action_on_tier_approved")
            rec._message_post_non_blocking(_("付款/收款申请审批通过。"))

    def _get_tier_reject_reason(self):
        self.ensure_one()
        reviews = self.review_ids.filtered(lambda review: review.status == "rejected" and review.comment)
        if reviews:
            return reviews.sorted(lambda review: review.write_date or review.create_date, reverse=True)[0].comment
        return False

    def action_on_tier_rejected(self, reason=None):
        for rec in self:
            if rec.state != "submit":
                continue
            reason = reason or rec._get_tier_reject_reason()
            if not reason:
                raise_guard(
                    "AUDIT_REASON_REQUIRED",
                    f"付款申请[{rec.display_name}]",
                    "审批驳回",
                    reasons=["reason is required"],
                )
            before = rec._snapshot_audit_payload()
            rec.with_context(allow_transition=True).write(
                {"state": "rejected", "reject_reason": reason}
            )
            after = rec._snapshot_audit_payload()
            rec._audit_transition(
                "payment_rejected",
                before,
                after,
                reason=reason,
                require_reason=True,
                action_name="action_on_tier_rejected",
            )
            rec._message_post_non_blocking(_("付款/收款申请审批驳回：%s") % reason)
