# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


_DOCUMENT_STATE_TOKEN = object()


class ScPlan(models.Model):
    _name = "sc.plan"
    _description = "计划"
    _inherit = ["mail.thread", "mail.activity.mixin", "tier.validation"]
    _order = "planned_start desc, id desc"

    reject_reason = fields.Text(string="驳回原因", readonly=True, copy=False)
    name = fields.Char(string="计划名称", required=True, tracking=True)
    plan_type = fields.Selection(
        [
            ("key_node", "关键节点计划"),
            ("master", "项目主项计划"),
            ("special", "项目专项计划"),
            ("company_special", "公司专项计划"),
            ("organization", "组织计划"),
        ],
        string="计划类型",
        required=True,
        default="master",
        index=True,
        tracking=True,
    )
    project_id = fields.Many2one("project.project", string="项目", index=True, tracking=True)
    company_id = fields.Many2one(
        "res.company",
        string="公司",
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )
    owner_id = fields.Many2one("res.users", string="责任人", default=lambda self: self.env.user, index=True)
    department_id = fields.Many2one("hr.department", string="责任部门", index=True)
    phase_name = fields.Char(string="项目分期/标段", index=True)
    template_name = fields.Char(string="计划模板", index=True)
    creation_method = fields.Selection(
        [
            ("manual", "手工编制"),
            ("template", "模板创建"),
            ("excel", "Excel导入"),
            ("project", "Project导入"),
            ("system", "系统生成"),
        ],
        string="编制方式",
        default="manual",
        index=True,
        tracking=True,
    )
    version_stage = fields.Selection(
        [("draft", "编制阶段"), ("baseline", "基准版"), ("adjustment", "调整版"), ("archive", "历史版")],
        string="版本阶段",
        default="draft",
        index=True,
    )
    report_cycle = fields.Selection(
        [("none", "不固定"), ("daily", "日报"), ("weekly", "周报"), ("monthly", "月报"), ("milestone", "节点汇报")],
        string="汇报周期",
        default="milestone",
        index=True,
    )
    planned_start = fields.Date(string="计划开始", index=True)
    planned_finish = fields.Date(string="计划完成", index=True)
    actual_start = fields.Date(string="实际开始", readonly=True, copy=False, index=True)
    actual_finish = fields.Date(string="实际完成", readonly=True, copy=False, index=True)
    state = fields.Selection(
        [
            ("draft", "草稿"),
            ("confirmed", "已确认"),
            ("in_progress", "执行中"),
            ("done", "已完成"),
            ("cancel", "已取消"),
        ],
        string="状态",
        readonly=True,
        copy=False,
        default="draft",
        required=True,
        index=True,
        tracking=True,
    )
    line_ids = fields.One2many("sc.plan.line", "plan_id", string="计划节点")
    version_ids = fields.One2many("sc.plan.version", "plan_id", string="计划版本")
    report_ids = fields.One2many("sc.plan.report", "plan_id", string="汇报")
    attachment_ids = fields.Many2many("ir.attachment", string="计划附件")
    progress_rate = fields.Float(string="完成率(%)", compute="_compute_progress_rate", store=True)
    attainment_state = fields.Selection(
        [("not_started", "未开始"), ("on_track", "正常"), ("due_soon", "即将逾期"), ("overdue", "已逾期"), ("done", "已完成")],
        string="达成状态",
        compute="_compute_attainment_state",
        store=True,
        index=True,
    )
    legacy_fact_model = fields.Char(string="来源通用模型", index=True)
    legacy_fact_id = fields.Integer(string="来源通用记录ID", index=True)
    legacy_fact_type = fields.Char(string="来源业务类型", index=True)
    note = fields.Text(string="说明")

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get("state", self.env.context.get("default_state", "draft")) != "draft":
                raise UserError(_("计划必须从草稿通过正式审批和业务动作流转。"))
            if any(values.get(name, self.env.context.get("default_" + name)) for name in ("actual_start", "actual_finish")):
                raise UserError(_("计划实际起止日期只能由开始执行和完成动作产生。"))
        return super().create(vals_list)

    def write(self, vals):
        authoritative = self.env.context.get("sc_document_state_token") is _DOCUMENT_STATE_TOKEN
        if {"state", "actual_start", "actual_finish"}.intersection(vals) and not authoritative:
            raise UserError(_("计划状态及实际起止日期只能由正式业务动作写入。"))
        # Child execution is governed separately; these are the reviewed plan facts.
        definition_fields = {
            "name", "plan_type", "project_id", "company_id", "owner_id", "department_id",
            "phase_name", "template_name", "creation_method", "version_stage", "report_cycle",
            "planned_start", "planned_finish", "note", "attachment_ids",
        }
        if not authoritative and definition_fields.intersection(vals) and any(
            rec.state != "draft" or getattr(rec, "validation_status", "") in ("waiting", "pending", "validated")
            for rec in self
        ):
            raise UserError(_("已提交审批或已确认的计划基准内容不可直接修改。"))
        return super().write(vals)

    def _plan_unlink_denial(self):
        for rec in self:
            if rec.state not in ("draft", "cancel") or rec.validation_status in ("waiting", "pending", "validated"):
                return _("审批中或已形成执行事实的计划不可删除。")
            if any(version.state != "draft" or version.validation_status in ("waiting", "pending", "validated") for version in rec.version_ids):
                return _("计划包含审批中或已确认的版本，不能通过删除计划移除版本事实。")
            if any(report.state not in ("draft", "rejected") or report.validation_status in ("waiting", "pending", "validated") for report in rec.report_ids):
                return _("计划包含审批中或已确认的汇报，不能通过删除计划移除汇报事实。")
        return False

    def unlink(self):
        reason = self._plan_unlink_denial()
        if reason:
            raise UserError(reason)
        return super().unlink()

    def _check_allow_write_under_validation(self, vals):
        self.ensure_one()
        # A rejected draft is editable again; status remains action-owned.
        if self.state == "draft" and self.validation_status == "rejected" and "state" not in vals:
            return True
        return super()._check_allow_write_under_validation(vals)

    def _write_document_state(self, values):
        return self.with_context(sc_document_state_token=_DOCUMENT_STATE_TOKEN).write(values)

    @api.depends("line_ids.progress_rate")
    def _compute_progress_rate(self):
        for plan in self:
            lines = plan.line_ids
            plan.progress_rate = sum(lines.mapped("progress_rate")) / len(lines) if lines else 0.0

    @api.depends("state", "planned_finish", "progress_rate")
    def _compute_attainment_state(self):
        today = fields.Date.context_today(self)
        for plan in self:
            if plan.state == "done" or plan.progress_rate >= 100:
                plan.attainment_state = "done"
            elif not plan.planned_finish:
                plan.attainment_state = "not_started" if plan.state == "draft" else "on_track"
            elif plan.planned_finish < today:
                plan.attainment_state = "overdue"
            elif (plan.planned_finish - today).days <= 7:
                plan.attainment_state = "due_soon"
            else:
                plan.attainment_state = "on_track"

    @api.constrains("planned_start", "planned_finish", "actual_start", "actual_finish")
    def _check_date_order(self):
        for rec in self:
            if rec.planned_start and rec.planned_finish and rec.planned_start > rec.planned_finish:
                raise ValidationError(_("计划开始不能晚于计划完成。"))
            if rec.actual_start and rec.actual_finish and rec.actual_start > rec.actual_finish:
                raise ValidationError(_("实际开始不能晚于实际完成。"))

    def action_confirm(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("只有草稿状态的计划可以确认。"))
            rec._check_business_anchor(require_schedule=True)
            if not self.env["sc.approval.policy"]._start_submission_review(rec):
                rec.with_context(skip_validation_check=True)._write_document_state({"state": "confirmed", "reject_reason": False})
        return True

    def action_on_tier_approved(self):
        for rec in self:
            if rec.state == "draft" and rec.review_ids and rec.validation_status == "validated":
                rec._check_business_anchor(require_schedule=True)
                rec.with_context(skip_validation_check=True)._write_document_state({"state": "confirmed", "reject_reason": False})

    def action_on_tier_rejected(self):
        for rec in self:
            if rec.state == "draft" and rec.review_ids and rec.validation_status == "rejected":
                reviews = rec.review_ids.filtered(lambda review: review.status == "rejected" and review.comment)
                reason = reviews.sorted(lambda review: review.write_date or review.create_date, reverse=True)[:1].comment if reviews else False
                rec.with_context(skip_validation_check=True).write({"reject_reason": reason})

    def action_start(self):
        for rec in self:
            if rec.state != "confirmed":
                raise UserError(_("只有已确认状态的计划可以开始执行。"))
            rec._check_business_anchor(require_schedule=True)
            self.env["sc.approval.policy"]._assert_submission_approved(rec, ("confirmed",))
        self._write_document_state({"state": "in_progress", "actual_start": fields.Date.context_today(self)})
        return True

    def action_done(self):
        for rec in self:
            if rec.state != "in_progress":
                raise UserError(_("只有执行中的计划可以完成。"))
            rec._check_business_anchor(require_schedule=True, require_lines_done=True)
            self.env["sc.approval.policy"]._assert_submission_approved(rec, ("in_progress",))
        self._write_document_state({"state": "done", "actual_finish": fields.Date.context_today(self)})
        return True

    def action_cancel(self):
        for rec in self:
            if rec.state not in ("draft", "confirmed", "in_progress"):
                raise UserError(_("只有未完成的计划可以取消。"))
        self._write_document_state({"state": "cancel"})
        return True

    def action_reset_draft(self):
        for rec in self:
            if rec.state != "cancel":
                raise UserError(_("只有已取消状态的计划可以重置为草稿。"))
        self._write_document_state({"state": "draft"})
        return True

    def _check_business_anchor(self, require_schedule=False, require_lines_done=False):
        for rec in self:
            if require_schedule and not rec.line_ids and not (rec.planned_start and rec.planned_finish):
                raise UserError(_("计划确认前必须维护计划起止日期或计划节点。"))
            if require_lines_done and rec.line_ids.filtered(lambda line: line.state not in ("done", "cancel")):
                raise UserError(_("计划完成前所有未取消节点必须完成。"))


class ScPlanLine(models.Model):
    _name = "sc.plan.line"
    _description = "计划节点"
    _parent_name = "parent_id"
    _parent_store = True
    _order = "plan_id, sequence, id"

    plan_id = fields.Many2one("sc.plan", string="计划", required=True, ondelete="cascade", index=True)
    parent_id = fields.Many2one("sc.plan.line", string="上级节点", index=True, ondelete="cascade")
    parent_path = fields.Char(index=True, unaccent=False)
    child_ids = fields.One2many("sc.plan.line", "parent_id", string="子节点")
    sequence = fields.Integer(default=10)
    name = fields.Char(string="节点名称", required=True)
    owner_id = fields.Many2one("res.users", string="责任人", index=True)
    participant_ids = fields.Many2many("res.users", string="参与人")
    department_id = fields.Many2one("hr.department", string="责任部门", index=True)
    node_type = fields.Selection(
        [("task", "工作项"), ("milestone", "里程碑"), ("key_node", "关键节点"), ("report", "报告节点")],
        string="节点类型",
        default="task",
        index=True,
    )
    phase_name = fields.Char(string="分期/标段", index=True)
    linked_plan_line_id = fields.Many2one("sc.plan.line", string="联动节点", index=True)
    contract_id = fields.Many2one("construction.contract", string="关联合同", index=True)
    planned_start = fields.Date(string="计划开始", index=True)
    planned_finish = fields.Date(string="计划完成", index=True)
    actual_start = fields.Date(string="实际开始", index=True)
    actual_finish = fields.Date(string="实际完成", index=True)
    completion_standard = fields.Text(string="完成标准")
    deliverable_name = fields.Char(string="成果名称")
    deliverable_attachment_ids = fields.Many2many("ir.attachment", string="成果附件")
    report_required = fields.Boolean(string="要求汇报", default=True)
    weight = fields.Float(string="权重")
    progress_rate = fields.Float(string="完成率(%)")
    delay_days = fields.Integer(string="延期天数", compute="_compute_delay_status", store=True)
    is_overdue = fields.Boolean(string="已逾期", compute="_compute_delay_status", store=True, index=True)
    state = fields.Selection(
        [("draft", "未开始"), ("in_progress", "执行中"), ("done", "已完成"), ("blocked", "受阻"), ("cancel", "已取消")],
        string="状态",
        default="draft",
        index=True,
    )
    predecessor_ids = fields.Many2many(
        "sc.plan.line",
        "sc_plan_line_predecessor_rel",
        "line_id",
        "predecessor_id",
        string="前置节点",
    )
    legacy_fact_model = fields.Char(string="来源通用模型", index=True)
    legacy_fact_id = fields.Integer(string="来源通用记录ID", index=True)
    legacy_fact_type = fields.Char(string="来源业务类型", index=True)

    def _assert_definition_editable(self):
        if any(line.plan_id.state != "draft" or line.plan_id.validation_status in ("waiting", "pending", "validated") for line in self):
            raise UserError(_("已提交审批或已确认的计划节点基准不可直接修改。"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            initial = {name: vals.get(name, self.env.context.get("default_" + name))
                       for name in ("state", "progress_rate", "actual_start", "actual_finish")}
            if (initial["state"] not in (None, "draft") or float(initial["progress_rate"] or 0) != 0
                    or initial["actual_start"] or initial["actual_finish"]):
                raise UserError(_("新建计划节点必须为未开始、零进度且无实际执行日期。"))
            plan = self.env["sc.plan"].browse(vals.get("plan_id") or self.env.context.get("default_plan_id")).exists()
            if plan and (plan.state != "draft" or plan.validation_status in ("waiting", "pending", "validated")):
                raise UserError(_("只能在未提交审批的草稿计划中新增节点。"))
        return super().create(vals_list)

    def write(self, vals):
        execution_fields = {"actual_start", "actual_finish", "progress_rate", "state", "deliverable_attachment_ids"}
        if set(vals) - execution_fields:
            self._assert_definition_editable()
        if "plan_id" in vals:
            target = self.env["sc.plan"].browse(vals["plan_id"]).exists()
            if target and (target.state != "draft" or target.validation_status in ("waiting", "pending", "validated")):
                raise UserError(_("节点不能移入已提交审批或已确认的计划。"))
        if execution_fields.intersection(vals) and any(
            line.plan_id.state != "in_progress" or line.plan_id.validation_status in ("waiting", "pending") for line in self
        ):
            raise UserError(_("只有执行中的计划可以更新节点执行记录。"))
        return super().write(vals)

    def unlink(self):
        self._assert_definition_editable()
        return super().unlink()

    @api.depends("state", "planned_finish", "actual_finish")
    def _compute_delay_status(self):
        today = fields.Date.context_today(self)
        for rec in self:
            compare_date = rec.actual_finish or today
            if rec.planned_finish and rec.state != "cancel" and compare_date > rec.planned_finish:
                rec.delay_days = (compare_date - rec.planned_finish).days
                rec.is_overdue = rec.state != "done" or bool(rec.actual_finish and rec.actual_finish > rec.planned_finish)
            else:
                rec.delay_days = 0
                rec.is_overdue = False

    @api.constrains("progress_rate")
    def _check_progress_rate(self):
        for rec in self:
            if rec.progress_rate < 0 or rec.progress_rate > 100:
                raise ValidationError(_("完成率必须在 0 到 100 之间。"))


class ScPlanVersion(models.Model):
    _name = "sc.plan.version"
    _description = "计划版本"
    _inherit = ["mail.thread", "mail.activity.mixin", "tier.validation"]
    _state_from = ["draft"]
    _state_to = ["approved"]
    _order = "plan_id, version_no desc, id desc"

    plan_id = fields.Many2one("sc.plan", string="计划", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one("res.company", related="plan_id.company_id", store=True, index=True)
    reject_reason = fields.Text(string="退回原因", readonly=True, copy=False)
    version_no = fields.Char(string="版本号", required=True)
    base_version_id = fields.Many2one("sc.plan.version", string="对比基准版本", index=True)
    revision_type = fields.Selection(
        [("initial", "初版"), ("adjustment", "计划调整"), ("baseline", "基准确认"), ("import", "导入版本")],
        string="版本类型",
        default="adjustment",
        index=True,
    )
    version_date = fields.Date(string="版本日期", default=fields.Date.context_today, index=True)
    approved_by = fields.Many2one("res.users", string="确认人", index=True)
    approved_date = fields.Date(string="确认日期", index=True)
    change_reason = fields.Text(string="修订原因")
    diff_summary = fields.Text(string="版本差异说明")
    snapshot_note = fields.Text(string="版本说明")
    state = fields.Selection([("draft", "草稿"), ("approved", "已确认")], string="状态", default="draft", index=True)
    legacy_fact_model = fields.Char(string="来源通用模型", index=True)
    legacy_fact_id = fields.Integer(string="来源通用记录ID", index=True)
    legacy_fact_type = fields.Char(string="来源业务类型", index=True)

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get("state", self.env.context.get("default_state", "draft")) != "draft":
                raise UserError(_("计划版本必须从草稿通过正式提交和审批流转。"))
            if any(values.get(name, self.env.context.get("default_" + name)) for name in ("approved_by", "approved_date", "reject_reason")):
                raise UserError(_("计划版本审核结果只能由正式审批动作写入。"))
        return super().create(vals_list)

    def write(self, vals):
        authoritative = self.env.context.get("sc_document_state_token") is _DOCUMENT_STATE_TOKEN
        if not authoritative and {"state", "approved_by", "approved_date", "reject_reason"}.intersection(vals):
            raise UserError(_("计划版本状态和审核结果只能由正式业务动作写入。"))
        definition_fields = {
            "plan_id", "company_id", "version_no", "base_version_id", "revision_type", "version_date",
            "change_reason", "diff_summary", "snapshot_note",
        }
        if not authoritative and definition_fields.intersection(vals) and any(
            rec.state != "draft" or rec.validation_status in ("waiting", "pending", "validated") for rec in self
        ):
            raise UserError(_("审批中或已确认的计划版本内容不可直接修改。"))
        return super().write(vals)

    def unlink(self):
        if any(rec.state != "draft" or rec.validation_status in ("waiting", "pending", "validated") for rec in self):
            raise UserError(_("审批中或已确认的计划版本不可删除。"))
        return super().unlink()

    def _check_allow_write_under_validation(self, vals):
        self.ensure_one()
        if self.state == "draft" and self.validation_status == "rejected" and "state" not in vals:
            return True
        return super()._check_allow_write_under_validation(vals)

    def _write_document_state(self, values):
        return self.with_context(sc_document_state_token=_DOCUMENT_STATE_TOKEN).write(values)

    @api.constrains("plan_id", "base_version_id")
    def _check_version_anchor(self):
        for rec in self:
            if rec.base_version_id and (rec.base_version_id == rec or rec.base_version_id.plan_id != rec.plan_id):
                raise ValidationError(_("对比基准版本必须属于同一计划，且不能是当前版本自身。"))

    def action_submit(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("只有草稿状态的计划版本可以提交。"))
            rec._check_version_anchor()
            if not self.env["sc.approval.policy"]._start_submission_review(rec):
                rec.with_context(skip_validation_check=True)._write_document_state({
                    "state": "approved", "reject_reason": False, "approved_by": False,
                    "approved_date": fields.Date.context_today(rec),
                })
        return True

    def action_on_tier_approved(self):
        for rec in self:
            if rec.state == "draft" and rec.review_ids and rec.validation_status == "validated":
                rec._check_version_anchor()
                reviews = rec.review_ids.filtered(lambda review: review.status == "approved" and review.done_by)
                last = reviews.sorted(lambda review: review.write_date or review.create_date, reverse=True)[:1]
                rec.with_context(skip_validation_check=True)._write_document_state({
                    "state": "approved", "reject_reason": False, "approved_date": fields.Date.context_today(rec),
                    "approved_by": last.done_by.id if last else False,
                })

    def action_on_tier_rejected(self):
        for rec in self:
            if rec.state == "draft" and rec.review_ids and rec.validation_status == "rejected":
                reviews = rec.review_ids.filtered(lambda review: review.status == "rejected" and review.comment)
                reason = reviews.sorted(lambda review: review.write_date or review.create_date, reverse=True)[:1].comment if reviews else False
                rec.with_context(skip_validation_check=True)._write_document_state({"reject_reason": reason})

    _sql_constraints = [
        ("uniq_plan_version_no", "unique(plan_id, version_no)", "同一计划下版本号不能重复。"),
    ]


class ScPlanReport(models.Model):
    _name = "sc.plan.report"
    _description = "计划汇报"
    _inherit = ["mail.thread", "mail.activity.mixin", "tier.validation"]
    _state_from = ["submitted"]
    _state_to = ["accepted"]
    _order = "report_date desc, id desc"

    name = fields.Char(string="汇报标题", required=True, default="计划汇报")
    plan_id = fields.Many2one("sc.plan", string="计划", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one("res.company", related="plan_id.company_id", store=True, index=True)
    line_id = fields.Many2one("sc.plan.line", string="计划节点", index=True)
    reporter_id = fields.Many2one("res.users", string="汇报人", default=lambda self: self.env.user, index=True)
    report_date = fields.Date(string="汇报日期", default=fields.Date.context_today, index=True)
    report_type = fields.Selection(
        [("progress", "进度汇报"), ("daily", "日报"), ("weekly", "周报"), ("monthly", "月报"), ("special", "专项报告")],
        string="汇报类型",
        default="progress",
        index=True,
    )
    source_channel = fields.Selection([("pc", "PC"), ("app", "APP"), ("import", "导入"), ("system", "系统")], string="来源端", default="pc", index=True)
    progress_rate = fields.Float(string="汇报完成率(%)")
    summary = fields.Text(string="完成情况")
    risk_note = fields.Text(string="风险说明")
    attachment_ids = fields.Many2many("ir.attachment", string="成果附件")
    approver_id = fields.Many2one("res.users", string="确认人", index=True)
    approved_date = fields.Date(string="确认日期", index=True)
    reject_reason = fields.Text(string="退回原因")
    state = fields.Selection([("draft", "草稿"), ("submitted", "已提交"), ("accepted", "已确认"), ("rejected", "已退回")], default="draft", string="状态", index=True)
    legacy_fact_model = fields.Char(string="来源通用模型", index=True)
    legacy_fact_id = fields.Integer(string="来源通用记录ID", index=True)
    legacy_fact_type = fields.Char(string="来源业务类型", index=True)

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get("state", self.env.context.get("default_state", "draft")) != "draft":
                raise UserError(_("计划汇报必须从草稿通过正式提交和审批流转。"))
            if any(values.get(name, self.env.context.get("default_" + name)) for name in ("approver_id", "approved_date", "reject_reason")):
                raise UserError(_("计划汇报审核结果只能由正式审批动作写入。"))
        return super().create(vals_list)

    def write(self, vals):
        authoritative = self.env.context.get("sc_document_state_token") is _DOCUMENT_STATE_TOKEN
        if not authoritative and {"state", "approver_id", "approved_date", "reject_reason"}.intersection(vals):
            raise UserError(_("计划汇报状态和审核结果只能由正式业务动作写入。"))
        reviewed_fields = {
            "name", "plan_id", "line_id", "company_id", "reporter_id", "report_date",
            "report_type", "source_channel", "progress_rate", "summary", "risk_note", "attachment_ids", "active",
        }
        if not authoritative and reviewed_fields.intersection(vals) and any(
            rec.state not in ("draft", "rejected") or rec.validation_status in ("waiting", "pending", "validated")
            for rec in self
        ):
            raise UserError(_("审批中或已确认的计划汇报内容不可直接修改。"))
        return super().write(vals)

    def _write_document_state(self, values):
        return self.with_context(sc_document_state_token=_DOCUMENT_STATE_TOKEN).write(values)

    @api.constrains("plan_id", "line_id")
    def _check_plan_anchor(self):
        for rec in self:
            if rec.line_id and rec.line_id.plan_id != rec.plan_id:
                raise ValidationError(_("汇报节点必须属于当前计划。"))

    def action_submit(self):
        for rec in self:
            if rec.state not in ("draft", "rejected"):
                raise UserError(_("只有草稿或已退回的计划汇报可以提交。"))
            rec._check_plan_anchor()
            rec._write_document_state({"state": "submitted", "reject_reason": False, "approver_id": False, "approved_date": False})
            if not self.env["sc.approval.policy"]._start_submission_review(rec):
                rec.with_context(skip_validation_check=True)._write_document_state({"state": "accepted", "approved_date": fields.Date.context_today(rec)})
        return True

    def action_on_tier_approved(self):
        for rec in self:
            if rec.state == "submitted" and rec.review_ids and rec.validation_status == "validated":
                rec._check_plan_anchor()
                reviews = rec.review_ids.filtered(lambda review: review.status == "approved" and review.done_by)
                last = reviews.sorted(lambda review: review.write_date or review.create_date, reverse=True)[:1]
                rec.with_context(skip_validation_check=True)._write_document_state({
                    "state": "accepted", "approved_date": fields.Date.context_today(rec),
                    "approver_id": last.done_by.id if last else False,
                })

    def action_on_tier_rejected(self):
        for rec in self:
            if rec.state == "submitted" and rec.review_ids and rec.validation_status == "rejected":
                reviews = rec.review_ids.filtered(lambda review: review.status == "rejected" and review.comment)
                reason = reviews.sorted(lambda review: review.write_date or review.create_date, reverse=True)[:1].comment if reviews else False
                rec.with_context(skip_validation_check=True)._write_document_state({"state": "rejected", "reject_reason": reason})

    @api.constrains("progress_rate")
    def _check_progress_rate(self):
        for rec in self:
            if rec.progress_rate < 0 or rec.progress_rate > 100:
                raise ValidationError(_("汇报完成率必须在 0 到 100 之间。"))


class ScPlanWarningLog(models.Model):
    _name = "sc.plan.warning.log"
    _description = "计划预警日志"
    _order = "warning_date desc, id desc"

    plan_id = fields.Many2one("sc.plan", string="计划", required=True, ondelete="cascade", index=True)
    line_id = fields.Many2one("sc.plan.line", string="计划节点", index=True)
    warning_type = fields.Selection(
        [("due_soon", "即将逾期"), ("overdue", "已逾期"), ("risk", "风险预警")],
        string="预警类型",
        required=True,
        index=True,
    )
    warning_date = fields.Date(string="预警日期", default=fields.Date.context_today, index=True)
    owner_id = fields.Many2one("res.users", string="责任人", index=True)
    message = fields.Text(string="预警内容")
    state = fields.Selection([("open", "未处理"), ("closed", "已关闭")], string="状态", default="open", index=True)
