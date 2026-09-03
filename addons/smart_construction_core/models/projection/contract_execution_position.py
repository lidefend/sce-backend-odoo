# -*- coding: utf-8 -*-
from odoo import _, api, fields, models, tools
from odoo.exceptions import AccessError


class ScContractExecutionPosition(models.Model):
    """Read-only current-position projection over authoritative contract facts."""

    _name = "sc.contract.execution.position"
    _description = "合同执行态势"
    _auto = False
    _order = "company_id, project_id, type, contract_id"
    _sc_readonly_navigation_button_methods = {
        "action_open_execution_source_contract",
        "action_open_cash_evidence",
    }

    contract_id = fields.Many2one("construction.contract", string="合同", readonly=True, index=True)
    subject = fields.Char(string="合同标题", readonly=True)
    type = fields.Selection([("out", "收入合同"), ("in", "支出合同")], string="收支方向", readonly=True, index=True)
    company_id = fields.Many2one("res.company", string="公司", readonly=True, index=True)
    project_id = fields.Many2one("project.project", string="项目", readonly=True, index=True)
    partner_id = fields.Many2one("res.partner", string="往来单位", readonly=True, index=True)
    state = fields.Char(string="合同状态", readonly=True, index=True)
    currency_id = fields.Many2one("res.currency", string="币种", readonly=True)
    contract_amount = fields.Monetary(string="最终合同价", currency_field="currency_id", readonly=True)
    settled_amount = fields.Monetary(string="已结算", currency_field="currency_id", readonly=True)
    settlement_balance = fields.Monetary(string="未结算", currency_field="currency_id", readonly=True)
    invoiced_amount = fields.Monetary(string="已开票", currency_field="currency_id", readonly=True)
    invoice_balance = fields.Monetary(string="未开票", currency_field="currency_id", readonly=True)
    cash_executed_amount = fields.Monetary(string="现金执行", currency_field="currency_id", readonly=True)
    cash_balance = fields.Monetary(string="现金未执行", currency_field="currency_id", readonly=True)
    settlement_rate = fields.Float(string="结算比例", readonly=True)
    invoice_rate = fields.Float(string="开票比例", readonly=True)
    cash_execution_rate = fields.Float(string="现金执行比例", readonly=True)
    ratio_defined = fields.Boolean(string="比例有效", readonly=True, index=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                WITH settlement AS (
                    SELECT l.contract_id, SUM(l.amount)::numeric AS amount
                      FROM sc_settlement_order_line l
                      JOIN sc_settlement_order s ON s.id = l.settlement_id
                     WHERE l.contract_id IS NOT NULL
                       AND s.state IN ('approve', 'done')
                     GROUP BY l.contract_id
                ), adjustment AS (
                    SELECT contract_id, SUM(signed_amount)::numeric AS amount
                      FROM sc_settlement_adjustment
                     WHERE contract_id IS NOT NULL
                       AND state IN ('confirmed', 'legacy_confirmed')
                       AND active IS TRUE
                     GROUP BY contract_id
                ), invoice AS (
                    SELECT contract_id, direction, SUM(amount_total)::numeric AS amount
                      FROM sc_invoice_registration
                     WHERE contract_id IS NOT NULL
                       AND state IN ('registered', 'legacy_confirmed')
                     GROUP BY contract_id, direction
                ), receipt AS (
                    SELECT request.contract_id, SUM(ledger.amount)::numeric AS amount
                      FROM sc_treasury_ledger ledger
                      JOIN payment_request request ON request.id = ledger.payment_request_id
                      JOIN construction_contract contract ON contract.id = request.contract_id
                      JOIN sc_receipt_income receipt
                        ON receipt.payment_request_id = request.id
                       AND receipt.treasury_ledger_id = ledger.id
                     WHERE request.contract_id IS NOT NULL
                       AND ledger.state = 'posted'
                       AND ledger.direction = 'in'
                       AND ledger.normalization_state IN ('normalized', 'legacy_observed_identity')
                       AND ledger.source_model = 'payment.request'
                       AND ledger.source_res_id = request.id
                       AND ledger.project_id = contract.project_id
                       AND ledger.company_id = contract.company_id
                       AND ledger.currency_id = contract.currency_id
                       AND ledger.partner_id = contract.partner_id
                       AND request.project_id = contract.project_id
                       AND request.company_id = contract.company_id
                       AND request.currency_id = contract.currency_id
                       AND request.partner_id = contract.partner_id
                       AND request.terminal_cash_source_model = 'sc.receipt.income'
                       AND request.terminal_cash_source_res_id = receipt.id
                       AND receipt.contract_id = contract.id
                       AND receipt.state IN ('received', 'legacy_confirmed')
                       AND receipt.finance_identity_state IN ('normalized', 'legacy_observed_identity')
                       AND receipt.project_id = contract.project_id
                       AND receipt.company_id = contract.company_id
                       AND receipt.currency_id = contract.currency_id
                       AND receipt.partner_id = contract.partner_id
                     GROUP BY request.contract_id
                ), payment AS (
                    SELECT a.contract_id, SUM(a.allocated_amount)::numeric AS amount
                      FROM payment_ledger_allocation a
                      JOIN payment_ledger l ON l.id = a.ledger_id
                      JOIN construction_contract contract ON contract.id = a.contract_id
                     WHERE a.contract_id IS NOT NULL
                       AND a.allocation_state = 'allocated'
                       AND a.normalization_state IN ('normalized', 'legacy_observed_identity')
                       AND l.state = 'posted'
                       AND l.normalization_state IN ('normalized', 'legacy_observed_identity')
                       AND a.project_id = contract.project_id
                       AND a.company_id = contract.company_id
                       AND a.currency_id = contract.currency_id
                       AND l.project_id = contract.project_id
                       AND l.company_id = contract.company_id
                       AND l.currency_id = contract.currency_id
                     GROUP BY a.contract_id
                ), position AS (
                    SELECT c.id,
                           c.id AS contract_id,
                           c.subject,
                           c.type,
                           c.company_id,
                           c.project_id,
                           c.partner_id,
                           c.state,
                           c.currency_id,
                           COALESCE(c.amount_final, 0.0)::numeric AS contract_amount,
                           (COALESCE(s.amount, 0.0) + COALESCE(a.amount, 0.0))::numeric AS settled_amount,
                           COALESCE(CASE WHEN c.type = 'out' THEN io.amount ELSE ii.amount END, 0.0)::numeric AS invoiced_amount,
                           COALESCE(CASE WHEN c.type = 'out' THEN r.amount ELSE p.amount END, 0.0)::numeric AS cash_executed_amount
                      FROM construction_contract c
                 LEFT JOIN settlement s ON s.contract_id = c.id
                 LEFT JOIN adjustment a ON a.contract_id = c.id
                 LEFT JOIN invoice io ON io.contract_id = c.id AND io.direction = 'output'
                 LEFT JOIN invoice ii ON ii.contract_id = c.id AND ii.direction = 'input'
                 LEFT JOIN receipt r ON r.contract_id = c.id
                 LEFT JOIN payment p ON p.contract_id = c.id
                     WHERE c.active IS TRUE
                )
                SELECT p.*,
                       (p.contract_amount - p.settled_amount)::numeric AS settlement_balance,
                       (p.contract_amount - p.invoiced_amount)::numeric AS invoice_balance,
                       (p.contract_amount - p.cash_executed_amount)::numeric AS cash_balance,
                       CASE WHEN p.contract_amount != 0 THEN p.settled_amount / p.contract_amount * 100.0 ELSE NULL END::double precision AS settlement_rate,
                       CASE WHEN p.contract_amount != 0 THEN p.invoiced_amount / p.contract_amount * 100.0 ELSE NULL END::double precision AS invoice_rate,
                       CASE WHEN p.contract_amount != 0 THEN p.cash_executed_amount / p.contract_amount * 100.0 ELSE NULL END::double precision AS cash_execution_rate,
                       (p.contract_amount != 0) AS ratio_defined
                  FROM position p
            )
            """
        )

    def action_open_execution_source_contract(self):
        self.ensure_one()
        return self.contract_id.action_open_execution_source_contract()

    def action_open_cash_evidence(self):
        self.ensure_one()
        identity = [
            ("project_id", "=", self.project_id.id),
            ("currency_id", "=", self.currency_id.id),
        ]
        if self.type == "out":
            return {
                "type": "ir.actions.act_window",
                "name": _("合同收款资金证据"),
                "res_model": "sc.treasury.ledger",
                "view_mode": "tree,form",
                "domain": identity
                + [
                    ("company_id", "=", self.company_id.id),
                    ("payment_request_id.contract_id", "=", self.contract_id.id),
                    ("payment_request_id.type", "=", "receive"),
                    ("payment_request_id.partner_id", "=", self.partner_id.id),
                    ("payment_request_id.terminal_cash_source_model", "=", "sc.receipt.income"),
                    ("source_model", "=", "payment.request"),
                    ("direction", "=", "in"),
                    ("state", "=", "posted"),
                    ("normalization_state", "in", ("normalized", "legacy_observed_identity")),
                ],
                "context": {"create": False, "edit": False, "delete": False},
            }
        allocation_tree = self.env.ref(
            "smart_construction_core.view_payment_ledger_allocation_evidence_tree"
        )
        allocation_form = self.env.ref(
            "smart_construction_core.view_payment_ledger_allocation_evidence_form"
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("合同付款分配证据"),
            "res_model": "payment.ledger.allocation",
            "view_mode": "tree,form",
            "views": [(allocation_tree.id, "tree"), (allocation_form.id, "form")],
            "domain": identity
            + [
                ("company_id", "=", self.company_id.id),
                ("contract_id", "=", self.contract_id.id),
                ("allocation_state", "=", "allocated"),
                ("normalization_state", "in", ("normalized", "legacy_observed_identity")),
                ("ledger_id.state", "=", "posted"),
                ("ledger_id.normalization_state", "in", ("normalized", "legacy_observed_identity")),
            ],
            "context": {"create": False, "edit": False, "delete": False},
        }

    @api.model_create_multi
    def create(self, vals_list):
        raise AccessError(_("合同执行态势是只读投影。"))

    def write(self, vals):
        raise AccessError(_("合同执行态势是只读投影。"))

    def unlink(self):
        raise AccessError(_("合同执行态势是只读投影。"))
