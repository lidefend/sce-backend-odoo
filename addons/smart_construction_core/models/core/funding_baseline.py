# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.float_utils import float_compare


class ProjectFundingBaseline(models.Model):
    _name = "project.funding.baseline"
    _description = "Project Funding Baseline"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    project_id = fields.Many2one(
        "project.project",
        string="项目",
        required=True,
        index=True,
        ondelete="cascade",
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="币种",
        related="project_id.company_id.currency_id",
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="公司",
        related="project_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    total_amount = fields.Monetary(
        string="资金上限",
        currency_field="currency_id",
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "草稿"),
            ("active", "生效"),
            ("closed", "关闭"),
        ],
        string="状态",
        default="draft",
        index=True,
        required=True,
        tracking=True,
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "project_funding_baseline_attachment_rel",
        "baseline_id",
        "attachment_id",
        string="附件",
    )
    line_ids = fields.One2many(
        "project.funding.baseline.line",
        "baseline_id",
        string="资金计划明细",
        copy=True,
    )
    allocated_amount = fields.Monetary(
        string="已分配实际付款",
        currency_field="currency_id",
        compute="_compute_allocation_amounts",
        store=True,
        readonly=True,
    )
    remaining_amount = fields.Monetary(
        string="计划未分配余额",
        currency_field="currency_id",
        compute="_compute_allocation_amounts",
        store=True,
        readonly=True,
    )

    @api.depends("total_amount", "line_ids.allocated_amount")
    def _compute_allocation_amounts(self):
        for record in self:
            allocated = sum(record.line_ids.mapped("allocated_amount"))
            record.allocated_amount = allocated
            record.remaining_amount = (record.total_amount or 0.0) - allocated

    def _check_funding_ready(self, project):
        if not project.is_funding_ready():
            raise UserError("项目未满足资金承载条件，不能建立资金基准。")

    @api.model
    def _caller_visible_project(self, project_id):
        try:
            relation_id = int(project_id)
        except (TypeError, ValueError):
            relation_id = 0
        project = self.env["project.project"].search(
            [("id", "=", relation_id)],
            limit=1,
        )
        if not project:
            raise AccessError(_("项目不存在或当前用户无权访问。"))
        return project

    def _check_single_active(self, project, exclude_ids=None):
        domain = [
            ("project_id", "=", project.id),
            ("state", "=", "active"),
        ]
        if exclude_ids:
            domain.append(("id", "not in", exclude_ids))
        if self.search_count(domain):
            raise UserError("项目已存在生效中的资金基准。")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            project_id = vals.get("project_id")
            if project_id:
                project = self._caller_visible_project(project_id)
                self._check_funding_ready(project)
                if vals.get("state") == "active":
                    self._check_single_active(project)
        return super().create(vals_list)

    def write(self, vals):
        allocations = self.line_ids.allocation_ids
        state_to_active = vals.get("state") == "active"
        project_id = vals.get("project_id")
        target_project = (
            self._caller_visible_project(project_id) if project_id else False
        )
        for rec in self:
            project = target_project or rec.project_id
            if project:
                if "project_id" in vals or "state" in vals:
                    self._check_funding_ready(project)
                if state_to_active or (project_id and rec.state == "active"):
                    self._check_single_active(project, exclude_ids=rec.ids)
        result = super().write(vals)
        allocations._validate_relation_state()
        return result

    def unlink(self):
        if self.line_ids.allocation_ids:
            raise UserError(
                _("已有实际付款分配的资金计划不能删除，请保留审计关系。")
            )
        return super().unlink()


class ProjectFundingBaselineLine(models.Model):
    _name = "project.funding.baseline.line"
    _description = "Project Funding Baseline Line"
    _order = "sequence, id"

    baseline_id = fields.Many2one(
        "project.funding.baseline",
        string="资金计划",
        required=True,
        index=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(string="顺序", default=10)
    name = fields.Char(string="预算科目", required=True, index=True)
    planned_amount = fields.Monetary(
        string="计划金额",
        currency_field="currency_id",
        required=True,
    )
    project_id = fields.Many2one(
        "project.project",
        string="项目",
        related="baseline_id.project_id",
        store=True,
        readonly=True,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="公司",
        related="baseline_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="币种",
        related="baseline_id.currency_id",
        store=True,
        readonly=True,
    )
    allocation_ids = fields.One2many(
        "project.funding.actual.event.allocation",
        "plan_line_id",
        string="实际付款分配",
    )
    allocated_amount = fields.Monetary(
        string="已分配金额",
        currency_field="currency_id",
        compute="_compute_allocation_amounts",
        store=True,
        readonly=True,
    )
    remaining_amount = fields.Monetary(
        string="未分配余额",
        currency_field="currency_id",
        compute="_compute_allocation_amounts",
        store=True,
        readonly=True,
    )

    _sql_constraints = [
        (
            "planned_amount_positive",
            "CHECK(planned_amount > 0)",
            "资金计划明细金额必须大于 0。",
        ),
    ]

    @api.depends("planned_amount", "allocation_ids.allocated_amount")
    def _compute_allocation_amounts(self):
        for record in self:
            allocated = sum(record.allocation_ids.mapped("allocated_amount"))
            record.allocated_amount = allocated
            record.remaining_amount = (record.planned_amount or 0.0) - allocated

    @api.constrains("planned_amount")
    def _check_planned_amount(self):
        for record in self:
            if float_compare(
                record.planned_amount or 0.0,
                0.0,
                precision_rounding=record.currency_id.rounding or 0.01,
            ) <= 0:
                raise ValidationError(_("资金计划明细金额必须大于 0。"))

    def write(self, vals):
        allocations = self.allocation_ids
        result = super().write(vals)
        allocations._validate_relation_state()
        return result

    def unlink(self):
        if self.allocation_ids:
            raise UserError(
                _("已有实际付款分配的资金计划明细不能删除，请保留审计关系。")
            )
        return super().unlink()


class ProjectFundingActualEventAllocation(models.Model):
    _name = "project.funding.actual.event.allocation"
    _description = "Fund Plan Actual Payment Allocation"
    _order = "id desc"

    plan_line_id = fields.Many2one(
        "project.funding.baseline.line",
        string="资金计划明细",
        required=True,
        index=True,
        ondelete="restrict",
    )
    actual_event_id = fields.Many2one(
        "payment.ledger",
        string="实际付款事件",
        required=True,
        index=True,
        ondelete="restrict",
    )
    allocated_amount = fields.Monetary(
        string="分配金额",
        currency_field="currency_id",
        required=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="公司",
        related="actual_event_id.project_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    project_id = fields.Many2one(
        "project.project",
        string="项目",
        related="actual_event_id.project_id",
        store=True,
        readonly=True,
        index=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="币种",
        related="actual_event_id.currency_id",
        store=True,
        readonly=True,
    )

    _sql_constraints = [
        (
            "allocated_amount_positive",
            "CHECK(allocated_amount > 0)",
            "资金计划分配金额必须大于 0。",
        ),
    ]

    @api.model
    def _caller_visible_relation(self, model_name, record_id):
        try:
            relation_id = int(record_id)
        except (TypeError, ValueError):
            relation_id = 0
        record = self.env[model_name].search(
            [("id", "=", relation_id)],
            limit=1,
        )
        if not record:
            raise AccessError(_("资金计划分配关系不存在或当前用户无权访问。"))
        return record

    @api.model
    def _resolve_relation_values(self, vals, current=None):
        plan_line_id = vals.get(
            "plan_line_id",
            current.plan_line_id.id if current else False,
        )
        actual_event_id = vals.get(
            "actual_event_id",
            current.actual_event_id.id if current else False,
        )
        plan_line = self._caller_visible_relation(
            "project.funding.baseline.line",
            plan_line_id,
        )
        actual_event = self._caller_visible_relation(
            "payment.ledger",
            actual_event_id,
        )
        return plan_line, actual_event

    @api.model
    def _validate_pair(self, plan_line, actual_event, allocated_amount):
        if plan_line.company_id != actual_event.project_id.company_id:
            raise ValidationError(_("资金计划明细与实际付款事件必须属于同一公司。"))
        if plan_line.project_id != actual_event.project_id:
            raise ValidationError(_("资金计划明细与实际付款事件必须属于同一项目。"))
        if plan_line.currency_id != actual_event.currency_id:
            raise ValidationError(_("资金计划明细与实际付款事件币种不一致。"))
        rounding = actual_event.currency_id.rounding or 0.01
        if float_compare(
            allocated_amount or 0.0,
            0.0,
            precision_rounding=rounding,
        ) <= 0:
            raise ValidationError(_("资金计划分配金额必须大于 0。"))

    def _validate_relation_state(self):
        for record in self:
            self._validate_pair(
                record.plan_line_id,
                record.actual_event_id,
                record.allocated_amount,
            )
        self._check_actual_event_totals()

    def _check_actual_event_totals(self, event_ids=None):
        ids = set(event_ids or self.mapped("actual_event_id").ids)
        if not ids:
            return
        self.env.cr.execute(
            "SELECT id FROM payment_ledger WHERE id IN %s FOR UPDATE",
            [tuple(ids)],
        )
        events = self.env["payment.ledger"].search([("id", "in", list(ids))])
        totals = {
            row["actual_event_id"][0]: row.get(
                "allocated_amount_sum",
                row.get("allocated_amount", 0.0),
            )
            for row in self.read_group(
                [("actual_event_id", "in", list(ids))],
                ["allocated_amount:sum"],
                ["actual_event_id"],
            )
        }
        for event in events:
            rounding = event.currency_id.rounding or 0.01
            if float_compare(
                totals.get(event.id, 0.0),
                event.amount or 0.0,
                precision_rounding=rounding,
            ) > 0:
                raise ValidationError(
                    _("实际付款事件的资金计划分配合计不得超过实际付款金额。")
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            plan_line, actual_event = self._resolve_relation_values(vals)
            self._validate_pair(
                plan_line,
                actual_event,
                vals.get("allocated_amount"),
            )
        records = super().create(vals_list)
        records._validate_relation_state()
        return records

    def write(self, vals):
        old_event_ids = set(self.mapped("actual_event_id").ids)
        for record in self:
            plan_line, actual_event = self._resolve_relation_values(
                vals,
                current=record,
            )
            self._validate_pair(
                plan_line,
                actual_event,
                vals.get("allocated_amount", record.allocated_amount),
            )
        result = super().write(vals)
        self._validate_relation_state()
        self._check_actual_event_totals(
            old_event_ids | set(self.mapped("actual_event_id").ids)
        )
        return result

    def unlink(self):
        event_ids = set(self.mapped("actual_event_id").ids)
        result = super().unlink()
        self._check_actual_event_totals(event_ids)
        return result
