# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import AccessError


class PaymentLedgerAllocation(models.Model):
    """Immutable contract attribution captured with an actual-payment fact."""

    _name = "payment.ledger.allocation"
    _description = "付款台账合同分摊事实"
    _order = "ledger_id, allocation_key, id"

    ledger_id = fields.Many2one(
        "payment.ledger", string="付款台账", required=True, ondelete="restrict", index=True
    )
    payment_request_id = fields.Many2one(
        "payment.request",
        string="付款申请",
        related="ledger_id.payment_request_id",
        store=True,
        readonly=True,
        index=True,
    )
    payment_request_line_id = fields.Many2one(
        "payment.request.line", string="分摊依据明细", ondelete="restrict", readonly=True, index=True
    )
    contract_id = fields.Many2one(
        "construction.contract", string="归属合同", ondelete="restrict", readonly=True, index=True
    )
    settlement_id = fields.Many2one(
        "sc.settlement.order", string="来源结算单", ondelete="restrict", readonly=True, index=True
    )
    settlement_line_id = fields.Many2one(
        "sc.settlement.order.line", string="来源结算行", ondelete="restrict", readonly=True, index=True
    )
    project_id = fields.Many2one(
        "project.project",
        string="项目",
        related="ledger_id.project_id",
        store=True,
        readonly=True,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="公司",
        related="project_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="币种",
        related="ledger_id.currency_id",
        store=True,
        readonly=True,
    )
    basis_amount = fields.Monetary(
        string="分摊依据快照", currency_field="currency_id", readonly=True
    )
    allocated_amount = fields.Monetary(
        string="实际归属金额", currency_field="currency_id", readonly=True
    )
    allocation_state = fields.Selection(
        [
            ("allocated", "已分摊"),
            ("unresolved_candidate", "候选合同待核对"),
            ("unresolved_global", "全局待核对"),
        ],
        string="分摊状态",
        required=True,
        readonly=True,
        index=True,
    )
    reason_code = fields.Selection(
        [
            ("request_line_ratio", "申请明细比例"),
            ("direct_contract", "唯一直接合同"),
            ("missing_basis", "缺少分摊依据"),
            ("unresolved_contract", "合同依据不完整或冲突"),
            ("basis_total_mismatch", "依据合计与申请金额不一致"),
            ("invalid_basis_amount", "分摊依据金额无效"),
            ("currency_mismatch", "币种不一致"),
            ("project_company_mismatch", "项目或公司不一致"),
            ("historical_backfill_unresolved", "历史台账待核对"),
        ],
        string="原因码",
        required=True,
        readonly=True,
        index=True,
    )
    allocation_key = fields.Char(string="幂等键", required=True, readonly=True, index=True)

    _sql_constraints = [
        (
            "ledger_key_unique",
            "unique(ledger_id, allocation_key)",
            "同一付款台账的合同分摊键必须唯一。",
        ),
        (
            "amount_nonnegative",
            "CHECK(allocated_amount >= 0 AND basis_amount >= 0)",
            "付款合同分摊金额不得为负数。",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su or not self.env.context.get("_sc_payment_ledger_allocation_build"):
            raise AccessError(_("付款台账合同分摊只能由受控付款事实服务生成。"))
        return super().create(vals_list)

    def write(self, vals):
        raise AccessError(_("付款台账合同分摊是不可变事实，不允许修改。"))

    def unlink(self):
        raise AccessError(_("付款台账合同分摊是不可变事实，不允许删除。"))

    def init(self):
        """Truthful one-time coverage for ledgers created before this model existed.

        A direct request contract is a strong anchor. Every other historical
        ledger remains explicitly unresolved; upgrade must never guess from a
        mutable or incomplete historical line set.
        """
        self.env.cr.execute(
            """
            INSERT INTO payment_ledger_allocation (
                ledger_id, payment_request_id, payment_request_line_id, contract_id,
                settlement_id, settlement_line_id, basis_amount,
                allocated_amount, allocation_state, reason_code, project_id,
                company_id, currency_id,
                allocation_key, create_uid, create_date, write_uid, write_date
            )
            SELECT l.id, l.payment_request_id, NULL, r.contract_id, r.settlement_id, NULL,
                   l.amount, l.amount, 'allocated', 'direct_contract',
                   r.project_id, r.company_id, r.currency_id,
                   'backfill:direct', 1, NOW(), 1, NOW()
              FROM payment_ledger l
              JOIN payment_request r ON r.id = l.payment_request_id
              JOIN construction_contract c ON c.id = r.contract_id
             WHERE r.contract_id IS NOT NULL
               AND (r.project_id IS NULL OR c.project_id = r.project_id)
               AND (r.company_id IS NULL OR c.company_id = r.company_id)
               AND (r.currency_id IS NULL OR c.currency_id = r.currency_id)
               AND NOT EXISTS (
                    SELECT 1
                     FROM payment_request_line prl
                     WHERE prl.request_id = r.id
                       AND prl.active IS TRUE
               )
               AND NOT EXISTS (
                    SELECT 1 FROM payment_ledger_allocation a WHERE a.ledger_id = l.id
               )
            """
        )
        self.env.cr.execute(
            """
            INSERT INTO payment_ledger_allocation (
                ledger_id, payment_request_id, payment_request_line_id, contract_id,
                settlement_id, settlement_line_id, basis_amount,
                allocated_amount, allocation_state, reason_code, project_id,
                company_id, currency_id,
                allocation_key, create_uid, create_date, write_uid, write_date
            )
            SELECT l.id, l.payment_request_id, NULL, NULL, r.settlement_id, NULL,
                   0, 0, 'unresolved_global', 'historical_backfill_unresolved',
                   r.project_id, r.company_id, r.currency_id,
                   'backfill:unresolved', 1, NOW(), 1, NOW()
              FROM payment_ledger l
              JOIN payment_request r ON r.id = l.payment_request_id
             WHERE NOT EXISTS (
                    SELECT 1 FROM payment_ledger_allocation a WHERE a.ledger_id = l.id
               )
            """
        )
        self.env.cr.execute(
            """
            WITH allocation_totals AS (
                SELECT ledger_id,
                       COALESCE(SUM(allocated_amount), 0) AS allocated_amount,
                       COUNT(*) FILTER (WHERE allocation_state != 'allocated') AS unresolved_count
                  FROM payment_ledger_allocation
              GROUP BY ledger_id
            ), desired AS (
                SELECT l.id AS ledger_id,
                       t.allocated_amount,
                       GREATEST(l.amount - t.allocated_amount, 0) AS unallocated_amount,
                       CASE
                           WHEN t.unresolved_count = 0 AND t.allocated_amount = l.amount
                           THEN 'complete'
                           ELSE 'review_required'
                       END AS allocation_status
                  FROM payment_ledger l
                  JOIN allocation_totals t ON t.ledger_id = l.id
            )
            UPDATE payment_ledger l
               SET contract_allocated_amount = d.allocated_amount,
                   contract_unallocated_amount = d.unallocated_amount,
                   contract_allocation_status = d.allocation_status
              FROM desired d
             WHERE d.ledger_id = l.id
               AND (
                    l.contract_allocated_amount IS DISTINCT FROM d.allocated_amount
                 OR l.contract_unallocated_amount IS DISTINCT FROM d.unallocated_amount
                 OR l.contract_allocation_status IS DISTINCT FROM d.allocation_status
               )
            """
        )
        self.env.cr.execute(
            """
            UPDATE payment_ledger_allocation a
               SET payment_request_id = l.payment_request_id,
                   project_id = r.project_id,
                   company_id = r.company_id,
                   currency_id = r.currency_id
              FROM payment_ledger l
              JOIN payment_request r ON r.id = l.payment_request_id
             WHERE a.ledger_id = l.id
               AND (
                    a.payment_request_id IS DISTINCT FROM l.payment_request_id
                 OR a.project_id IS DISTINCT FROM r.project_id
                 OR a.company_id IS DISTINCT FROM r.company_id
                 OR a.currency_id IS DISTINCT FROM r.currency_id
               )
            """
        )
