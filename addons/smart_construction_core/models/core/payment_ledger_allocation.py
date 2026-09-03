# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import AccessError

_PAYMENT_LEDGER_ALLOCATION_AUTHORITY_TOKEN = object()


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
        ondelete="restrict",
        readonly=True,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="公司",
        ondelete="restrict",
        readonly=True,
        index=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="币种",
        ondelete="restrict",
        readonly=True,
    )
    normalization_state = fields.Selection(
        [
            ("normalized", "标准事实"),
            ("legacy_observed_identity", "历史冻结身份"),
            ("legacy_unresolved_identity", "历史身份待确认"),
        ],
        string="身份状态",
        required=True,
        default="normalized",
        readonly=True,
        index=True,
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
        (
            "canonical_identity_complete",
            "CHECK(normalization_state = 'legacy_unresolved_identity' OR "
            "(project_id IS NOT NULL AND company_id IS NOT NULL AND currency_id IS NOT NULL))",
            "标准或历史可确认付款分摊必须具备完整的项目、公司和币种身份。",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        if (
            not self.env.su
            or self.env.context.get("sc_payment_ledger_allocation_authority_token")
            is not _PAYMENT_LEDGER_ALLOCATION_AUTHORITY_TOKEN
        ):
            raise AccessError(_("付款台账合同分摊只能由受控付款事实服务生成。"))
        ledger_ids = [vals.get("ledger_id") for vals in vals_list if vals.get("ledger_id")]
        ledgers = self.env["payment.ledger"].browse(ledger_ids).exists()
        ledgers_by_id = {ledger.id: ledger for ledger in ledgers}
        frozen_values = []
        for incoming_vals in vals_list:
            vals = dict(incoming_vals)
            ledger = ledgers_by_id.get(vals.get("ledger_id"))
            if (
                not ledger
                or ledger.normalization_state != "normalized"
                or not ledger.project_id
                or not ledger.company_id
                or not ledger.currency_id
            ):
                raise AccessError(_("付款台账合同分摊必须从身份完整的付款台账冻结项目、公司与币种。"))
            vals.update(
                {
                    "project_id": ledger.project_id.id,
                    "company_id": ledger.company_id.id,
                    "currency_id": ledger.currency_id.id,
                    "normalization_state": "normalized",
                }
            )
            frozen_values.append(vals)
        return super().create(frozen_values)

    @api.model
    def _create_authoritative(self, vals_list):
        return self.sudo().with_context(
            sc_payment_ledger_allocation_authority_token=_PAYMENT_LEDGER_ALLOCATION_AUTHORITY_TOKEN
        ).create(vals_list)

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
                company_id, currency_id, normalization_state,
                allocation_key, create_uid, create_date, write_uid, write_date
            )
            SELECT l.id, l.payment_request_id, NULL, r.contract_id, r.settlement_id, NULL,
                   l.amount, l.amount, 'allocated', 'direct_contract',
                   l.project_id, l.company_id, l.currency_id, l.normalization_state,
                   'backfill:direct', 1, NOW(), 1, NOW()
              FROM payment_ledger l
              JOIN payment_request r ON r.id = l.payment_request_id
              JOIN construction_contract c ON c.id = r.contract_id
             WHERE r.contract_id IS NOT NULL
               AND (r.project_id IS NULL OR c.project_id = r.project_id)
               AND (r.company_id IS NULL OR c.company_id = r.company_id)
               AND (r.currency_id IS NULL OR c.currency_id = r.currency_id)
               AND l.normalization_state IN ('normalized', 'legacy_observed_identity')
               AND l.project_id = c.project_id
               AND l.company_id = c.company_id
               AND l.currency_id = c.currency_id
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
                company_id, currency_id, normalization_state,
                allocation_key, create_uid, create_date, write_uid, write_date
            )
            SELECT l.id, l.payment_request_id, NULL, NULL, r.settlement_id, NULL,
                   0, 0, 'unresolved_global', 'historical_backfill_unresolved',
                   l.project_id, l.company_id, l.currency_id,
                   COALESCE(l.normalization_state, 'legacy_unresolved_identity'),
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
            UPDATE payment_ledger_allocation allocation
               SET payment_request_id = ledger.payment_request_id
              FROM payment_ledger ledger
             WHERE allocation.ledger_id = ledger.id
               AND allocation.payment_request_id IS NULL
            """
        )
