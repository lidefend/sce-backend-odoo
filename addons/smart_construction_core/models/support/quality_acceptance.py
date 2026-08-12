# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ScQualityAcceptance(models.Model):
    _name = "sc.quality.acceptance"
    _description = "质量验收"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "acceptance_date desc, id desc"

    name = fields.Char("验收名称", required=True, tracking=True)
    project_id = fields.Many2one(
        "project.project", string="项目", required=True, index=True, tracking=True
    )
    company_id = fields.Many2one(
        related="project_id.company_id", store=True, readonly=True, string="所属公司"
    )
    acceptance_type = fields.Selection(
        [
            ("inspection_lot", "检验批验收"),
            ("hidden_work", "隐蔽工程验收"),
            ("subsection", "分项工程验收"),
            ("division", "分部工程验收"),
            ("completion", "竣工验收"),
            ("other", "其他验收"),
        ],
        string="验收类型",
        default="inspection_lot",
        required=True,
        tracking=True,
    )
    acceptance_date = fields.Date("验收日期", default=fields.Date.context_today, tracking=True)
    location = fields.Char("验收部位")
    standard = fields.Text("验收依据/标准")
    responsible_id = fields.Many2one("res.users", string="责任人", default=lambda self: self.env.user)
    participant_ids = fields.Many2many(
        "res.users", "sc_quality_acceptance_user_rel", "acceptance_id", "user_id", string="验收人员"
    )
    result = fields.Selection(
        [
            ("pending", "待形成结论"),
            ("passed", "合格"),
            ("conditional", "有条件通过"),
            ("failed", "不合格"),
        ],
        string="验收结论",
        default="pending",
        required=True,
        tracking=True,
    )
    conclusion = fields.Text("验收意见")
    rectification_deadline = fields.Date("整改期限")
    issue_ids = fields.Many2many(
        "sc.quality.issue",
        "sc_quality_acceptance_issue_rel",
        "acceptance_id",
        "issue_id",
        string="关联质量问题",
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "sc_quality_acceptance_attachment_rel",
        "acceptance_id",
        "attachment_id",
        string="验收资料",
    )
    state = fields.Selection(
        [("draft", "草稿"), ("confirmed", "已确认"), ("cancelled", "已取消")],
        default="draft",
        required=True,
        tracking=True,
    )
    processing_advisory = fields.Char("办理建议", compute="_compute_processing_advisory")

    @api.depends(
        "acceptance_date",
        "location",
        "standard",
        "participant_ids",
        "conclusion",
        "attachment_ids",
        "result",
        "rectification_deadline",
    )
    def _compute_processing_advisory(self):
        for record in self:
            suggestions = []
            if not record.acceptance_date:
                suggestions.append("建议补充验收日期")
            if not record.location:
                suggestions.append("建议补充验收部位")
            if not record.standard:
                suggestions.append("建议补充验收依据/标准")
            if not record.participant_ids:
                suggestions.append("建议补充验收人员")
            if not record.conclusion:
                suggestions.append("建议补充验收意见")
            if not record.attachment_ids:
                suggestions.append("建议上传验收资料")
            if record.result in ("conditional", "failed") and not record.rectification_deadline:
                suggestions.append("建议设置整改期限")
            record.processing_advisory = (
                "；".join(suggestions) if suggestions else "当前验收资料已完善"
            )

    def _check_operator(self):
        if self.env.su or self.env.user.has_group(
            "smart_construction_core.group_sc_cap_project_user"
        ) or self.env.user.has_group("smart_construction_core.group_sc_super_admin"):
            return
        raise UserError(_("你没有权限办理质量验收。"))

    def action_confirm(self):
        self._check_operator()
        invalid = self.filtered(lambda record: record.state != "draft")
        if invalid:
            raise UserError(_("只有草稿状态的质量验收可以确认。"))
        if self.filtered(lambda record: record.result == "pending"):
            raise UserError(_("确认验收必须选择验收结论，否则系统无法表达验收结果。"))
        self.write({"state": "confirmed"})
        suggestions = [
            item for item in self.mapped("processing_advisory") if item != "当前验收资料已完善"
        ]
        if suggestions:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "验收已确认，建议继续完善资料",
                    "message": "；".join(dict.fromkeys(suggestions)),
                    "type": "warning",
                    "sticky": False,
                },
            }
        return True

    def action_cancel(self):
        self._check_operator()
        self.filtered(lambda record: record.state != "cancelled").write({"state": "cancelled"})
        return True

    def action_reset_draft(self):
        self._check_operator()
        self.filtered(lambda record: record.state == "cancelled").write({"state": "draft"})
        return True
