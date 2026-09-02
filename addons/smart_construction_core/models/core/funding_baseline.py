# -*- coding: utf-8 -*-
import uuid

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.float_utils import float_compare


_FUNDING_BASELINE_TOKEN = object()
_FUNDING_ALLOCATION_TOKEN = object()


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
        readonly=True,
        copy=False,
    )
    company_id = fields.Many2one(
        "res.company",
        string="公司",
        readonly=True,
        copy=False,
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
            ("superseded", "已被新版本替代"),
            ("closed", "关闭"),
            ("cancelled", "取消"),
            ("legacy_unresolved", "历史权威待确认"),
        ],
        string="状态",
        default="draft",
        index=True,
        required=True,
        tracking=True,
    )
    version_no = fields.Integer(string="版本号", readonly=True, copy=False, index=True)
    version_key = fields.Char(string="版本标识", readonly=True, copy=False, index=True)
    period_start = fields.Date(string="控制期开始", tracking=True, index=True)
    period_end = fields.Date(string="控制期结束", tracking=True, index=True)
    supersedes_id = fields.Many2one(
        "project.funding.baseline", string="前一版本", readonly=True, copy=False,
        index=True, ondelete="restrict",
    )
    superseded_by_id = fields.Many2one(
        "project.funding.baseline", string="后一版本", readonly=True, copy=False,
        index=True, ondelete="restrict",
    )
    revision_reason = fields.Text(string="修订原因", readonly=True, copy=False)
    normalization_state = fields.Selection(
        [
            ("normalized", "已标准化"),
            ("legacy_unresolved_period", "历史期间待确认"),
            ("legacy_unresolved_authority", "历史权威版本待确认"),
            ("legacy_unresolved_amount", "历史金额待确认"),
            ("legacy_unresolved_identity", "历史公司币种待确认"),
        ],
        string="标准化状态", default="normalized", required=True,
        readonly=True, copy=False, index=True,
    )
    activated_at = fields.Datetime(string="生效时间", readonly=True, copy=False)
    activated_by_id = fields.Many2one(
        "res.users", string="生效人", readonly=True, copy=False, ondelete="restrict",
    )
    ended_at = fields.Datetime(string="终止时间", readonly=True, copy=False)
    ended_by_id = fields.Many2one(
        "res.users", string="终止人", readonly=True, copy=False, ondelete="restrict",
    )
    end_reason = fields.Text(string="终止原因", readonly=True, copy=False)
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

    _sql_constraints = [
        ("total_amount_positive", "CHECK(normalization_state != 'normalized' OR total_amount > 0)", "标准资金基线的资金上限必须大于 0。"),
        ("project_version_no_unique", "UNIQUE(project_id, version_no)", "同一项目版本号不得重复。"),
        ("project_version_key_unique", "UNIQUE(project_id, version_key)", "同一项目版本标识不得重复。"),
        ("period_order", "CHECK(period_start IS NULL OR period_end IS NULL OR period_start <= period_end)", "资金控制期开始日期不得晚于结束日期。"),
        ("normalized_identity_present", "CHECK(normalization_state != 'normalized' OR (company_id IS NOT NULL AND currency_id IS NOT NULL))", "标准资金基线必须固化公司与币种身份。"),
    ]

    def init(self):
        self.env.cr.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS project_funding_baseline_one_active_uidx "
            "ON project_funding_baseline (project_id) WHERE state = 'active'"
        )
        self.env.cr.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS project_funding_baseline_one_live_successor_uidx "
            "ON project_funding_baseline (supersedes_id) "
            "WHERE supersedes_id IS NOT NULL AND state != 'cancelled'"
        )

    @api.constrains(
        "normalization_state", "version_no", "version_key", "period_start",
        "period_end", "total_amount", "supersedes_id", "project_id", "company_id",
        "currency_id",
    )
    def _check_normalized_authority_shape(self):
        for record in self:
            if record.normalization_state == "normalized":
                if (
                    not record.version_no
                    or not record.version_key
                    or not record.period_start
                    or not record.period_end
                    or not record.company_id
                    or not record.currency_id
                ):
                    raise ValidationError(_("标准资金基线必须具备版本身份和完整控制期。"))
                if float_compare(
                    record.total_amount or 0.0,
                    0.0,
                    precision_rounding=record.currency_id.rounding or 0.01,
                ) <= 0:
                    raise ValidationError(_("标准资金基线的资金上限必须大于 0。"))
            predecessor = record.supersedes_id
            if predecessor and (
                predecessor == record
                or predecessor.project_id != record.project_id
                or predecessor.company_id != record.company_id
                or predecessor.currency_id != record.currency_id
                or (
                    predecessor.version_no
                    and record.version_no
                    and predecessor.version_no >= record.version_no
                )
            ):
                raise ValidationError(_("资金基线前后版本必须属于同一项目并保持严格递增。"))

    @api.depends("total_amount", "line_ids.allocated_amount")
    def _compute_allocation_amounts(self):
        totals = {}
        if self.ids:
            rows = self.env["project.funding.actual.event.allocation"].read_group(
                [("baseline_id", "in", self.ids), ("normalization_state", "in", ["normalized", "legacy_unresolved_period"])],
                ["effective_amount:sum"], ["baseline_id"],
            )
            totals = {
                row["baseline_id"][0]: row.get(
                    "effective_amount_sum", row.get("effective_amount", 0.0)
                )
                for row in rows
            }
        for record in self:
            allocated = totals.get(record.id, 0.0)
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
        domain = [("id", "=", relation_id)]
        if not self.env.su and not self.env.user.has_group(
            "smart_construction_core.group_sc_cap_finance_manager"
        ):
            domain += [
                "|",
                ("user_id", "=", self.env.user.id),
                ("message_follower_ids.partner_id", "=", self.env.user.partner_id.id),
            ]
        project = self.env["project.project"].search(domain, limit=1)
        if not project:
            raise AccessError(_("项目不存在或当前用户无权访问。"))
        return project

    @api.model
    def _lock_projects(self, project_ids):
        ids = sorted({int(item) for item in project_ids if item})
        if ids:
            self.env.cr.execute(
                "SELECT id FROM project_project WHERE id = ANY(%s) ORDER BY id FOR UPDATE",
                [ids],
            )

    @api.model
    def _next_version_no(self, project_id):
        self._lock_projects([project_id])
        self.env.cr.execute(
            """
            SELECT GREATEST(
                       COALESCE(MAX(version_no), 0),
                       COALESCE(MAX(
                           CASE
                               WHEN version_key ~ %s
                               THEN substring(version_key FROM ':v([0-9]+)$')::integer
                           END
                       ), 0)
                   ) + 1
              FROM project_funding_baseline
             WHERE project_id = %s
            """,
            [f"^{int(project_id)}:v[0-9]+$", project_id],
        )
        return self.env.cr.fetchone()[0]

    @api.model
    def _lock_project_baselines(self, project_ids):
        ids = sorted({int(item) for item in project_ids if item})
        self._lock_projects(ids)
        if ids:
            self.env.cr.execute(
                "SELECT id FROM project_funding_baseline "
                "WHERE project_id = ANY(%s) ORDER BY id FOR UPDATE",
                [ids],
            )

    @api.model
    def _advance_reservation_authority(self, project_ids):
        ids = sorted({int(item) for item in project_ids if item})
        if ids:
            self.env.cr.execute(
                "UPDATE project_project SET funding_reservation_revision = "
                "COALESCE(funding_reservation_revision, 0) + 1 "
                "WHERE id = ANY(%s)",
                [ids],
            )

    @api.model_create_multi
    def create(self, vals_list):
        self.check_access_rights("create")
        requested_projects = [int(vals.get("project_id") or 0) for vals in vals_list]
        if len([item for item in requested_projects if item]) != len(
            set(item for item in requested_projects if item)
        ):
            raise ValidationError(_("同一批次不能并行创建同一项目的多个资金基线版本。"))
        projects = []
        for vals in vals_list:
            project_id = vals.get("project_id")
            if project_id:
                project = self._caller_visible_project(project_id)
                projects.append(project)
            else:
                projects.append(self.env["project.project"])
        self._lock_projects(
            project.id for project in projects if project
        )
        for vals, project in zip(vals_list, projects):
            if project:
                project.invalidate_recordset()
                self._check_funding_ready(project)
                if not project.company_id or not project.company_id.currency_id:
                    raise ValidationError(_("标准资金基线要求项目明确归属公司及本位币。"))
                vals.pop("company_id", None)
                vals.pop("currency_id", None)
                vals["company_id"] = project.company_id.id
                vals["currency_id"] = project.company_id.currency_id.id
                if vals.get("state", "draft") != "draft":
                    raise UserError(_("资金基线必须先创建为草稿，再通过受控动作生效。"))
                if vals.get("normalization_state", "normalized") != "normalized":
                    raise AccessError(_("历史标准化状态只能由版本迁移维护。"))
                if not vals.get("period_start") or not vals.get("period_end"):
                    raise ValidationError(_("标准资金基线必须明确控制期开始和结束日期。"))
                version_no = self._next_version_no(project.id)
                if self.env.context.get("_sc_funding_baseline_token") is not _FUNDING_BASELINE_TOKEN:
                    vals.pop("version_no", None)
                    vals.pop("version_key", None)
                    vals.pop("supersedes_id", None)
                    vals.pop("revision_reason", None)
                vals["version_no"] = version_no
                vals["version_key"] = f"{project.id}:v{version_no}"
        return super().create(vals_list)

    def write(self, vals):
        service = (
            self.env.context.get("_sc_funding_baseline_token")
            is _FUNDING_BASELINE_TOKEN
        )
        protected = {
            "state", "version_no", "version_key", "supersedes_id", "superseded_by_id",
            "normalization_state", "activated_at", "activated_by_id", "ended_at",
            "ended_by_id", "end_reason", "revision_reason", "company_id", "currency_id",
        }
        if protected.intersection(vals) and not service:
            raise AccessError(_("资金基线版本与状态只能由受控生命周期动作维护。"))
        if "project_id" in vals:
            raise AccessError(_("资金基线所属项目自创建起不可变；请取消后重新建立。"))
        business = {
            "total_amount", "period_start", "period_end", "attachment_ids", "line_ids",
        }
        if business.intersection(vals):
            self._lock_project_baselines(self.mapped("project_id").ids)
            self.invalidate_recordset()
        if business.intersection(vals) and self.filtered(lambda row: row.state != "draft"):
            raise UserError(_("生效或终止后的资金基线不可修改；请创建修订版本。"))
        return super().write(vals)

    def unlink(self):
        raise UserError(_("资金基线属于版本化权威事实，不允许删除；草稿可通过取消动作终止。"))

    def _assert_manager(self):
        if not self.env.su and not self.env.user.has_group(
            "smart_construction_core.group_sc_cap_finance_manager"
        ):
            raise AccessError(_("只有财务经理可以维护资金基线版本。"))

    def action_activate(self):
        self._assert_manager()
        project_ids = self.mapped("project_id").ids
        self._lock_project_baselines(project_ids)
        self._advance_reservation_authority(project_ids)
        self.invalidate_recordset()
        for record in self:
            if record.state != "draft" or record.normalization_state != "normalized":
                raise UserError(_("只有已标准化草稿资金基线可以生效。"))
            if (
                record.company_id != record.project_id.company_id
                or record.currency_id != record.project_id.company_id.currency_id
            ):
                raise UserError(_("项目公司或本位币已变化；历史金额不得换币生效，请重新建立资金基线。"))
            if not record.period_start or not record.period_end or record.period_start > record.period_end:
                raise ValidationError(_("资金基线控制期不完整或无效。"))
            if not record.line_ids:
                raise ValidationError(_("资金基线至少需要一条计划明细。"))
            planned = sum(record.line_ids.mapped("planned_amount"))
            if float_compare(planned, record.total_amount, precision_rounding=record.currency_id.rounding or 0.01):
                raise ValidationError(_("资金计划明细合计必须等于资金基线上限。"))
            active = self.sudo().search([
                ("project_id", "=", record.project_id.id), ("state", "=", "active"),
                ("id", "!=", record.id),
            ], limit=2)
            if active:
                if len(active) != 1 or record.supersedes_id != active:
                    raise UserError(_("新版本必须明确承接当前唯一生效版本。"))
                active.with_context(_sc_funding_baseline_token=_FUNDING_BASELINE_TOKEN).write({
                    "state": "superseded", "superseded_by_id": record.id,
                    "ended_at": fields.Datetime.now(), "ended_by_id": self.env.user.id,
                    "end_reason": record.revision_reason or _("新版本生效"),
                })
            elif record.supersedes_id and record.supersedes_id.state not in ("closed", "superseded"):
                raise UserError(_("前一版本状态不允许被承接。"))
            elif record.supersedes_id and record.supersedes_id.state == "closed":
                predecessor = record.supersedes_id
                if predecessor.superseded_by_id and predecessor.superseded_by_id != record:
                    raise UserError(_("关闭版本已由另一资金基线版本承接。"))
                predecessor.with_context(
                    _sc_funding_baseline_token=_FUNDING_BASELINE_TOKEN
                ).write({"superseded_by_id": record.id})
            record.with_context(_sc_funding_baseline_token=_FUNDING_BASELINE_TOKEN).write({
                "state": "active", "activated_at": fields.Datetime.now(),
                "activated_by_id": self.env.user.id,
            })
        return True

    def action_close(self, reason=None):
        self._assert_manager()
        if not reason:
            raise ValidationError(_("关闭资金基线必须填写原因。"))
        project_ids = self.mapped("project_id").ids
        self._lock_project_baselines(project_ids)
        self._advance_reservation_authority(project_ids)
        self.invalidate_recordset()
        for record in self:
            if record.state != "active":
                raise UserError(_("只有生效中的资金基线可以关闭。"))
            record.with_context(_sc_funding_baseline_token=_FUNDING_BASELINE_TOKEN).write({
                "state": "closed", "ended_at": fields.Datetime.now(),
                "ended_by_id": self.env.user.id, "end_reason": reason,
            })
        return True

    def action_open_transition_wizard(self):
        self.ensure_one()
        self._assert_manager()
        operation = self.env.context.get("funding_baseline_operation")
        allowed_states = {"close": ("active",), "revision": ("active", "closed")}
        if operation not in allowed_states or self.state not in allowed_states[operation]:
            raise UserError(_("当前资金基线状态不允许执行该生命周期操作。"))
        return {
            "type": "ir.actions.act_window",
            "name": _("关闭资金基线") if operation == "close" else _("创建资金基线修订"),
            "res_model": "project.funding.baseline.transition.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_baseline_id": self.id,
                "default_operation": operation,
            },
        }

    def action_cancel(self):
        self._assert_manager()
        if self.filtered(lambda row: row.state != "draft"):
            raise UserError(_("只有草稿资金基线可以取消。"))
        self._lock_project_baselines(self.mapped("project_id").ids)
        self.invalidate_recordset()
        if self.filtered(lambda row: row.state != "draft"):
            raise UserError(_("只有草稿资金基线可以取消。"))
        return self.with_context(
            _sc_funding_baseline_token=_FUNDING_BASELINE_TOKEN
        ).write({"state": "cancelled"})

    def action_create_revision(self, reason=None, period_start=None, period_end=None):
        self.ensure_one()
        self._assert_manager()
        if self.state not in ("active", "closed") or not reason:
            raise ValidationError(_("只能从生效或关闭版本创建有原因的修订。"))
        if (
            self.company_id != self.project_id.company_id
            or self.currency_id != self.project_id.company_id.currency_id
        ):
            raise UserError(_("项目公司或本位币已变化；不得复制历史金额，请重新建立资金基线。"))
        self._lock_project_baselines([self.project_id.id])
        self.invalidate_recordset()
        if self.state not in ("active", "closed"):
            raise ValidationError(_("只能从生效或关闭版本创建有原因的修订。"))
        existing = self.search([("supersedes_id", "=", self.id), ("state", "!=", "cancelled")], limit=1)
        if existing:
            return existing
        version_no = self._next_version_no(self.project_id.id)
        target_start = period_start or self.period_start
        target_end = period_end or self.period_end
        if not target_start or not target_end:
            raise ValidationError(_("历史待确认资金基线的修订必须人工明确新控制期。"))
        return self.with_context(
            _sc_funding_baseline_token=_FUNDING_BASELINE_TOKEN
        ).create({
            "project_id": self.project_id.id, "total_amount": self.total_amount,
            "period_start": target_start, "period_end": target_end,
            "version_no": version_no, "version_key": f"{self.project_id.id}:v{version_no}",
            "supersedes_id": self.id, "revision_reason": reason,
            "line_ids": [(0, 0, {
                "sequence": line.sequence, "name": line.name,
                "planned_amount": line.planned_amount, "line_key": line.line_key,
            }) for line in self.line_ids],
        })


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
    line_key = fields.Char(string="明细稳定标识", readonly=True, copy=False, index=True)

    _sql_constraints = [
        (
            "planned_amount_positive",
            "CHECK(planned_amount > 0)",
            "资金计划明细金额必须大于 0。",
        ),
        ("baseline_line_key_unique", "UNIQUE(baseline_id, line_key)", "同一资金版本内明细标识不得重复。"),
    ]

    @api.depends("planned_amount", "allocation_ids.effective_amount", "allocation_ids.normalization_state")
    def _compute_allocation_amounts(self):
        totals = {}
        if self.ids:
            rows = self.env["project.funding.actual.event.allocation"].read_group(
                [("plan_line_id", "in", self.ids), ("normalization_state", "in", ["normalized", "legacy_unresolved_period"])],
                ["effective_amount:sum"], ["plan_line_id"],
            )
            totals = {
                row["plan_line_id"][0]: row.get(
                    "effective_amount_sum", row.get("effective_amount", 0.0)
                )
                for row in rows
            }
        for record in self:
            allocated = totals.get(record.id, 0.0)
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

    @api.model_create_multi
    def create(self, vals_list):
        baselines = self.env["project.funding.baseline"].browse(
            [vals.get("baseline_id") for vals in vals_list if vals.get("baseline_id")]
        ).exists()
        baselines._lock_project_baselines(baselines.mapped("project_id").ids)
        baselines.invalidate_recordset()
        baseline_by_id = {record.id: record for record in baselines}
        for vals in vals_list:
            baseline = baseline_by_id.get(vals.get("baseline_id"))
            if baseline and baseline.state != "draft":
                raise UserError(_("只有草稿资金基线可以新增计划明细。"))
            if self.env.context.get(
                "_sc_funding_baseline_token"
            ) is not _FUNDING_BASELINE_TOKEN:
                vals.pop("line_key", None)
            vals.setdefault("line_key", uuid.uuid4().hex)
        return super().create(vals_list)

    def write(self, vals):
        if "baseline_id" in vals:
            raise AccessError(_("资金计划明细所属基线自创建起不可变。"))
        baselines = self.mapped("baseline_id")
        baselines._lock_project_baselines(baselines.mapped("project_id").ids)
        baselines.invalidate_recordset()
        if self.filtered(lambda row: row.baseline_id.state != "draft"):
            raise UserError(_("资金基线生效后，计划明细不可修改。"))
        if "line_key" in vals:
            raise AccessError(_("计划明细稳定标识不可修改。"))
        return super().write(vals)

    def unlink(self):
        baselines = self.mapped("baseline_id")
        baselines._lock_project_baselines(baselines.mapped("project_id").ids)
        baselines.invalidate_recordset()
        if self.filtered(lambda row: row.baseline_id.state != "draft"):
            raise UserError(_("资金基线生效后，计划明细不可删除。"))
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
        required=True, readonly=True,
    )
    effective_amount = fields.Monetary(
        string="净影响金额", currency_field="currency_id", required=True, readonly=True,
    )
    baseline_id = fields.Many2one(
        "project.funding.baseline", string="资金基线快照",
        readonly=True, copy=False, index=True, ondelete="restrict",
    )
    operation_key = fields.Char(string="操作幂等键", readonly=True, index=True)
    allocation_key = fields.Char(string="分配事实键", readonly=True, index=True)
    entry_type = fields.Selection(
        [("allocation", "分配"), ("reversal", "冲销")],
        readonly=True, index=True,
    )
    reverses_id = fields.Many2one(
        "project.funding.actual.event.allocation", string="冲销原事实",
        readonly=True, copy=False, index=True, ondelete="restrict",
    )
    reversed_by_id = fields.Many2one(
        "project.funding.actual.event.allocation", string="冲销事实",
        readonly=True, copy=False, index=True, ondelete="restrict",
    )
    effective_at = fields.Datetime(string="生效时间", readonly=True, index=True)
    effective_date = fields.Date(string="生效日期", readonly=True, index=True)
    normalization_state = fields.Selection(
        [
            ("normalized", "已标准化"),
            ("legacy_unresolved_period", "历史期间待确认"),
            ("legacy_unresolved_relation", "历史关系待确认"),
            ("legacy_unresolved_conservation", "历史守恒异常"),
        ],
        readonly=True, index=True,
    )
    reason = fields.Text(string="原因", readonly=True)
    company_id = fields.Many2one(
        "res.company",
        string="公司",
        readonly=True,
        copy=False,
        index=True,
    )
    project_id = fields.Many2one(
        "project.project",
        string="项目",
        readonly=True,
        copy=False,
        index=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="币种",
        readonly=True,
        copy=False,
    )

    _sql_constraints = [
        (
            "allocated_amount_positive",
            "CHECK(allocated_amount > 0)",
            "资金计划分配金额必须大于 0。",
        ),
        ("allocation_key_unique", "UNIQUE(allocation_key)", "资金分配事实键不得重复。"),
        ("allocation_reversal_unique", "UNIQUE(reverses_id)", "每条资金分配事实最多冲销一次。"),
        ("effective_sign_valid", "CHECK((entry_type = 'allocation' AND effective_amount = allocated_amount AND reverses_id IS NULL) OR (entry_type = 'reversal' AND effective_amount = -allocated_amount AND reverses_id IS NOT NULL))", "资金分配净影响方向无效。"),
        ("normalized_identity_present", "CHECK(normalization_state != 'normalized' OR (baseline_id IS NOT NULL AND project_id IS NOT NULL AND company_id IS NOT NULL AND currency_id IS NOT NULL))", "标准资金分配事实必须固化基线、项目、公司与币种身份。"),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get("_sc_funding_allocation_token") is not _FUNDING_ALLOCATION_TOKEN:
            raise AccessError(_("资金分配是不可变事实，只能由受控付款台账服务创建。"))
        normalized = []
        for incoming in vals_list:
            vals = dict(incoming)
            line = self.env["project.funding.baseline.line"].browse(
                int(vals.get("plan_line_id") or 0)
            ).exists()
            event = self.env["payment.ledger"].browse(
                int(vals.get("actual_event_id") or 0)
            ).exists()
            if not line or not event:
                raise ValidationError(_("资金分配必须关联有效的计划明细与实际付款事件。"))
            baseline = line.baseline_id
            original = self.browse(int(vals.get("reverses_id") or 0)).exists()
            if original:
                if (
                    original.entry_type != "allocation"
                    or original.normalization_state != "normalized"
                    or original.actual_event_id != event
                    or original.plan_line_id != line
                    or original.baseline_id != baseline
                    or not original.project_id
                    or not original.company_id
                    or not original.currency_id
                ):
                    raise ValidationError(_("资金冲销必须完整继承原分配的历史经济身份。"))
                snapshot_project = original.project_id
                snapshot_company = original.company_id
                snapshot_currency = original.currency_id
            else:
                if (
                    baseline.project_id != event.project_id
                    or baseline.company_id != event.project_id.company_id
                    or baseline.currency_id != event.currency_id
                ):
                    raise ValidationError(_("资金分配的项目、公司或币种快照与付款事件不一致。"))
                snapshot_project = baseline.project_id
                snapshot_company = baseline.company_id
                snapshot_currency = baseline.currency_id
            vals.update({
                "baseline_id": baseline.id,
                "project_id": snapshot_project.id,
                "company_id": snapshot_company.id,
                "currency_id": snapshot_currency.id,
            })
            normalized.append(vals)
        return super().create(normalized)

    def write(self, vals):
        raise AccessError(_("资金分配日记不可修改；调整必须追加冲销和新分配。"))

    def unlink(self):
        raise AccessError(_("资金分配日记不可删除。"))
