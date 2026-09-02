# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.float_utils import float_compare


class PaymentLedger(models.Model):
    _name = "payment.ledger"
    _description = "Payment Ledger"
    _order = "paid_at desc, id desc"
    _sc_readonly_navigation_button_methods = {
        "action_open_payment_request",
        "action_open_settlement",
    }

    _sql_constraints = []

    payment_request_id = fields.Many2one(
        "payment.request",
        string="付款申请",
        required=True,
        ondelete="restrict",
        index=True,
    )
    payment_execution_id = fields.Many2one(
        "sc.payment.execution",
        string="来源付款登记",
        ondelete="restrict",
        index=True,
        readonly=True,
        copy=False,
    )
    project_id = fields.Many2one(
        "project.project",
        string="项目",
        related="payment_request_id.project_id",
        store=True,
        readonly=True,
    )
    operation_strategy = fields.Selection(
        related="project_id.operation_strategy",
        string="经营方式",
        store=True,
        readonly=True,
        index=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="往来单位",
        related="payment_request_id.partner_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="币种",
        related="payment_request_id.currency_id",
        store=True,
        readonly=True,
    )
    amount = fields.Monetary(
        string="付款金额",
        currency_field="currency_id",
        required=True,
    )
    paid_at = fields.Datetime(
        string="付款时间",
        default=fields.Datetime.now,
        required=True,
    )
    ref = fields.Char(string="外部参考")
    note = fields.Text(string="备注")
    state = fields.Selection(
        [("posted", "已入账"), ("reversed", "已冲销")],
        string="台账状态",
        default="posted",
        required=True,
        readonly=True,
        index=True,
    )
    reversed_at = fields.Datetime(string="冲销时间", readonly=True, copy=False)
    reversed_by_id = fields.Many2one(
        "res.users",
        string="冲销人",
        readonly=True,
        copy=False,
        ondelete="restrict",
    )
    reversal_execution_id = fields.Many2one(
        "sc.payment.execution",
        string="冲销来源付款登记",
        readonly=True,
        copy=False,
        ondelete="restrict",
    )
    reversal_reason = fields.Text(string="冲销原因", readonly=True, copy=False)
    fund_plan_allocation_ids = fields.One2many(
        "project.funding.actual.event.allocation",
        "actual_event_id",
        string="资金计划分配",
    )
    contract_allocation_ids = fields.One2many(
        "payment.ledger.allocation",
        "ledger_id",
        string="合同分摊事实",
        readonly=True,
    )
    contract_allocated_amount = fields.Monetary(
        string="合同已分摊金额",
        currency_field="currency_id",
        compute="_compute_contract_allocation_totals",
        store=True,
        readonly=True,
    )
    contract_unallocated_amount = fields.Monetary(
        string="合同待核对金额",
        currency_field="currency_id",
        compute="_compute_contract_allocation_totals",
        store=True,
        readonly=True,
    )
    contract_allocation_status = fields.Selection(
        [("complete", "分摊完整"), ("review_required", "待核对")],
        string="合同分摊状态",
        compute="_compute_contract_allocation_totals",
        store=True,
        readonly=True,
        index=True,
    )
    fund_plan_allocated_amount = fields.Monetary(
        string="计划已分配金额",
        currency_field="currency_id",
        compute="_compute_fund_plan_allocation_amounts",
        store=True,
        readonly=True,
    )
    fund_plan_unallocated_amount = fields.Monetary(
        string="计划未分配金额",
        currency_field="currency_id",
        compute="_compute_fund_plan_allocation_amounts",
        store=True,
        readonly=True,
    )

    @api.depends(
        "amount",
        "contract_allocation_ids.allocated_amount",
        "contract_allocation_ids.allocation_state",
    )
    def _compute_contract_allocation_totals(self):
        for ledger in self:
            allocated = sum(ledger.contract_allocation_ids.mapped("allocated_amount"))
            currency = ledger.currency_id
            allocated = currency.round(allocated) if currency else allocated
            unallocated = max((ledger.amount or 0.0) - allocated, 0.0)
            unallocated = currency.round(unallocated) if currency else unallocated
            unresolved = ledger.contract_allocation_ids.filtered(
                lambda row: row.allocation_state != "allocated"
            )
            exact_total = (
                float_compare(
                    allocated,
                    ledger.amount or 0.0,
                    precision_rounding=currency.rounding if currency else 0.01,
                )
                == 0
            )
            complete = bool(ledger.contract_allocation_ids) and not unresolved and exact_total
            ledger.contract_allocated_amount = allocated
            ledger.contract_unallocated_amount = unallocated
            ledger.contract_allocation_status = "complete" if complete else "review_required"

    @staticmethod
    def _allocation_contract_candidates(line):
        return (
            line.contract_id
            | line.settlement_line_id.contract_id
            | line.settlement_id.contract_id
        )

    def _allocation_contract_is_consistent(self, contract, request):
        return (
            contract
            and (not request.project_id or contract.project_id == request.project_id)
            and (not request.company_id or contract.company_id == request.company_id)
            and (not request.currency_id or contract.currency_id == request.currency_id)
        )

    def _rounded_ratio_allocations(self, basis_rows):
        """Largest-remainder allocation with deterministic line-id tie-breaking."""
        self.ensure_one()
        currency = self.currency_id
        precision = currency.rounding if currency and currency.rounding else 0.01
        basis_total = sum(item["basis_amount"] for item in basis_rows)
        raw_rows = []
        for item in basis_rows:
            raw = (self.amount or 0.0) * item["basis_amount"] / basis_total
            rounded = currency.round(raw) if currency else round(raw, 2)
            raw_rows.append({**item, "raw_amount": raw, "allocated_amount": rounded})
        delta = (self.amount or 0.0) - sum(item["allocated_amount"] for item in raw_rows)
        delta = currency.round(delta) if currency else round(delta, 2)
        units = int(round(delta / precision)) if precision else 0
        if units:
            reverse = units > 0
            ranked = sorted(
                raw_rows,
                key=lambda item: (
                    item["raw_amount"] - item["allocated_amount"],
                    -item["payment_request_line_id"],
                ),
                reverse=reverse,
            )
            step = precision if units > 0 else -precision
            for index in range(abs(units)):
                row = ranked[index % len(ranked)]
                row["allocated_amount"] = (
                    currency.round(row["allocated_amount"] + step)
                    if currency
                    else round(row["allocated_amount"] + step, 2)
                )
        return raw_rows

    def _unresolved_contract_allocation_values(self, contracts, reason_code):
        self.ensure_one()
        values = []
        for contract in contracts.sorted("id"):
            values.append(
                {
                    "ledger_id": self.id,
                    "contract_id": contract.id,
                    "basis_amount": 0.0,
                    "allocated_amount": 0.0,
                    "allocation_state": "unresolved_candidate",
                    "reason_code": reason_code,
                    "allocation_key": f"candidate:{contract.id}",
                }
            )
        if not values:
            values.append(
                {
                    "ledger_id": self.id,
                    "basis_amount": 0.0,
                    "allocated_amount": 0.0,
                    "allocation_state": "unresolved_global",
                    "reason_code": reason_code,
                    "allocation_key": "unresolved:global",
                }
            )
        return values

    def _prepare_contract_allocation_values(self):
        self.ensure_one()
        request = self.payment_request_id
        currency = self.currency_id or request.currency_id
        precision = currency.rounding if currency and currency.rounding else 0.01
        lines = request.outflow_line_ids.filtered("active").sorted("id")
        if lines:
            basis_rows = []
            candidate_contracts = self.env["construction.contract"]
            reason_code = False
            for line in lines:
                candidates = self._allocation_contract_candidates(line)
                candidate_contracts |= candidates
                if float_compare(
                    line.current_pay_amount or 0.0,
                    0.0,
                    precision_rounding=precision,
                ) <= 0:
                    reason_code = "invalid_basis_amount"
                    continue
                if len(candidates) != 1:
                    reason_code = "unresolved_contract"
                    continue
                contract = candidates
                if not self._allocation_contract_is_consistent(contract, request):
                    reason_code = (
                        "currency_mismatch"
                        if contract.currency_id != request.currency_id
                        else "project_company_mismatch"
                    )
                    continue
                basis_rows.append(
                    {
                        "payment_request_line_id": line.id,
                        "contract_id": contract.id,
                        "settlement_id": line.settlement_id.id or False,
                        "settlement_line_id": line.settlement_line_id.id or False,
                        "basis_amount": line.current_pay_amount,
                    }
                )
            basis_total = sum(item["basis_amount"] for item in basis_rows)
            if float_compare(
                basis_total,
                request.amount or 0.0,
                precision_rounding=precision,
            ):
                reason_code = reason_code or "basis_total_mismatch"
            if reason_code or len(basis_rows) != len(lines):
                return self._unresolved_contract_allocation_values(
                    candidate_contracts, reason_code or "unresolved_contract"
                )
            return [
                {
                    "ledger_id": self.id,
                    "payment_request_line_id": item["payment_request_line_id"],
                    "contract_id": item["contract_id"],
                    "settlement_id": item["settlement_id"],
                    "settlement_line_id": item["settlement_line_id"],
                    "basis_amount": item["basis_amount"],
                    "allocated_amount": item["allocated_amount"],
                    "allocation_state": "allocated",
                    "reason_code": "request_line_ratio",
                    "allocation_key": f"line:{item['payment_request_line_id']}",
                }
                for item in self._rounded_ratio_allocations(basis_rows)
            ]

        direct_contracts = request.contract_id
        if len(direct_contracts) == 1 and self._allocation_contract_is_consistent(
            direct_contracts, request
        ):
            return [
                {
                    "ledger_id": self.id,
                    "contract_id": direct_contracts.id,
                    "settlement_id": request.settlement_id.id or False,
                    "basis_amount": request.amount or self.amount,
                    "allocated_amount": self.amount,
                    "allocation_state": "allocated",
                    "reason_code": "direct_contract",
                    "allocation_key": f"direct:{direct_contracts.id}",
                }
            ]
        return self._unresolved_contract_allocation_values(
            direct_contracts,
            "unresolved_contract" if direct_contracts else "missing_basis",
        )

    def _ensure_contract_allocations(self):
        if not self:
            return
        self.env.cr.execute(
            "SELECT id FROM payment_ledger WHERE id IN %s FOR UPDATE",
            [tuple(sorted(self.ids))],
        )
        self.invalidate_recordset(["contract_allocation_ids"])
        Allocation = self.env["payment.ledger.allocation"].sudo().with_context(
            _sc_payment_ledger_allocation_build=True
        )
        values = []
        for ledger in self:
            if ledger.contract_allocation_ids:
                continue
            values.extend(ledger._prepare_contract_allocation_values())
        if values:
            Allocation.create(values)

    def init(self):
        """Keep every installment while preventing duplicate ledgering per execution."""
        self._cr.execute(
            "ALTER TABLE payment_ledger "
            "DROP CONSTRAINT IF EXISTS payment_ledger_uniq_payment_request_id"
        )
        self._cr.execute("DROP INDEX IF EXISTS payment_ledger_one_posted_per_request_idx")
        self._cr.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS payment_ledger_one_posted_per_execution_idx "
            "ON payment_ledger (payment_execution_id) "
            "WHERE payment_execution_id IS NOT NULL AND state = 'posted'"
        )

    @api.depends("amount", "fund_plan_allocation_ids.allocated_amount")
    def _compute_fund_plan_allocation_amounts(self):
        for record in self:
            allocated = sum(
                record.fund_plan_allocation_ids.mapped("allocated_amount")
            )
            record.fund_plan_allocated_amount = allocated
            record.fund_plan_unallocated_amount = (
                (record.amount or 0.0) - allocated
            )

    def _check_request_state(self, request):
        if not request or request.state != "approved":
            raise UserError("付款申请未处于已批准状态，不能登记付款。")
        basis_type = request.payment_basis_type or "none"
        if basis_type == "material_settlement":
            if request.material_settlement_id.state == "confirmed":
                return
            raise UserError("材料结算单未确认，不能登记付款。")
        if basis_type == "line_settlement":
            line_settlements = request._linked_settlement_orders()
            if line_settlements and all(
                settlement.state in ("approve", "done")
                for settlement in line_settlements
            ):
                return
            raise UserError("付款申请明细关联的结算单未全部审批，不能登记付款。")
        if basis_type == "contract":
            contract = request.contract_id
            if contract and contract.state != "cancel":
                return
            raise UserError("付款申请关联合同无效或已取消，不能登记付款。")
        if basis_type == "standard_settlement" and request.settlement_id.state not in ("approve", "done"):
            ICP = self.env["ir.config_parameter"].sudo()
            soft_gate = bool(self.env.context.get("payment_soft_gate"))
            force_block = str(
                ICP.get_param("sc.payment.force_block.p0_payment_settlement_not_ready", "False") or ""
            ).strip().lower() in ("1", "true", "yes", "on")
            if soft_gate and not force_block:
                return
            raise UserError("结算单未处于已审批状态，不能登记付款。")
        if basis_type == "standard_settlement":
            return
        raise UserError("付款申请缺少有效的合同或结算依据，不能登记付款。")

    def _check_amount(self):
        for rec in self:
            if (rec.amount or 0.0) <= 0.0:
                raise ValidationError(_("付款金额必须大于 0。"))

    def _check_overpay(self, exclude_ids=None):
        for rec in self:
            req = rec.payment_request_id
            if not req:
                continue
            rounding = req.currency_id.rounding if req.currency_id else 0.01
            domain = [
                ("payment_request_id", "=", req.id),
                ("state", "=", "posted"),
            ]
            if exclude_ids:
                domain.append(("id", "not in", exclude_ids))
            data = self.env["payment.ledger"].read_group(
                domain,
                ["amount:sum"],
                [],
            )
            paid_total = data[0].get("amount_sum", data[0].get("amount", 0.0)) if data else 0.0
            if float_compare(paid_total, req.amount or 0.0, precision_rounding=rounding) == 1:
                raise UserError("付款累计金额超过申请金额，禁止登记。")

    @api.model_create_multi
    def create(self, vals_list):
        audited_history_import = bool(
            self.env.context.get("sc_tenant_payload_import")
        )
        if not self.env.su:
            raise AccessError(_("付款台账只能由受控付款执行服务创建。"))
        if audited_history_import:
            self.env["sc.tenant.payload.adapter"].assert_import_operator()
        if not audited_history_import and not self.env.context.get("_sc_payment_ledger_internal_create"):
            raise UserError("请通过付款申请登记付款记录。")
        request_ids = []
        for vals in vals_list:
            if not audited_history_import and vals.get("state", "posted") != "posted":
                raise UserError("付款台账只能先登记为有效台账，再通过受控冲销改变状态。")
            req_id = vals.get("payment_request_id")
            if req_id:
                request_ids.append(req_id)
            request = self.env["payment.request"].browse(req_id)
            if not audited_history_import:
                self._check_request_state(request)
                execution_id = vals.get("payment_execution_id")
                if execution_id:
                    execution = self.env["sc.payment.execution"].browse(execution_id).exists()
                    if not execution or execution.payment_request_id != request:
                        raise UserError("付款台账的来源付款登记与付款申请不一致。")
        if request_ids:
            if len(request_ids) != len(set(request_ids)):
                raise UserError("同一付款申请不能生成多条付款台账。")
            self.env.cr.execute(
                "SELECT id FROM payment_request WHERE id IN %s FOR UPDATE",
                [tuple(sorted(set(request_ids)))],
            )
            for vals in vals_list:
                domain = [
                    ("payment_request_id", "=", vals.get("payment_request_id")),
                    ("state", "=", "posted"),
                    ("payment_execution_id", "=", vals.get("payment_execution_id") or False),
                ]
                if self.search(domain, limit=1):
                    raise UserError("该付款登记已存在付款台账，禁止重复生成。")
        records = super().create(vals_list)
        records._check_amount()
        if not audited_history_import:
            records._check_overpay()
        records._ensure_contract_allocations()
        return records

    def write(self, vals):
        if not self.env.su:
            raise AccessError(_("付款台账属于受控财务事实，不允许直接修改。"))
        if self.env.context.get("_sc_payment_ledger_internal_reversal"):
            allowed = {
                "state",
                "reversed_at",
                "reversed_by_id",
                "reversal_execution_id",
                "reversal_reason",
            }
            if set(vals) - allowed:
                raise UserError(_("冲销付款台账时不得修改原始付款事实。"))
            if vals.get("state") != "reversed":
                raise UserError(_("付款台账受控状态只能变更为已冲销。"))
            if any(record.state != "posted" for record in self):
                raise UserError(_("只有有效付款台账可以冲销。"))
            return super().write(vals)
        raise AccessError(
            _("付款台账是不可变现金事实，不允许修改；请通过受控冲销保留审计链。")
        )

    def unlink(self):
        raise UserError(_("付款台账属于财务事实，不允许删除；请通过受控冲销保留审计链。"))

    def action_reverse(self, execution, reason=None):
        self.ensure_one()
        if not self.env.su:
            raise AccessError(_("付款台账只能由受控付款执行服务冲销。"))
        if self.fund_plan_allocation_ids:
            raise UserError(
                _("已有资金计划分配的付款台账不能直接冲销，请先办理分配调整。")
            )
        if not execution or execution.payment_request_id != self.payment_request_id:
            raise UserError(_("冲销来源付款登记与付款台账不一致。"))
        if self.payment_execution_id and self.payment_execution_id != execution:
            raise UserError(_("只能由生成该台账的付款登记发起冲销。"))
        self.with_context(_sc_payment_ledger_internal_reversal=True).write(
            {
                "state": "reversed",
                "reversed_at": fields.Datetime.now(),
                "reversed_by_id": execution.env.user.id,
                "reversal_execution_id": execution.id,
                "reversal_reason": reason or _("付款登记撤销"),
            }
        )
        return self

    def action_open_payment_request(self):
        self.ensure_one()
        if not self.payment_request_id:
            raise UserError(_("当前付款台账没有关联付款申请。"))
        return {
            "type": "ir.actions.act_window",
            "name": _("付款申请"),
            "res_model": "payment.request",
            "res_id": self.payment_request_id.id,
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_project_id": self.project_id.id,
                "default_partner_id": self.partner_id.id,
            },
        }

    def action_open_settlement(self):
        self.ensure_one()
        material_settlement = self.payment_request_id.material_settlement_id
        if material_settlement:
            return {
                "type": "ir.actions.act_window",
                "name": _("材料结算"),
                "res_model": "sc.material.settlement",
                "res_id": material_settlement.id,
                "view_mode": "form",
                "target": "current",
                "context": {"default_project_id": self.project_id.id},
            }
        settlement = self.payment_request_id.settlement_id
        if not settlement:
            settlements = self.payment_request_id._linked_settlement_orders()
            if len(settlements) == 1:
                settlement = settlements
            elif settlements:
                raise UserError(_("当前付款申请关联多张结算单，请在付款申请明细中查看。"))
            else:
                raise UserError(_("当前付款台账没有关联结算单或材料结算单。"))
        return {
            "type": "ir.actions.act_window",
            "name": _("结算单"),
            "res_model": "sc.settlement.order",
            "res_id": settlement.id,
            "view_mode": "form",
            "target": "current",
            "context": {"default_project_id": self.project_id.id},
        }
