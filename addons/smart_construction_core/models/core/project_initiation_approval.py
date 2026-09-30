# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


_INITIATION_APPROVAL_TOKEN = object()


class ProjectInitiationApproval(models.Model):
    _name = "project.project"
    _inherit = ["project.project", "tier.validation"]
    _state_field = "sc_approval_state"
    _state_from = ["draft"]
    _state_to = ["approved"]

    sc_approval_state = fields.Selection(
        [("draft", "待提交"), ("approved", "立项已通过")],
        string="立项审批", default="draft", required=True, readonly=True, copy=False,
    )
    reject_reason = fields.Text(string="驳回原因", readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        if any(values.get("sc_approval_state", "draft") != "draft" for values in vals_list):
            raise UserError("项目立项状态必须通过提交和审批动作产生。")
        return super().create(vals_list)

    def write(self, vals):
        if "sc_approval_state" in vals and self.env.context.get("sc_initiation_approval_token") is not _INITIATION_APPROVAL_TOKEN:
            raise UserError("项目立项状态必须通过提交和审批动作产生。")
        return super().write(vals)

    def _check_initiation_ready(self):
        for project in self:
            if project.lifecycle_state != "draft":
                raise UserError("只有未启动的草稿项目可以提交立项审批。")
            if not (project.name or "").strip() or not project.company_id:
                raise UserError("请先填写项目名称并确认所属公司。")

    def request_validation(self):
        self._check_initiation_ready()
        return super().request_validation()

    def action_sc_submit(self):
        if not (
            self.env.user.has_group("smart_construction_core.group_sc_cap_project_user")
            or self.env.user.has_group("smart_construction_core.group_sc_cap_project_manager")
            or self.env.user.has_group("smart_construction_core.group_sc_super_admin")
        ):
            raise UserError("你没有权限推进项目阶段。")
        for project in self:
            project._check_initiation_ready()
            if project.sc_approval_state != "draft":
                raise UserError("项目立项已通过，请使用启动项目继续办理。")
            if not self.env["sc.approval.policy"]._start_submission_review(project):
                project._complete_initiation_approval()
        return True

    def _complete_initiation_approval(self):
        self.ensure_one()
        self.with_context(skip_validation_check=True, sc_initiation_approval_token=_INITIATION_APPROVAL_TOKEN).write({"sc_approval_state": "approved", "reject_reason": False})
        self.message_post(body="项目立项已通过，尚未启动。")

    def action_on_tier_approved(self):
        for project in self:
            if project.sc_approval_state == "draft" and project.review_ids and project.validation_status == "validated":
                project._check_initiation_ready()
                project._complete_initiation_approval()

    def action_on_tier_rejected(self):
        for project in self:
            if project.sc_approval_state == "draft" and project.review_ids and project.validation_status == "rejected":
                reviews = project.review_ids.filtered(lambda review: review.status == "rejected" and review.comment)
                reason = reviews.sorted(lambda review: review.write_date or review.create_date, reverse=True)[:1].comment if reviews else False
                project.with_context(skip_validation_check=True).write({"reject_reason": reason})
                project.message_post(body="项目立项审批已驳回。")

    def _assert_initiation_approved(self):
        for project in self:
            self.env["sc.approval.policy"]._assert_submission_approved(project, ("approved",))

    def action_sc_start(self):
        for project in self:
            if project.lifecycle_state != "draft":
                raise UserError("只有未启动的草稿项目可以启动；暂停项目请使用恢复项目。")
            project._assert_initiation_approved()
        advisories = self._sc_lifecycle_advisories("in_progress")
        self.action_set_lifecycle_state("in_progress")
        if advisories:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "项目已启动",
                    "message": "；".join(advisories),
                    "type": "warning",
                    "sticky": False,
                },
            }
        return True

