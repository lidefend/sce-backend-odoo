# -*- coding: utf-8 -*-
import ast

from odoo import api, fields, models, tools
from odoo.exceptions import UserError


class ScFinanceBusinessFact(models.Model):
    _name = "sc.finance.business.fact"
    _description = "项目收付款来源明细"
    _auto = False
    _rec_name = "display_name"
    _order = "document_date desc, id desc"
    _sc_readonly_navigation_button_methods = {
        "action_open_source_record",
        "action_open_business_entry",
    }

    _BUSINESS_ENTRY_ACTION_BY_FACT_TYPE = {
        "deduction_bill": "smart_construction_core.action_sc_expense_claim_deduction_bill",
        "deduction_paid": "smart_construction_core.action_sc_expense_claim_deduction_paid",
        "deduction_refund": "smart_construction_core.action_sc_expense_claim_deduction_paid_refund",
        "tax_deducted": "smart_construction_core.action_sc_tax_deduction_registration_user",
        "guarantee_out": "smart_construction_core.action_sc_expense_claim_deposit",
        "guarantee_return": "smart_construction_core.action_sc_expense_claim_deposit",
        "self_funding_income": "smart_construction_core.action_sc_self_funding_registration_income",
        "self_funding_refund": "smart_construction_core.action_sc_self_funding_registration_refund",
        "arrival_gross": "smart_construction_core.action_sc_receipt_income_user",
    }

    display_name = fields.Char(string="业务摘要", readonly=True)
    business_domain = fields.Selection(
        [
            ("arrival_settlement", "到款确认"),
            ("deduction_registration", "扣款登记"),
            ("deduction_clearing", "扣款实缴/退回"),
            ("tax_deduction", "抵扣登记"),
            ("self_funding", "自筹收入/退回"),
            ("guarantee_deposit", "保证金收退"),
        ],
        string="收付款类型",
        readonly=True,
        index=True,
    )
    fact_type = fields.Selection(
        [
            ("arrival_gross", "到款确认"),
            ("deduction_bill", "扣款登记"),
            ("deduction_paid", "扣款实缴"),
            ("deduction_refund", "扣款退回"),
            ("tax_deducted", "税务抵扣"),
            ("self_funding_income", "自筹收入"),
            ("self_funding_refund", "自筹退回"),
            ("self_funding_visible_reference", "自筹可见参考"),
            ("guarantee_out", "保证金支出"),
            ("guarantee_return", "保证金退回"),
        ],
        string="业务类型",
        readonly=True,
        index=True,
    )
    balance_policy = fields.Selection(
        [
            ("canonical", "正式余额"),
            ("clearing_component", "清分组成"),
            ("noncash_tax", "非现金税务事实"),
            ("noncash_deduction", "非现金扣款责任事实"),
            ("visible_reference", "可见追溯参考"),
            ("policy_required", "待口径确认"),
        ],
        string="余额策略",
        readonly=True,
        index=True,
    )
    classification_reason = fields.Char(string="口径说明", readonly=True)
    source_model = fields.Char(string="来源模型", readonly=True, index=True)
    source_res_id = fields.Integer(string="来源记录ID", readonly=True, index=True)
    source_record_name = fields.Char(string="来源单据号", readonly=True, index=True)
    source_document_no = fields.Char(string="来源编号", readonly=True, index=True)
    source_menu_hint = fields.Char(string="来源业务入口", readonly=True, index=True)
    document_date = fields.Date(string="发生日期", readonly=True, index=True)
    company_id = fields.Many2one("res.company", string="公司", readonly=True, index=True)
    currency_id = fields.Many2one("res.currency", string="币种", readonly=True)
    amount = fields.Monetary(string="业务金额", currency_field="currency_id", readonly=True)
    balance_effect = fields.Monetary(string="余额影响", currency_field="currency_id", readonly=True)
    cash_in_amount = fields.Monetary(string="现金流入", currency_field="currency_id", readonly=True)
    cash_out_amount = fields.Monetary(string="现金流出", currency_field="currency_id", readonly=True)
    deduction_amount = fields.Monetary(string="扣款/清分金额", currency_field="currency_id", readonly=True)
    paid_amount = fields.Monetary(string="拨付/实付金额", currency_field="currency_id", readonly=True)
    tax_amount = fields.Monetary(string="税额", currency_field="currency_id", readonly=True)
    project_id = fields.Many2one("project.project", string="项目", readonly=True, index=True)
    partner_id = fields.Many2one("res.partner", string="往来单位/人员", readonly=True, index=True)
    partner_name = fields.Char(string="往来单位/人员名称", readonly=True, index=True)
    state = fields.Char(string="来源状态", readonly=True, index=True)
    normalization_state = fields.Char(string="身份归一状态", readonly=True, index=True)
    cash_evidence_state = fields.Selection(
        [
            ("posted_ledger", "已入账资金证据"),
            ("missing_posted_ledger", "缺少已入账资金证据"),
            ("not_applicable", "非现金事实"),
        ],
        string="现金证据状态",
        readonly=True,
        index=True,
    )
    legacy_source_model = fields.Char(string="历史来源模型", readonly=True, index=True)
    legacy_source_table = fields.Char(string="历史来源表", readonly=True, index=True)
    legacy_record_id = fields.Char(string="历史记录ID", readonly=True, index=True)
    source_note = fields.Text(string="来源说明", readonly=True)

    def _raise_readonly_projection(self):
        raise UserError("项目收付款来源明细是只读汇总，请从来源业务单据维护数据。")

    @api.model_create_multi
    def create(self, vals_list):
        self._raise_readonly_projection()

    def write(self, vals):
        self._raise_readonly_projection()

    def unlink(self):
        self._raise_readonly_projection()

    def _action_domain(self, action_result):
        raw_domain = action_result.get("domain") or []
        if isinstance(raw_domain, str):
            try:
                parsed = ast.literal_eval(raw_domain)
            except (SyntaxError, ValueError):
                parsed = []
            return list(parsed) if isinstance(parsed, list) else []
        return list(raw_domain) if isinstance(raw_domain, list) else []

    def _source_default_context(self, target_model):
        self.ensure_one()
        source = self._source_record()
        context = {}

        def put(context_key, field_name):
            if field_name in source._fields:
                value = source[field_name]
                if value:
                    context[context_key] = value.id if hasattr(value, "id") else value

        put("default_document_no", "document_no")
        put("default_document_no", "legacy_document_no")
        if target_model == "sc.expense.claim":
            for context_key, field_name in (
                ("default_applicant_name", "applicant_name"),
                ("default_department_name", "department_name"),
                ("default_company_name_text", "company_name_text"),
                ("default_guarantee_project_name", "guarantee_project_name"),
                ("default_payee", "payee"),
                ("default_receipt_account_name", "receipt_account_name"),
                ("default_payee_account", "payee_account"),
                ("default_payee_bank", "payee_bank"),
                ("default_payment_account_name", "payment_account_name"),
                ("default_payer_account", "payer_account"),
                ("default_payer_bank", "payer_bank"),
            ):
                put(context_key, field_name)
        elif target_model == "sc.tax.deduction.registration":
            for context_key, field_name in (
                ("default_invoice_no", "invoice_no"),
                ("default_invoice_code", "invoice_code"),
                ("default_invoice_date", "invoice_date"),
                ("default_invoice_amount_untaxed", "invoice_amount_untaxed"),
                ("default_invoice_tax_amount", "invoice_tax_amount"),
                ("default_invoice_amount_total", "invoice_amount_total"),
                ("default_deduction_confirm_date", "deduction_confirm_date"),
                ("default_withholding_amount", "withholding_amount"),
                ("default_deduction_reason", "deduction_reason"),
            ):
                put(context_key, field_name)
        return context

    def _action_context(self, action_result):
        raw_context = action_result.get("context") or {}
        if isinstance(raw_context, str):
            try:
                parsed = ast.literal_eval(raw_context)
            except (SyntaxError, ValueError):
                parsed = {}
            context = dict(parsed) if isinstance(parsed, dict) else {}
        else:
            context = dict(raw_context) if isinstance(raw_context, dict) else {}
        context.update(self._source_default_context(action_result.get("res_model")))
        if self.project_id:
            context.update(
                {
                    "default_project_id": self.project_id.id,
                    "current_project_id": self.project_id.id,
                }
            )
        if self.partner_id:
            context.update(
                {
                    "default_partner_id": self.partner_id.id,
                    "current_partner_id": self.partner_id.id,
                }
            )
        if self.document_date:
            context.update(
                {
                    "default_date_claim": self.document_date,
                    "default_document_date": self.document_date,
                    "current_document_date": self.document_date,
                }
            )
        if self.amount:
            context["default_amount"] = abs(self.amount)
            context["current_business_amount"] = abs(self.amount)
        if self.display_name:
            context.setdefault("default_summary", self.display_name)
            context.setdefault("default_purpose", self.display_name)
        source_no = self.source_document_no or self.source_record_name
        if source_no:
            context["default_document_no"] = source_no
            context["current_source_document_no"] = source_no
        if self.partner_name:
            context["default_partner_name"] = self.partner_name
            context.setdefault("default_payee", self.partner_name)
            context.setdefault("default_deduction_unit_name", self.partner_name)
        note_parts = [
            self.display_name,
            "来源入口：%s" % self.source_menu_hint if self.source_menu_hint else False,
            "来源单号：%s" % source_no if source_no else False,
            self.source_note,
        ]
        context.setdefault("default_note", "\n".join(part for part in note_parts if part))
        if self.fact_type == "tax_deducted":
            if self.deduction_amount:
                context["default_deduction_amount"] = abs(self.deduction_amount)
            if self.tax_amount:
                context["default_deduction_tax_amount"] = abs(self.tax_amount)
        return context

    def _source_record(self):
        self.ensure_one()
        if not self.source_model or not self.source_res_id or self.source_model not in self.env:
            raise UserError("没有可打开的来源业务单据。")
        source = self.env[self.source_model].browse(self.source_res_id).exists()
        if not source:
            raise UserError("来源业务单据不存在或已归档。")
        source.check_access_rights("read")
        source.check_access_rule("read")
        return source

    def action_open_source_record(self):
        self.ensure_one()
        source = self._source_record()
        return {
            "type": "ir.actions.act_window",
            "name": self.source_menu_hint or source.display_name,
            "res_model": self.source_model,
            "res_id": source.id,
            "views": [(False, "form")],
            "view_mode": "form",
            "target": "current",
        }

    def action_open_business_entry(self):
        self.ensure_one()
        action_xmlid = self._BUSINESS_ENTRY_ACTION_BY_FACT_TYPE.get(self.fact_type)
        if not action_xmlid:
            return self.action_open_source_record()
        action = self.env.ref(action_xmlid, raise_if_not_found=False)
        if not action:
            return self.action_open_source_record()
        result = action.sudo().read()[0]
        domain = self._action_domain(result)
        target_model_name = result.get("res_model")
        if not target_model_name or target_model_name not in self.env:
            return self.action_open_source_record()
        target_model = self.env[target_model_name]
        if self.project_id:
            domain.append(("project_id", "=", self.project_id.id))
        if self.company_id and "company_id" in target_model._fields:
            domain.append(("company_id", "=", self.company_id.id))
        if self.currency_id and "currency_id" in target_model._fields:
            domain.append(("currency_id", "=", self.currency_id.id))
        if self.partner_id and target_model_name in {
            "sc.expense.claim",
            "sc.tax.deduction.registration",
            "sc.self.funding.registration",
        }:
            domain.append(("partner_id", "=", self.partner_id.id))
        result.update(
            {
                "name": "%s / 同类正式办理" % (self.source_menu_hint or result.get("name") or "业务办理"),
                "domain": domain,
                "context": self._action_context(result),
                "target": "current",
            }
        )
        return result

    def init(self):
        self._cr.execute(
            """
            SELECT
                to_regclass('sc_expense_claim'),
                to_regclass('sc_tax_deduction_registration'),
                to_regclass('sc_self_funding_registration'),
                to_regclass('sc_receipt_income'),
                to_regclass('sc_treasury_ledger'),
                to_regclass('tender_guarantee'),
                to_regclass('tender_bid')
            """
        )
        if not all(self._cr.fetchone()):
            return

        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                WITH cash_ledger AS (
                    SELECT l.*
                      FROM sc_treasury_ledger l
                     WHERE l.state = 'posted'
                       AND l.normalization_state IN ('normalized', 'legacy_observed_identity')
                       AND l.project_id IS NOT NULL
                       AND l.company_id IS NOT NULL
                       AND l.currency_id IS NOT NULL
                ),
                arrival AS (
                    SELECT
                        100000000 + r.id AS id,
                        COALESCE(r.name, r.document_no, '到款确认') AS display_name,
                        'arrival_settlement' AS business_domain,
                        'arrival_gross' AS fact_type,
                        CASE WHEN l.id IS NOT NULL THEN 'canonical' ELSE 'policy_required' END AS balance_policy,
                        CASE WHEN l.id IS NOT NULL
                             THEN 'received income backed by an exact posted treasury ledger'
                             ELSE 'received income retained for traceability but excluded from cash totals until posted-ledger evidence is complete'
                        END AS classification_reason,
                        'sc.receipt.income' AS source_model,
                        r.id AS source_res_id,
                        r.name AS source_record_name,
                        COALESCE(r.document_no, r.name) AS source_document_no,
                        '收款与收入登记' AS source_menu_hint,
                        r.date_receipt AS document_date,
                        r.company_id,
                        r.currency_id,
                        COALESCE(r.amount, 0.0) AS amount,
                        COALESCE(l.amount, 0.0) AS balance_effect,
                        COALESCE(l.amount, 0.0) AS cash_in_amount,
                        0.0 AS cash_out_amount,
                        COALESCE(r.deducted_invoice_amount, 0.0) + COALESCE(r.deducted_tax_amount, 0.0) AS deduction_amount,
                        COALESCE(l.amount, 0.0) AS paid_amount,
                        COALESCE(r.deducted_tax_amount, 0.0) AS tax_amount,
                        r.project_id,
                        r.partner_id,
                        COALESCE(rp.name, r.legacy_partner_name) AS partner_name,
                        r.state,
                        r.finance_identity_state AS normalization_state,
                        CASE WHEN l.id IS NOT NULL THEN 'posted_ledger' ELSE 'missing_posted_ledger' END AS cash_evidence_state,
                        r.legacy_source_model,
                        r.legacy_source_table,
                        r.legacy_record_id,
                        COALESCE(r.note, r.legacy_note) AS source_note
                    FROM sc_receipt_income r
                    LEFT JOIN res_partner rp ON rp.id = r.partner_id
                    LEFT JOIN cash_ledger l
                      ON l.id = r.treasury_ledger_id
                     AND l.direction = 'in'
                     AND l.project_id = r.project_id
                     AND l.company_id = r.company_id
                     AND l.currency_id = r.currency_id
                     AND l.partner_id = r.partner_id
                     AND (
                            (l.source_model = 'sc.receipt.income' AND l.source_res_id = r.id)
                         OR (
                                r.payment_request_id IS NOT NULL
                            AND l.payment_request_id = r.payment_request_id
                            AND l.source_model = 'payment.request'
                            AND l.source_res_id = r.payment_request_id
                            AND EXISTS (
                                SELECT 1
                                  FROM payment_request request
                                 WHERE request.id = r.payment_request_id
                                   AND request.type = 'receive'
                                   AND request.project_id = r.project_id
                                   AND request.company_id = r.company_id
                                   AND request.currency_id = r.currency_id
                                   AND request.partner_id = r.partner_id
                                   AND request.contract_id = r.contract_id
                                   AND request.terminal_cash_source_model = 'sc.receipt.income'
                                   AND request.terminal_cash_source_res_id = r.id
                            )
                         )
                     )
                    WHERE r.active IS TRUE
                      AND r.state IN ('received', 'legacy_confirmed')
                      AND r.finance_identity_state IN ('normalized', 'legacy_observed_identity')
                ),
                deduction_bill AS (
                    SELECT
                        190000000 + c.id AS id,
                        COALESCE(c.name, c.legacy_document_no, '扣款登记') AS display_name,
                        'deduction_registration' AS business_domain,
                        'deduction_bill' AS fact_type,
                        'noncash_deduction' AS balance_policy,
                        'canonical noncash deduction responsibility claim' AS classification_reason,
                        'sc.expense.claim' AS source_model,
                        c.id AS source_res_id,
                        c.name AS source_record_name,
                        COALESCE(c.legacy_document_no, c.name) AS source_document_no,
                        '公司&项目扣款' AS source_menu_hint,
                        c.date_claim AS document_date,
                        c.company_id,
                        c.currency_id,
                        COALESCE(NULLIF(c.approved_amount, 0.0), c.amount, 0.0) AS amount,
                        0.0 AS balance_effect,
                        0.0 AS cash_in_amount,
                        0.0 AS cash_out_amount,
                        COALESCE(NULLIF(c.approved_amount, 0.0), c.amount, 0.0) AS deduction_amount,
                        0.0 AS paid_amount,
                        0.0 AS tax_amount,
                        c.project_id,
                        c.partner_id,
                        COALESCE(rp.name, c.payee, c.applicant_name) AS partner_name,
                        c.state,
                        c.finance_identity_state AS normalization_state,
                        'not_applicable' AS cash_evidence_state,
                        c.legacy_source_model,
                        c.legacy_source_table,
                        c.legacy_record_id,
                        COALESCE(c.note, c.summary) AS source_note
                    FROM sc_expense_claim c
                    LEFT JOIN res_partner rp ON rp.id = c.partner_id
                    LEFT JOIN sc_business_category bc ON bc.id = c.business_category_id
                    WHERE c.active IS TRUE
                      AND bc.code = 'finance.deduction.bill'
                      AND c.state IN ('done', 'legacy_confirmed')
                      AND c.finance_identity_state IN ('normalized', 'legacy_observed_identity')
                ),
                deduction_paid AS (
                    SELECT
                        200000000 + c.id AS id,
                        COALESCE(c.name, c.legacy_document_no, '扣款实缴') AS display_name,
                        'deduction_clearing' AS business_domain,
                        'deduction_paid' AS fact_type,
                        CASE WHEN l.id IS NOT NULL THEN 'canonical' ELSE 'policy_required' END AS balance_policy,
                        CASE WHEN l.id IS NOT NULL THEN 'deduction payment backed by posted treasury ledger'
                             ELSE 'deduction payment lacks exact posted-ledger evidence' END AS classification_reason,
                        'sc.expense.claim' AS source_model,
                        c.id AS source_res_id,
                        c.name AS source_record_name,
                        COALESCE(c.legacy_document_no, c.name) AS source_document_no,
                        '扣款实缴登记' AS source_menu_hint,
                        c.date_claim AS document_date,
                        c.company_id,
                        c.currency_id,
                        COALESCE(NULLIF(c.approved_amount, 0.0), c.amount, 0.0) AS amount,
                        COALESCE(l.amount, 0.0) AS balance_effect,
                        COALESCE(l.amount, 0.0) AS cash_in_amount,
                        0.0 AS cash_out_amount,
                        COALESCE(NULLIF(c.approved_amount, 0.0), c.amount, 0.0) AS deduction_amount,
                        COALESCE(l.amount, 0.0) AS paid_amount,
                        0.0 AS tax_amount,
                        c.project_id,
                        c.partner_id,
                        COALESCE(rp.name, c.payee, c.applicant_name) AS partner_name,
                        c.state,
                        c.finance_identity_state AS normalization_state,
                        CASE WHEN l.id IS NOT NULL THEN 'posted_ledger' ELSE 'missing_posted_ledger' END AS cash_evidence_state,
                        c.legacy_source_model,
                        c.legacy_source_table,
                        c.legacy_record_id,
                        COALESCE(c.note, c.summary) AS source_note
                    FROM sc_expense_claim c
                    LEFT JOIN res_partner rp ON rp.id = c.partner_id
                    LEFT JOIN cash_ledger l
                      ON l.payment_request_id = c.payment_request_id
                     AND l.source_model = 'payment.request'
                     AND l.source_res_id = c.payment_request_id
                     AND l.direction = 'in'
                     AND l.project_id = c.project_id
                     AND l.company_id = c.company_id
                     AND l.currency_id = c.currency_id
                     AND l.partner_id = c.partner_id
                     AND EXISTS (
                         SELECT 1
                           FROM payment_request request
                          WHERE request.id = c.payment_request_id
                            AND request.type = 'receive'
                            AND request.project_id = c.project_id
                            AND request.company_id = c.company_id
                            AND request.currency_id = c.currency_id
                            AND request.partner_id = c.partner_id
                            AND request.terminal_cash_source_model = 'sc.expense.claim'
                            AND request.terminal_cash_source_res_id = c.id
                     )
                    WHERE c.active IS TRUE
                      AND c.handling_kind = 'deduction_paid'
                      AND c.state IN ('done', 'legacy_confirmed')
                      AND c.finance_identity_state IN ('normalized', 'legacy_observed_identity')
                ),
                deduction_refund AS (
                    SELECT
                        210000000 + c.id AS id,
                        COALESCE(c.name, c.legacy_document_no, '扣款退回') AS display_name,
                        'deduction_clearing' AS business_domain,
                        'deduction_refund' AS fact_type,
                        CASE WHEN l.id IS NOT NULL THEN 'canonical' ELSE 'policy_required' END AS balance_policy,
                        CASE WHEN l.id IS NOT NULL THEN 'deduction refund backed by posted treasury ledger'
                             ELSE 'deduction refund lacks exact posted-ledger evidence' END AS classification_reason,
                        'sc.expense.claim' AS source_model,
                        c.id AS source_res_id,
                        c.name AS source_record_name,
                        COALESCE(c.legacy_document_no, c.name) AS source_document_no,
                        '扣款实缴退回' AS source_menu_hint,
                        c.date_claim AS document_date,
                        c.company_id,
                        c.currency_id,
                        COALESCE(NULLIF(c.approved_amount, 0.0), c.amount, 0.0) AS amount,
                        -COALESCE(l.amount, 0.0) AS balance_effect,
                        0.0 AS cash_in_amount,
                        COALESCE(l.amount, 0.0) AS cash_out_amount,
                        COALESCE(NULLIF(c.approved_amount, 0.0), c.amount, 0.0) AS deduction_amount,
                        COALESCE(l.amount, 0.0) AS paid_amount,
                        0.0 AS tax_amount,
                        c.project_id,
                        c.partner_id,
                        COALESCE(rp.name, c.payee, c.applicant_name) AS partner_name,
                        c.state,
                        c.finance_identity_state AS normalization_state,
                        CASE WHEN l.id IS NOT NULL THEN 'posted_ledger' ELSE 'missing_posted_ledger' END AS cash_evidence_state,
                        c.legacy_source_model,
                        c.legacy_source_table,
                        c.legacy_record_id,
                        COALESCE(c.note, c.summary) AS source_note
                    FROM sc_expense_claim c
                    LEFT JOIN res_partner rp ON rp.id = c.partner_id
                    LEFT JOIN cash_ledger l
                      ON l.payment_request_id = c.payment_request_id
                     AND l.source_model = 'payment.request'
                     AND l.source_res_id = c.payment_request_id
                     AND l.direction = 'out'
                     AND l.project_id = c.project_id
                     AND l.company_id = c.company_id
                     AND l.currency_id = c.currency_id
                     AND l.partner_id = c.partner_id
                     AND EXISTS (
                         SELECT 1
                           FROM payment_request request
                          WHERE request.id = c.payment_request_id
                            AND request.type = 'pay'
                            AND request.project_id = c.project_id
                            AND request.company_id = c.company_id
                            AND request.currency_id = c.currency_id
                            AND request.partner_id = c.partner_id
                            AND request.terminal_cash_source_model = 'sc.expense.claim'
                            AND request.terminal_cash_source_res_id = c.id
                     )
                    WHERE c.active IS TRUE
                      AND c.handling_kind = 'deduction_refund'
                      AND c.state IN ('done', 'legacy_confirmed')
                      AND c.finance_identity_state IN ('normalized', 'legacy_observed_identity')
                ),
                tax_deduction AS (
                    SELECT
                        300000000 + t.id AS id,
                        COALESCE(t.name, t.document_no, '抵扣登记') AS display_name,
                        'tax_deduction' AS business_domain,
                        'tax_deducted' AS fact_type,
                        'noncash_tax' AS balance_policy,
                        'tax deduction is a fiscal fact; it does not change cash balance directly' AS classification_reason,
                        'sc.tax.deduction.registration' AS source_model,
                        t.id AS source_res_id,
                        t.name AS source_record_name,
                        COALESCE(t.document_no, t.name) AS source_document_no,
                        '抵扣登记' AS source_menu_hint,
                        COALESCE(t.deduction_confirm_date, t.document_date) AS document_date,
                        t.company_id,
                        t.currency_id,
                        COALESCE(t.deduction_amount, 0.0) AS amount,
                        0.0 AS balance_effect,
                        0.0 AS cash_in_amount,
                        0.0 AS cash_out_amount,
                        COALESCE(t.withholding_amount, 0.0) AS deduction_amount,
                        0.0 AS paid_amount,
                        COALESCE(t.deduction_tax_amount, 0.0) AS tax_amount,
                        t.project_id,
                        t.partner_id,
                        COALESCE(rp.name, t.partner_name, t.deduction_unit_name) AS partner_name,
                        t.state,
                        t.finance_identity_state AS normalization_state,
                        'not_applicable' AS cash_evidence_state,
                        t.legacy_source_model,
                        t.legacy_source_table,
                        t.legacy_record_id,
                        COALESCE(t.deduction_reason, t.note) AS source_note
                    FROM sc_tax_deduction_registration t
                    LEFT JOIN res_partner rp ON rp.id = t.partner_id
                    WHERE t.active IS TRUE
                      AND t.state IN ('deducted', 'legacy_confirmed')
                      AND t.finance_identity_state IN ('normalized', 'legacy_observed_identity')
                ),
                formal_self_funding AS (
                    SELECT
                        410000000 + r.id AS id,
                        COALESCE(r.name, r.document_no, r.summary, '自筹办理') AS display_name,
                        'self_funding' AS business_domain,
                        CASE WHEN r.funding_type = 'refund' THEN 'self_funding_refund' ELSE 'self_funding_income' END AS fact_type,
                        CASE WHEN l.id IS NOT NULL THEN 'canonical' ELSE 'policy_required' END AS balance_policy,
                        CASE WHEN l.id IS NOT NULL THEN 'self funding backed by exact posted treasury ledger'
                             ELSE 'self funding lacks exact posted-ledger evidence' END AS classification_reason,
                        'sc.self.funding.registration' AS source_model,
                        r.id AS source_res_id,
                        r.name AS source_record_name,
                        COALESCE(r.document_no, r.name) AS source_document_no,
                        CASE WHEN r.funding_type = 'refund' THEN '自筹退回办理' ELSE '自筹垫付办理' END AS source_menu_hint,
                        r.document_date,
                        r.company_id,
                        r.currency_id,
                        COALESCE(r.amount, 0.0) AS amount,
                        CASE WHEN r.funding_type = 'refund' THEN -COALESCE(l.amount, 0.0) ELSE COALESCE(l.amount, 0.0) END AS balance_effect,
                        CASE WHEN r.funding_type = 'income' THEN COALESCE(l.amount, 0.0) ELSE 0.0 END AS cash_in_amount,
                        CASE WHEN r.funding_type = 'refund' THEN COALESCE(l.amount, 0.0) ELSE 0.0 END AS cash_out_amount,
                        0.0 AS deduction_amount,
                        0.0 AS paid_amount,
                        0.0 AS tax_amount,
                        r.project_id,
                        r.partner_id,
                        rp.name AS partner_name,
                        r.state,
                        r.finance_identity_state AS normalization_state,
                        CASE WHEN l.id IS NOT NULL THEN 'posted_ledger' ELSE 'missing_posted_ledger' END AS cash_evidence_state,
                        CASE WHEN r.source_origin = 'legacy' THEN 'online_old_legacy_source:self_funding' ELSE NULL::varchar END AS legacy_source_model,
                        r.legacy_source_table AS legacy_source_table,
                        r.legacy_record_id AS legacy_record_id,
                        COALESCE(r.note, r.summary) AS source_note
                    FROM sc_self_funding_registration r
                    LEFT JOIN res_partner rp ON rp.id = r.partner_id
                    LEFT JOIN cash_ledger l
                      ON l.source_model = 'sc.self.funding.registration'
                     AND l.source_res_id = r.id
                     AND l.source_kind = 'self_funding'
                     AND l.direction = CASE WHEN r.funding_type = 'refund' THEN 'out' ELSE 'in' END
                     AND l.project_id = r.project_id
                     AND l.company_id = r.company_id
                     AND l.currency_id = r.currency_id
                    WHERE r.active IS TRUE
                      AND r.state = 'done'
                      AND r.finance_identity_state IN ('normalized', 'legacy_observed_identity')
                ),
                guarantee AS (
                    SELECT
                        500000000 + g.id AS id,
                        COALESCE(b.name, b.tender_name, '保证金') AS display_name,
                        'guarantee_deposit' AS business_domain,
                        CASE WHEN g.type = 'return' THEN 'guarantee_return' ELSE 'guarantee_out' END AS fact_type,
                        CASE WHEN l.id IS NOT NULL THEN 'canonical' ELSE 'policy_required' END AS balance_policy,
                        CASE WHEN l.id IS NOT NULL THEN 'confirmed guarantee backed by exact posted treasury ledger'
                             ELSE 'confirmed guarantee lacks exact posted-ledger evidence' END AS classification_reason,
                        'tender.guarantee' AS source_model,
                        g.id AS source_res_id,
                        b.name AS source_record_name,
                        b.name AS source_document_no,
                        CASE WHEN g.type = 'return' THEN '保证金退回' ELSE '保证金支出' END AS source_menu_hint,
                        g.date AS document_date,
                        g.company_id,
                        g.currency_id,
                        COALESCE(g.amount, 0.0) AS amount,
                        CASE WHEN g.type = 'return' THEN -COALESCE(l.amount, 0.0) ELSE COALESCE(l.amount, 0.0) END AS balance_effect,
                        CASE WHEN g.type = 'return' THEN COALESCE(l.amount, 0.0) ELSE 0.0 END AS cash_in_amount,
                        CASE WHEN g.type = 'return' THEN 0.0 ELSE COALESCE(l.amount, 0.0) END AS cash_out_amount,
                        0.0 AS deduction_amount,
                        0.0 AS paid_amount,
                        0.0 AS tax_amount,
                        g.project_id,
                        g.partner_id,
                        COALESCE(rp.name, b.legacy_owner_name) AS partner_name,
                        g.state,
                        g.finance_identity_state AS normalization_state,
                        CASE WHEN l.id IS NOT NULL THEN 'posted_ledger' ELSE 'missing_posted_ledger' END AS cash_evidence_state,
                        b.legacy_fact_model AS legacy_source_model,
                        'tender_guarantee' AS legacy_source_table,
                        NULLIF(b.legacy_fact_id::varchar, '') AS legacy_record_id,
                        COALESCE(g.remark, b.legacy_note) AS source_note
                    FROM tender_guarantee g
                    JOIN tender_bid b ON b.id = g.bid_id
                    LEFT JOIN res_partner rp ON rp.id = g.partner_id
                    LEFT JOIN cash_ledger l
                      ON l.id = g.treasury_ledger_id
                     AND l.source_model = 'tender.guarantee'
                     AND l.source_res_id = g.id
                     AND l.direction = CASE WHEN g.type = 'return' THEN 'in' ELSE 'out' END
                     AND l.project_id = g.project_id
                     AND l.company_id = g.company_id
                     AND l.currency_id = g.currency_id
                    WHERE g.state = 'confirmed'
                      AND g.finance_identity_state IN ('normalized', 'legacy_observed_identity')
                )
                SELECT * FROM arrival
                UNION ALL SELECT * FROM deduction_bill
                UNION ALL SELECT * FROM deduction_paid
                UNION ALL SELECT * FROM deduction_refund
                UNION ALL SELECT * FROM tax_deduction
                UNION ALL SELECT * FROM formal_self_funding
                UNION ALL SELECT * FROM guarantee
            )
            """
        )
