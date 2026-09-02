# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.float_utils import float_compare

from .funding_baseline import _FUNDING_ALLOCATION_TOKEN

_PAYMENT_LEDGER_AUTHORITY_TOKEN = object()


class PaymentLedger(models.Model):
    _name = "payment.ledger"
    _description = "Payment Ledger"
    _order = "paid_at desc, id desc"
    _sc_readonly_navigation_button_methods = {
        "action_open_payment_request",
        "action_open_settlement",
        "action_open_funding_allocation_wizard",
    }

    _sql_constraints = [
        (
            "canonical_identity_complete",
            "CHECK(normalization_state = 'legacy_unresolved_identity' OR "
            "(project_id IS NOT NULL AND company_id IS NOT NULL AND partner_id IS NOT NULL "
            "AND currency_id IS NOT NULL AND operation_strategy IS NOT NULL))",
            "标准或历史可确认付款台账必须具备完整的项目、公司、往来单位、币种和经营方式身份。",
        ),
    ]

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
    operation_strategy = fields.Selection(
        [("direct", "公司直营"), ("joint", "联营项目")],
        string="经营方式",
        readonly=True,
        index=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="往来单位",
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
        Allocation = self.env["payment.ledger.allocation"]
        values = []
        for ledger in self:
            if ledger.contract_allocation_ids:
                continue
            values.extend(ledger._prepare_contract_allocation_values())
        if values:
            Allocation._create_authoritative(values)

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

    @api.depends(
        "amount",
        "fund_plan_allocation_ids.effective_amount",
        "fund_plan_allocation_ids.normalization_state",
        "normalization_state",
    )
    def _compute_fund_plan_allocation_amounts(self):
        totals = {}
        if self.ids:
            rows = self.env["project.funding.actual.event.allocation"].read_group(
                [
                    ("actual_event_id", "in", self.ids),
                    ("normalization_state", "in", ["normalized", "legacy_unresolved_period"]),
                    ("actual_event_id.normalization_state", "in", ["normalized", "legacy_observed_identity"]),
                ],
                ["effective_amount:sum"],
                ["actual_event_id"],
            )
            totals = {
                row["actual_event_id"][0]: row.get(
                    "effective_amount_sum", row.get("effective_amount", 0.0)
                )
                for row in rows
            }
        for record in self:
            allocated = totals.get(record.id, 0.0)
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
        requests = self.mapped("payment_request_id")
        if not requests:
            return
        del exclude_ids
        requests._assert_unambiguous_posted_payment_history()
        paid_by_request = requests._canonical_payment_paid_amount_map()
        for req in requests:
            rounding = req.currency_id.rounding if req.currency_id else 0.01
            paid_total = paid_by_request.get(req.id, 0.0)
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
        if (
            not audited_history_import
            and self.env.context.get("sc_payment_ledger_authority_token")
            is not _PAYMENT_LEDGER_AUTHORITY_TOKEN
        ):
            raise UserError("请通过付款申请登记付款记录。")
        request_ids = [vals.get("payment_request_id") for vals in vals_list if vals.get("payment_request_id")]
        requests = self.env["payment.request"].browse(request_ids).exists()
        requests_by_id = {request.id: request for request in requests}
        execution_ids = [vals.get("payment_execution_id") for vals in vals_list if vals.get("payment_execution_id")]
        executions = self.env["sc.payment.execution"].browse(execution_ids).exists()
        executions_by_id = {execution.id: execution for execution in executions}
        frozen_vals_list = []
        for incoming_vals in vals_list:
            vals = dict(incoming_vals)
            if not audited_history_import and vals.get("state", "posted") != "posted":
                raise UserError("付款台账只能先登记为有效台账，再通过受控冲销改变状态。")
            req_id = vals.get("payment_request_id")
            request = requests_by_id.get(req_id, self.env["payment.request"])
            if not request:
                raise UserError("付款台账必须关联有效的付款申请。")
            if audited_history_import:
                identity_state = vals.get("normalization_state") or "legacy_unresolved_identity"
                if identity_state not in {
                    "legacy_observed_identity",
                    "legacy_unresolved_identity",
                }:
                    raise UserError("历史付款台账必须显式分类为历史冻结身份或历史身份待确认。")
                if identity_state == "legacy_observed_identity" and not all(
                    vals.get(field_name)
                    for field_name in (
                        "project_id",
                        "company_id",
                        "partner_id",
                        "currency_id",
                        "operation_strategy",
                    )
                ):
                    raise UserError("历史冻结身份付款台账必须提供完整且有证据的身份快照。")
                vals["normalization_state"] = identity_state
            else:
                if (
                    not request.project_id
                    or not request.project_id.company_id
                    or not request.partner_id
                    or not request.currency_id
                    or not request.project_id.operation_strategy
                ):
                    raise UserError("付款台账必须从身份完整的付款申请冻结项目、公司、往来单位、币种与经营方式。")
                vals.update(
                    {
                        "project_id": request.project_id.id,
                        "company_id": request.project_id.company_id.id,
                        "partner_id": request.partner_id.id,
                        "currency_id": request.currency_id.id,
                        "operation_strategy": request.project_id.operation_strategy,
                        "normalization_state": "normalized",
                    }
                )
                self._check_request_state(request)
                execution_id = vals.get("payment_execution_id")
                if execution_id:
                    execution = executions_by_id.get(execution_id, self.env["sc.payment.execution"])
                    if not execution or execution.payment_request_id != request:
                        raise UserError("付款台账的来源付款登记与付款申请不一致。")
            frozen_vals_list.append(vals)
        if request_ids:
            if len(request_ids) != len(set(request_ids)):
                raise UserError("同一付款申请不能生成多条付款台账。")
            self.env.cr.execute(
                "SELECT id FROM payment_request WHERE id IN %s FOR UPDATE",
                [tuple(sorted(set(request_ids)))],
            )
            if not audited_history_import:
                requests._assert_unambiguous_posted_payment_history()
            existing = self.search(
                [
                    ("payment_request_id", "in", request_ids),
                    ("state", "=", "posted"),
                ]
            )
            existing_keys = {
                (ledger.payment_request_id.id, ledger.payment_execution_id.id or False)
                for ledger in existing
            }
            for vals in frozen_vals_list:
                key = (vals.get("payment_request_id"), vals.get("payment_execution_id") or False)
                if key in existing_keys:
                    raise UserError("该付款登记已存在付款台账，禁止重复生成。")
        records = super().create(frozen_vals_list)
        records._check_amount()
        if not audited_history_import:
            records._check_overpay()
            records._ensure_contract_allocations()
        return records

    @api.model
    def _create_authoritative(self, vals_list):
        return self.sudo().with_context(
            sc_payment_ledger_authority_token=_PAYMENT_LEDGER_AUTHORITY_TOKEN
        ).create(vals_list)

    def _lock_funding_authority(self, lines):
        """Lock every funding authority tier once, in the repository-wide order."""
        request_ids = sorted(set(self.mapped("payment_request_id").ids))
        project_ids = sorted(set(self.mapped("project_id").ids))
        baseline_ids = sorted(set(lines.mapped("baseline_id").ids))
        line_ids = sorted(set(lines.ids))
        ledger_ids = sorted(set(self.ids))
        for table, ids in (
            ("payment_request", request_ids),
            ("project_project", project_ids),
            ("project_funding_baseline", baseline_ids),
            ("project_funding_baseline_line", line_ids),
            ("payment_ledger", ledger_ids),
        ):
            if ids:
                self.env.cr.execute(
                    f"SELECT id FROM {table} WHERE id = ANY(%s) ORDER BY id FOR UPDATE",
                    [ids],
                )
        self.invalidate_recordset(["state", "amount", "payment_request_id", "project_id"])
        lines.invalidate_recordset()
        lines.mapped("baseline_id").invalidate_recordset()

    def _caller_visible_funding_ledger(self):
        relation_ids = self.ids
        if len(relation_ids) != 1:
            raise AccessError(_("付款台账不存在或当前用户无权访问。"))
        ledger = self.env["payment.ledger"].search(
            [("id", "=", relation_ids[0])], limit=1
        )
        if not ledger:
            raise AccessError(_("付款台账不存在或当前用户无权访问。"))
        return ledger

    def action_open_funding_allocation_wizard(self):
        self = self._caller_visible_funding_ledger()
        mode = self.env.context.get("funding_allocation_mode", "allocate")
        if not self.env.su and not (
            self.env.user.has_group("smart_construction_core.group_sc_cap_finance_user")
            or self.env.user.has_group("smart_construction_core.group_sc_cap_finance_manager")
        ):
            raise AccessError(_("当前用户没有办理资金分配的权限。"))
        if self.state != "posted":
            raise UserError(_("只有有效付款台账可以进行资金计划分配。"))
        if self.normalization_state != "normalized":
            raise UserError(_("只有身份完整的标准付款台账可以进行资金计划分配。"))
        baseline = self.payment_request_id.funding_baseline_id
        if not baseline or baseline.normalization_state != "normalized":
            raise UserError(_("付款申请未绑定标准化资金基线版本。"))
        if mode == "correct" and not self.env.su and not self.env.user.has_group(
            "smart_construction_core.group_sc_cap_finance_manager"
        ):
            raise AccessError(_("只有财务经理可以纠正资金计划分配。"))
        return {
            "type": "ir.actions.act_window",
            "name": _("分配实际付款至资金计划"),
            "res_model": "payment.ledger.funding.allocation.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_ledger_id": self.id, "default_mode": mode},
        }

    def action_allocate_funding(self, lines, operation_key):
        """Append idempotent authoritative allocation facts for one posted ledger.

        ``lines`` is a list of ``{plan_line_id, amount}``; direct journal CRUD is
        deliberately unavailable to RPC callers.
        """
        self = self._caller_visible_funding_ledger()
        if not operation_key:
            raise ValidationError(_("资金分配必须提供不可变操作幂等键。"))
        if not self.env.su and not self.env.user.has_group(
            "smart_construction_core.group_sc_cap_finance_user"
        ) and not self.env.user.has_group(
            "smart_construction_core.group_sc_cap_finance_manager"
        ):
            raise AccessError(_("当前用户没有办理资金分配的权限。"))
        specs = list(lines or [])
        if not specs:
            raise ValidationError(_("资金分配至少需要一条计划明细。"))
        line_ids = [int(item.get("plan_line_id") or 0) for item in specs]
        if len(line_ids) != len(set(line_ids)):
            raise ValidationError(_("同一操作中每条资金计划明细只能出现一次。"))
        plan_lines = self.env["project.funding.baseline.line"].search(
            [("id", "in", line_ids)]
        )
        if len(plan_lines) != len(set(line_ids)):
            raise AccessError(_("计划明细不存在或当前用户无权访问。"))
        self._lock_funding_authority(plan_lines)
        request = self.payment_request_id
        baseline = request.funding_baseline_id
        if self.state != "posted":
            raise UserError(_("只有有效付款台账可以进行资金计划分配。"))
        if self.normalization_state != "normalized":
            raise UserError(_("只有身份完整的标准付款台账可以进行资金计划分配。"))
        if not baseline or baseline.normalization_state != "normalized":
            raise UserError(_("付款申请未绑定标准化资金基线版本。"))
        if any(line.baseline_id.id != baseline.id for line in plan_lines):
            raise ValidationError(_("资金分配明细必须属于付款申请锁定的资金基线版本。"))
        if (
            baseline.project_id.id != self.project_id.id
            or baseline.company_id.id != self.project_id.company_id.id
            or baseline.currency_id.id != self.currency_id.id
        ):
            raise ValidationError(_("资金基线与付款台账的项目、公司或币种不一致。"))
        paid_date = fields.Date.to_date(self.paid_at)
        if not paid_date or not (
            baseline.period_start <= paid_date <= baseline.period_end
        ):
            raise ValidationError(_("实际付款日期必须落在申请锁定的资金基线控制期内。"))
        Allocation = self.env["project.funding.actual.event.allocation"].sudo()
        operation_namespace = f"allocation:{operation_key}"
        keys = [f"{operation_namespace}:{line_id}" for line_id in line_ids]
        rounding = self.currency_id.rounding or 0.01
        amounts_by_line = {}
        for spec, line_id in zip(specs, line_ids):
            amount = float(spec.get("amount") or 0.0)
            if float_compare(amount, 0.0, precision_rounding=rounding) <= 0:
                raise ValidationError(_("资金分配金额必须大于 0。"))
            amounts_by_line[line_id] = amount
        existing = Allocation.search([("operation_key", "=", operation_namespace)])
        if existing:
            existing_by_line = {row.plan_line_id.id: row for row in existing}
            payload_matches = (
                len(existing) == len(amounts_by_line)
                and set(existing_by_line) == set(amounts_by_line)
                and all(
                    row.entry_type == "allocation"
                    and row.actual_event_id == self
                    and row.normalization_state == "normalized"
                    and float_compare(
                        row.allocated_amount,
                        amounts_by_line[line_id],
                        precision_rounding=rounding,
                    ) == 0
                    and float_compare(
                        row.effective_amount,
                        amounts_by_line[line_id],
                        precision_rounding=rounding,
                    ) == 0
                    for line_id, row in existing_by_line.items()
                )
            )
            if not payload_matches:
                raise UserError(_("资金分配幂等键已被不同完整业务载荷占用。"))
            return existing
        pending = []
        pending_line = {}
        for line_id, key in zip(line_ids, keys):
            amount = amounts_by_line[line_id]
            pending_line[line_id] = pending_line.get(line_id, 0.0) + amount
            effective_at = self.paid_at or fields.Datetime.now()
            pending.append({
                "plan_line_id": line_id,
                "actual_event_id": self.id,
                "allocated_amount": amount,
                "effective_amount": amount,
                "operation_key": operation_namespace,
                "allocation_key": key,
                "entry_type": "allocation",
                "effective_at": effective_at,
                "effective_date": fields.Date.to_date(effective_at),
                "normalization_state": "normalized",
            })
        if pending:
            current_rows = Allocation.read_group(
                [("normalization_state", "=", "normalized"), ("plan_line_id", "in", line_ids)],
                ["effective_amount:sum"], ["plan_line_id"],
            )
            current_line = {
                row["plan_line_id"][0]: row.get(
                    "effective_amount_sum", row.get("effective_amount", 0.0)
                )
                for row in current_rows
            }
            for line in plan_lines:
                if float_compare(
                    current_line.get(line.id, 0.0) + pending_line.get(line.id, 0.0),
                    line.planned_amount,
                    precision_rounding=self.currency_id.rounding or 0.01,
                ) > 0:
                    raise ValidationError(_("资金计划明细累计分配不得超过计划金额。"))
            grouped_totals = Allocation.read_group(
                [("normalization_state", "=", "normalized"), "|",
                 ("actual_event_id", "=", self.id), ("baseline_id", "=", baseline.id)],
                ["effective_amount:sum", "actual_event_id", "baseline_id"],
                ["actual_event_id", "baseline_id"],
                lazy=False,
            )
            event_total = sum(
                row.get("effective_amount_sum", row.get("effective_amount", 0.0))
                for row in grouped_totals
                if row.get("actual_event_id") and row["actual_event_id"][0] == self.id
            ) + sum(item["effective_amount"] for item in pending)
            baseline_total = sum(
                row.get("effective_amount_sum", row.get("effective_amount", 0.0))
                for row in grouped_totals
                if row.get("baseline_id") and row["baseline_id"][0] == baseline.id
            ) + sum(item["effective_amount"] for item in pending)
            rounding = self.currency_id.rounding or 0.01
            if float_compare(event_total, self.amount, precision_rounding=rounding) > 0:
                raise ValidationError(_("付款台账累计分配不得超过实付金额。"))
            if float_compare(baseline_total, baseline.total_amount, precision_rounding=rounding) > 0:
                raise ValidationError(_("资金基线累计分配不得超过资金上限。"))
            created = Allocation.with_context(
                _sc_funding_allocation_token=_FUNDING_ALLOCATION_TOKEN
            ).create(pending)
            return created
        return Allocation

    @staticmethod
    def _grouped_effective_amount(Allocation, domain):
        rows = Allocation.read_group(domain, ["effective_amount:sum"], [])
        if not rows:
            return 0.0
        return rows[0].get(
            "effective_amount_sum", rows[0].get("effective_amount", 0.0)
        ) or 0.0

    def _append_funding_reversals(self, originals, operation_key, reason):
        Allocation = self.env["project.funding.actual.event.allocation"].sudo()
        operation_namespace = f"reversal:{operation_key}"
        keys = [f"{operation_namespace}:{original.id}" for original in originals]
        existing = Allocation.search([("operation_key", "=", operation_namespace)])
        reason_text = (reason or "").strip()
        rounding = self.currency_id.rounding or 0.01
        if existing:
            existing_by_original = {
                record.reverses_id.id: record
                for record in existing
                if record.reverses_id
            }
            payload_matches = (
                len(existing) == len(originals)
                and set(existing_by_original) == set(originals.ids)
                and all(
                    reversal.entry_type == "reversal"
                    and reversal.actual_event_id == self
                    and reversal.plan_line_id == original.plan_line_id
                    and reversal.normalization_state == "normalized"
                    and (reversal.reason or "").strip() == reason_text
                    and float_compare(
                        reversal.allocated_amount,
                        original.allocated_amount,
                        precision_rounding=rounding,
                    ) == 0
                    and float_compare(
                        reversal.effective_amount,
                        -original.allocated_amount,
                        precision_rounding=rounding,
                    ) == 0
                    for original in originals
                    for reversal in [existing_by_original.get(original.id)]
                    if reversal
                )
                and len(existing_by_original) == len(originals)
            )
            if not payload_matches:
                raise UserError(_("资金冲销幂等键已被不同完整业务载荷占用。"))
            return existing
        values = []
        for original, key in zip(originals, keys):
            effective_at = fields.Datetime.now()
            values.append({
                "plan_line_id": original.plan_line_id.id,
                "actual_event_id": self.id,
                "allocated_amount": original.allocated_amount,
                "effective_amount": -original.allocated_amount,
                "operation_key": operation_namespace,
                "allocation_key": key,
                "entry_type": "reversal",
                "reverses_id": original.id,
                "effective_at": effective_at,
                "effective_date": fields.Date.to_date(effective_at),
                "normalization_state": "normalized",
                "reason": reason_text,
            })
        if values:
            existing = Allocation.with_context(
                _sc_funding_allocation_token=_FUNDING_ALLOCATION_TOKEN
            ).create(values)
        reverse_by_original = {
            reversal.reverses_id.id: reversal.id
            for reversal in existing
            if reversal.reverses_id
        }
        if reverse_by_original:
            self.env.cr.execute(
                """
                UPDATE project_funding_actual_event_allocation AS original
                   SET reversed_by_id = links.reversal_id
                  FROM unnest(%s::integer[], %s::integer[])
                       AS links(original_id, reversal_id)
                 WHERE original.id = links.original_id
                   AND original.reversed_by_id IS NULL
                """,
                [list(reverse_by_original), list(reverse_by_original.values())],
            )
            originals.invalidate_recordset(["reversed_by_id"])
        return existing

    def action_reallocate_funding(
        self, original_allocation_ids, lines, operation_key, reason
    ):
        self = self._caller_visible_funding_ledger()
        if not self.env.su and not self.env.user.has_group(
            "smart_construction_core.group_sc_cap_finance_manager"
        ):
            raise AccessError(_("只有财务经理可以纠正资金计划分配。"))
        if not operation_key or not (reason or "").strip():
            raise ValidationError(_("分配纠正必须提供幂等键和可审计原因。"))
        original_ids = sorted({int(item) for item in original_allocation_ids or []})
        if not original_ids or not lines:
            raise ValidationError(_("分配纠正必须选择原分配并填写新的分配明细。"))
        originals = self.env["project.funding.actual.event.allocation"].search([
            ("id", "in", original_ids),
            ("actual_event_id", "=", self.id),
            ("entry_type", "=", "allocation"),
            ("normalization_state", "=", "normalized"),
        ])
        if len(originals) != len(original_ids):
            raise AccessError(_("待纠正分配不存在或当前用户无权访问。"))
        replacement_ids = [int(item.get("plan_line_id") or 0) for item in (lines or [])]
        replacement_lines = self.env["project.funding.baseline.line"].search([
            ("id", "in", replacement_ids),
        ])
        if len(replacement_lines) != len(set(replacement_ids)):
            raise AccessError(_("纠正后的计划明细不存在或当前用户无权访问。"))
        all_lines = originals.mapped("plan_line_id") | replacement_lines
        self._lock_funding_authority(all_lines)
        originals = self.env["project.funding.actual.event.allocation"].search([
            ("id", "in", original_ids),
            ("actual_event_id", "=", self.id),
            ("entry_type", "=", "allocation"),
            ("normalization_state", "=", "normalized"),
        ])
        reversal_operation = f"reallocation:{operation_key}"
        expected_prefix = f"reversal:{reversal_operation}"
        for original in originals:
            if original.reversed_by_id and not original.reversed_by_id.allocation_key.startswith(
                f"{expected_prefix}:"
            ):
                raise UserError(_("所选分配已经由另一业务操作冲销。"))
        reversals = self._append_funding_reversals(
            originals, reversal_operation, (reason or "").strip()
        )
        replacements = self.action_allocate_funding(
            lines, f"reallocation:{operation_key}:replacement"
        )
        return reversals | replacements

    def _reverse_funding_allocations(self, execution, reason):
        self.ensure_one()
        Allocation = self.env["project.funding.actual.event.allocation"].sudo()
        baseline = self.payment_request_id.funding_baseline_id
        authority_lines = baseline.line_ids if baseline else self.env[
            "project.funding.baseline.line"
        ]
        self._lock_funding_authority(authority_lines)
        originals = Allocation.search([
            ("actual_event_id", "=", self.id),
            ("entry_type", "=", "allocation"),
            ("normalization_state", "=", "normalized"),
            ("reversed_by_id", "=", False),
        ])
        self._append_funding_reversals(
            originals, f"reverse:{execution.id}", reason
        )
        total = self._grouped_effective_amount(Allocation, [
            ("actual_event_id", "=", self.id),
            ("normalization_state", "=", "normalized"),
        ])
        if float_compare(total, 0.0, precision_rounding=self.currency_id.rounding or 0.01):
            raise ValidationError(_("付款冲销后资金计划分配净额必须为零。"))

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
        if not execution or execution.payment_request_id != self.payment_request_id:
            raise UserError(_("冲销来源付款登记与付款台账不一致。"))
        if self.payment_execution_id and self.payment_execution_id != execution:
            raise UserError(_("只能由生成该台账的付款登记发起冲销。"))
        self._reverse_funding_allocations(execution, reason or _("付款登记撤销"))
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
