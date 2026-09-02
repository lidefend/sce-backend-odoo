# -*- coding: utf-8 -*-
import uuid

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.float_utils import float_compare


class ProjectFundingBaselineTransitionWizard(models.TransientModel):
    _name = "project.funding.baseline.transition.wizard"
    _description = "资金基线生命周期操作"

    baseline_id = fields.Many2one(
        "project.funding.baseline", string="资金基线", required=True, readonly=True
    )
    operation = fields.Selection(
        [("close", "关闭"), ("revision", "创建修订")],
        string="操作", required=True, readonly=True,
    )
    reason = fields.Text(string="原因", required=True)
    period_start = fields.Date(string="新控制期开始")
    period_end = fields.Date(string="新控制期结束")

    @api.model
    def default_get(self, field_list):
        values = super().default_get(field_list)
        baseline = self.env["project.funding.baseline"].browse(
            values.get("baseline_id")
        ).exists()
        if baseline and values.get("operation") == "revision":
            values.setdefault("period_start", baseline.period_start)
            values.setdefault("period_end", baseline.period_end)
        return values

    def action_apply(self):
        self.ensure_one()
        reason = (self.reason or "").strip()
        if not reason:
            raise ValidationError(_("必须填写可审计的操作原因。"))
        if self.operation == "close":
            self.baseline_id.action_close(reason)
            return {"type": "ir.actions.act_window_close"}
        if self.operation == "revision":
            if not self.period_start or not self.period_end:
                raise ValidationError(_("创建修订必须明确新控制期。"))
            revision = self.baseline_id.action_create_revision(
                reason, self.period_start, self.period_end
            )
            return {
                "type": "ir.actions.act_window",
                "name": _("资金基线修订"),
                "res_model": "project.funding.baseline",
                "res_id": revision.id,
                "view_mode": "form",
                "target": "current",
            }
        raise UserError(_("不支持的资金基线生命周期操作。"))


class PaymentLedgerFundingAllocationWizard(models.TransientModel):
    _name = "payment.ledger.funding.allocation.wizard"
    _description = "实际付款资金计划分配"

    ledger_id = fields.Many2one(
        "payment.ledger", string="付款台账", required=True, readonly=True
    )
    mode = fields.Selection(
        [("allocate", "新增分配"), ("correct", "纠正分配")],
        string="办理类型", required=True, readonly=True, default="allocate",
    )
    baseline_id = fields.Many2one(
        "project.funding.baseline", string="锁定资金基线",
        related="ledger_id.payment_request_id.funding_baseline_id", readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency", related="ledger_id.currency_id", readonly=True
    )
    amount = fields.Monetary(
        string="实付金额", related="ledger_id.amount", currency_field="currency_id",
        readonly=True,
    )
    unallocated_amount = fields.Monetary(
        string="待分配金额", related="ledger_id.fund_plan_unallocated_amount",
        currency_field="currency_id", readonly=True,
    )
    operation_key = fields.Char(
        string="操作幂等键", required=True, readonly=True,
        default=lambda self: uuid.uuid4().hex,
    )
    line_ids = fields.One2many(
        "payment.ledger.funding.allocation.wizard.line", "wizard_id",
        string="分配明细",
    )
    original_allocation_ids = fields.Many2many(
        "project.funding.actual.event.allocation",
        "payment_ledger_funding_correction_wizard_rel",
        "wizard_id", "allocation_id",
        string="待冲销原分配",
        domain="[('actual_event_id', '=', ledger_id), ('entry_type', '=', 'allocation'), ('normalization_state', '=', 'normalized'), ('reversed_by_id', '=', False)]",
    )
    reason = fields.Text(string="纠正原因")

    @api.model
    def default_get(self, field_list):
        values = super().default_get(field_list)
        ledger = self.env["payment.ledger"].browse(values.get("ledger_id")).exists()
        if not ledger:
            return values
        baseline = ledger.payment_request_id.funding_baseline_id
        if baseline and "line_ids" in field_list:
            mode = values.get("mode") or self.env.context.get("default_mode")
            candidate_lines = (
                baseline.line_ids
                if mode == "correct"
                else baseline.line_ids.filtered(lambda row: row.remaining_amount > 0)
            )
            values["line_ids"] = [
                (0, 0, {"plan_line_id": line.id, "available_amount": line.remaining_amount})
                for line in candidate_lines
            ]
        return values

    def action_confirm(self):
        self.ensure_one()
        if not self.env.su and not (
            self.env.user.has_group("smart_construction_core.group_sc_cap_finance_user")
            or self.env.user.has_group("smart_construction_core.group_sc_cap_finance_manager")
        ):
            raise AccessError(_("当前用户没有办理资金分配的权限。"))
        rounding = self.currency_id.rounding or 0.01
        specs = []
        for line in self.line_ids:
            if float_compare(line.amount, 0.0, precision_rounding=rounding) > 0:
                specs.append({"plan_line_id": line.plan_line_id.id, "amount": line.amount})
        if not specs:
            raise ValidationError(_("至少填写一条大于零的分配金额。"))
        if self.mode == "correct":
            if not (self.reason or "").strip():
                raise ValidationError(_("纠正分配必须填写可审计原因。"))
            allocations = self.ledger_id.action_reallocate_funding(
                self.original_allocation_ids.ids,
                specs,
                self.operation_key,
                self.reason,
            )
        else:
            allocations = self.ledger_id.action_allocate_funding(
                specs, self.operation_key
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("本次资金计划分配结果"),
            "res_model": "project.funding.actual.event.allocation",
            "view_mode": "tree,form",
            "domain": [("id", "in", allocations.ids)],
            "target": "current",
        }


class PaymentLedgerFundingAllocationWizardLine(models.TransientModel):
    _name = "payment.ledger.funding.allocation.wizard.line"
    _description = "实际付款资金计划分配明细"
    _order = "id"

    wizard_id = fields.Many2one(
        "payment.ledger.funding.allocation.wizard", required=True, ondelete="cascade"
    )
    plan_line_id = fields.Many2one(
        "project.funding.baseline.line", string="资金计划明细",
        required=True, readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency", related="wizard_id.currency_id", readonly=True
    )
    available_amount = fields.Monetary(
        string="计划可分配余额", currency_field="currency_id", readonly=True
    )
    amount = fields.Monetary(
        string="本次分配金额", currency_field="currency_id", default=0.0
    )
