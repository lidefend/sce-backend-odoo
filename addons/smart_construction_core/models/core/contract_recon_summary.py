# -*- coding: utf-8 -*-
from odoo import api, fields, models

from ..support import operating_metrics as opm


class ScContractReconSummary(models.Model):
    _name = "sc.contract.recon.summary"
    _description = "合同对账汇总"

    contract_id = fields.Many2one(
        "construction.contract",
        string="合同",
        required=True,
        index=True,
    )
    project_id = fields.Many2one(
        "project.project",
        string="项目",
        related="contract_id.project_id",
        store=True,
        readonly=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="往来单位",
        related="contract_id.partner_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="币种",
        related="contract_id.currency_id",
        store=True,
        readonly=True,
    )
    contract_amount_total = fields.Monetary(
        string="最终合同价",
        currency_field="currency_id",
        related="contract_id.amount_final",
        store=False,
        readonly=True,
    )
    settlement_total = fields.Monetary(
        string="结算金额",
        currency_field="currency_id",
        compute="_compute_totals",
        store=False,
    )
    settlement_ids_count = fields.Integer(
        string="结算单数",
        compute="_compute_totals",
        store=False,
    )
    payment_total = fields.Monetary(
        string="现金执行金额",
        currency_field="currency_id",
        compute="_compute_totals",
        store=False,
    )
    payment_ids_count = fields.Integer(
        string="现金执行单数",
        compute="_compute_totals",
        store=False,
    )
    delta = fields.Monetary(
        string="差额",
        currency_field="currency_id",
        compute="_compute_totals",
        store=False,
    )
    as_of_date = fields.Date(
        string="兼容日期（不参与当前态计算）",
        default=fields.Date.context_today,
        readonly=True,
        help="兼容既有记录保留；本模型仅表达当前合同执行态势，不提供历史时点重算。",
    )

    @api.depends("contract_id")
    def _compute_totals(self):
        contract_ids = self.mapped("contract_id").ids
        position_map = opm.contract_execution_position_map(self.env, contract_ids)
        settlement_count_map = {}
        settlement_count_rows = self.env["sc.settlement.order.line"].sudo().read_group(
            [
                ("contract_id", "in", contract_ids),
                ("settlement_id.state", "in", ["approve", "done"]),
            ],
            ["contract_id", "settlement_id"],
            ["contract_id", "settlement_id"],
            lazy=False,
        ) if contract_ids else []
        for row in settlement_count_rows:
            contract = row.get("contract_id")
            if contract:
                settlement_count_map[contract[0]] = settlement_count_map.get(contract[0], 0) + 1

        payment_count_map = {}
        payment_count_rows = self.env["payment.ledger.allocation"].sudo().read_group(
            [
                ("contract_id", "in", contract_ids),
                ("allocation_state", "=", "allocated"),
                ("normalization_state", "in", ["normalized", "legacy_observed_identity"]),
                ("ledger_id.state", "=", "posted"),
                ("ledger_id.normalization_state", "in", ["normalized", "legacy_observed_identity"]),
            ],
            ["contract_id", "ledger_id"],
            ["contract_id", "ledger_id"],
            lazy=False,
        ) if contract_ids else []
        for row in payment_count_rows:
            contract = row.get("contract_id")
            if contract:
                payment_count_map[contract[0]] = payment_count_map.get(contract[0], 0) + 1

        self.mapped("contract_id.type")
        for rec in self:
            contract = rec.contract_id
            position = position_map.get(contract.id, {})
            settlement_total = position.get("settled", 0.0)
            if contract.type == "out":
                payment_total = position.get("received", 0.0)
                payment_count = position.get("received_evidence_count", 0)
            else:
                payment_total = position.get("paid", 0.0)
                payment_count = payment_count_map.get(contract.id, 0)
            rec.settlement_total = settlement_total
            rec.settlement_ids_count = settlement_count_map.get(contract.id, 0)
            rec.payment_total = payment_total
            rec.payment_ids_count = payment_count
            rec.delta = settlement_total - payment_total
