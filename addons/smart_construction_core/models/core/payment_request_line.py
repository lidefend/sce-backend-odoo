# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class PaymentRequestLine(models.Model):
    _name = "payment.request.line"
    _description = "Payment Request Line"
    _inherit = ["sc.delete.guard.mixin"]
    _order = "request_id desc, sequence asc, id asc"

    request_id = fields.Many2one(
        "payment.request",
        string="付款申请",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(string="序号", default=10, index=True)
    legacy_line_id = fields.Char(string="历史明细ID", required=True, copy=False, index=True)
    legacy_parent_id = fields.Char(string="历史父单ID", required=True, copy=False, index=True)
    legacy_supplier_contract_id = fields.Char(string="历史供应合同ID", copy=False)
    source_document_no = fields.Char(string="来源单号")
    source_line_type = fields.Char(string="来源类型")
    source_counterparty_text = fields.Char(string="来源往来方")
    source_contract_no = fields.Char(string="来源合同号")
    project_id = fields.Many2one(
        "project.project",
        string="项目",
        related="request_id.project_id",
        store=True,
        readonly=True,
        index=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="往来单位",
        related="request_id.partner_id",
        store=True,
        readonly=True,
        index=True,
    )
    contract_id = fields.Many2one(
        "construction.contract",
        string="供应合同",
        index=True,
    )
    settlement_id = fields.Many2one(
        "sc.settlement.order",
        string="结算单",
        index=True,
        ondelete="set null",
        help="历史付款申请明细关联的结算单；用于保留一张付款申请对应多张结算单的历史事实。",
    )
    settlement_line_id = fields.Many2one(
        "sc.settlement.order.line",
        string="结算行",
        index=True,
        ondelete="set null",
        help="引入的结算单明细行；用于结算行级已申请/剩余金额追踪与从结算单追溯资金执行情况。",
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="币种",
        related="request_id.currency_id",
        store=True,
        readonly=True,
    )
    amount = fields.Monetary(string="明细金额", currency_field="currency_id", required=True)
    paid_before_amount = fields.Monetary(string="历史已付", currency_field="currency_id")
    remaining_amount = fields.Monetary(string="历史未付", currency_field="currency_id")
    current_pay_amount = fields.Monetary(string="本次申请", currency_field="currency_id")
    note = fields.Text(string="备注")
    import_batch = fields.Char(string="导入批次", copy=False)
    active = fields.Boolean(default=True)
    attachment_count = fields.Integer(string="附件数量", compute="_compute_attachment_count")

    def _compute_attachment_count(self):
        grouped = {}
        if self.ids:
            data = self.env["ir.attachment"].sudo().read_group(
                [("res_model", "=", self._name), ("res_id", "in", self.ids)],
                ["res_id"],
                ["res_id"],
            )
            grouped = {int(row["res_id"]): int(row.get("__count", row.get("res_id_count", 0))) for row in data}
        for rec in self:
            rec.attachment_count = grouped.get(rec.id, 0)

    @api.constrains("request_id", "settlement_id", "contract_id", "active")
    def _check_payment_basis_relation(self):
        execution_model = self.env["sc.payment.execution"]
        for request in self.mapped("request_id").filtered(
            lambda rec: rec.type == "pay"
        ):
            execution_model._payment_basis_contracts(request)
            executions = execution_model.search(
                [("payment_request_id", "=", request.id)]
            )
            for execution in executions:
                execution._normalize_payment_relation_values({}, current=execution)

    def action_open_attachments(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "附件",
            "res_model": "ir.attachment",
            "view_mode": "tree,form",
            "domain": [("res_model", "=", self._name), ("res_id", "=", self.id)],
            "context": {"default_res_model": self._name, "default_res_id": self.id, "create": False},
            "target": "current",
        }

    @api.model
    def _lock_allocation_basis_requests(self, request_ids):
        """Serialize basis changes with request workflow transitions."""
        request_ids = sorted({int(request_id) for request_id in request_ids if request_id})
        if not request_ids:
            return self.env["payment.request"]
        self.env.cr.execute(
            """
            SELECT id
              FROM payment_request
             WHERE id IN %s
          ORDER BY id
               FOR UPDATE
            """,
            (tuple(request_ids),),
        )
        requests = self.env["payment.request"].browse(request_ids).exists()
        requests.invalidate_recordset(["state"])
        return requests

    @api.model
    def _assert_allocation_basis_requests_mutable(self, requests, operation):
        locked = requests.filtered(
            lambda request: request.state not in ("draft", "rejected", "cancel")
        )
        if locked:
            raise UserError(operation)

    @api.model_create_multi
    def create(self, vals_list):
        default_request_id = self.env.context.get("default_request_id")
        request_ids = {
            vals.get("request_id") or default_request_id
            for vals in vals_list
            if vals.get("request_id") or default_request_id
        }
        requests = self._lock_allocation_basis_requests(request_ids)
        self._assert_allocation_basis_requests_mutable(
            requests,
            "付款申请进入审批或执行后，不允许新增合同分摊依据明细；请撤回到允许状态后处理。",
        )
        return super().create(vals_list)

    def write(self, vals):
        allocation_basis_fields = {
            "request_id",
            "active",
            "contract_id",
            "settlement_id",
            "settlement_line_id",
            "amount",
            "current_pay_amount",
        }
        if allocation_basis_fields & set(vals):
            request_ids = set(self.mapped("request_id").ids)
            if "request_id" in vals and vals.get("request_id"):
                request_ids.add(vals["request_id"])
            requests = self._lock_allocation_basis_requests(request_ids)
            self._assert_allocation_basis_requests_mutable(
                requests,
                "付款申请进入审批或执行后，合同分摊依据不可修改；请撤回到允许状态后处理。",
            )
        return super().write(vals)

    def unlink(self):
        requests = self._lock_allocation_basis_requests(self.mapped("request_id").ids)
        self._assert_allocation_basis_requests_mutable(
            requests,
            "仅草稿、已驳回或已取消付款申请的明细允许删除。",
        )
        self._sc_raise_delete_blockers(action_label="删除付款申请明细")
        return super().unlink()
