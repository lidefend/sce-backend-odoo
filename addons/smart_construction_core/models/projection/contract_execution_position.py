# -*- coding: utf-8 -*-
from odoo import _, api, fields, models, tools
from odoo.exceptions import AccessError


class ScContractExecutionPosition(models.Model):
    """Read-only current-position projection over authoritative contract facts."""

    _name = "sc.contract.execution.position"
    _description = "合同执行态势"
    _auto = False
    _order = "company_id, project_id, type, contract_id"

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
                    SELECT contract_id, SUM(amount)::numeric AS amount
                      FROM sc_receipt_income
                     WHERE contract_id IS NOT NULL
                       AND state IN ('received', 'legacy_confirmed')
                     GROUP BY contract_id
                ), payment AS (
                    SELECT a.contract_id, SUM(a.allocated_amount)::numeric AS amount
                      FROM payment_ledger_allocation a
                      JOIN payment_ledger l ON l.id = a.ledger_id
                     WHERE a.contract_id IS NOT NULL
                       AND a.allocation_state = 'allocated'
                       AND l.state = 'posted'
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

    @api.model_create_multi
    def create(self, vals_list):
        raise AccessError(_("合同执行态势是只读投影。"))

    def write(self, vals):
        raise AccessError(_("合同执行态势是只读投影。"))

    def unlink(self):
        raise AccessError(_("合同执行态势是只读投影。"))
