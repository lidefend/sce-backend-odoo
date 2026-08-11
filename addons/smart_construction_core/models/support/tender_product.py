# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class TenderOpportunity(models.Model):
    _name = "tender.opportunity"
    _description = "招标信息"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "deadline asc, id desc"

    name = fields.Char("招标项目名称", required=True, tracking=True)
    code = fields.Char("招标编号", index=True, tracking=True)
    company_id = fields.Many2one(
        "res.company", string="所属公司", required=True, default=lambda self: self.env.company
    )
    owner_id = fields.Many2one("res.partner", string="招标人/业主", tracking=True)
    contact_name = fields.Char("联系人")
    contact_phone = fields.Char("联系电话")
    location = fields.Char("项目地点")
    publish_date = fields.Date("发布日期")
    deadline = fields.Datetime("投标截止时间", tracking=True)
    estimated_amount = fields.Monetary("估算金额", currency_field="currency_id")
    currency_id = fields.Many2one(
        "res.currency", related="company_id.currency_id", store=True, readonly=True
    )
    source = fields.Char("信息来源")
    qualification_requirements = fields.Text("资格要求")
    note = fields.Text("备注")
    project_id = fields.Many2one("project.project", string="关联项目", tracking=True)
    bid_id = fields.Many2one("tender.bid", string="关联投标项目", readonly=True, copy=False)
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "tender_opportunity_attachment_rel",
        "opportunity_id",
        "attachment_id",
        string="招标资料",
    )
    state = fields.Selection(
        [
            ("draft", "待评估"),
            ("following", "跟进中"),
            ("converted", "已转投标"),
            ("abandoned", "已放弃"),
        ],
        string="状态",
        default="draft",
        required=True,
        tracking=True,
    )
    processing_advisory = fields.Char("办理建议", compute="_compute_processing_advisory")

    @api.depends("code", "owner_id", "location", "publish_date", "deadline", "source")
    def _compute_processing_advisory(self):
        for record in self:
            suggestions = []
            if not record.code:
                suggestions.append("建议补充招标编号")
            if not record.owner_id:
                suggestions.append("建议补充招标人/业主")
            if not record.location:
                suggestions.append("建议补充项目地点")
            if not record.publish_date:
                suggestions.append("建议补充发布日期")
            if not record.deadline:
                suggestions.append("建议补充投标截止时间")
            if not record.source:
                suggestions.append("建议补充信息来源")
            record.processing_advisory = (
                "；".join(suggestions) if suggestions else "当前招标信息已完善"
            )

    def _check_operator(self):
        if self.env.su or self.env.user.has_group(
            "smart_construction_core.group_sc_cap_project_user"
        ) or self.env.user.has_group("smart_construction_core.group_sc_super_admin"):
            return
        raise UserError(_("你没有权限办理招标信息。"))

    def action_follow(self):
        self._check_operator()
        self.filtered(lambda item: item.state == "draft").write({"state": "following"})
        return True

    def action_abandon(self):
        self._check_operator()
        self.filtered(lambda item: item.state in ("draft", "following")).write(
            {"state": "abandoned"}
        )
        return True

    def action_create_bid(self):
        self.ensure_one()
        self._check_operator()
        if self.bid_id:
            return {
                "type": "ir.actions.act_window",
                "res_model": "tender.bid",
                "res_id": self.bid_id.id,
                "view_mode": "form",
            }
        if not self.project_id:
            raise UserError(_("生成投标项目需要先关联项目；其余招标信息可按当前节奏继续完善。"))
        bid = self.env["tender.bid"].create(
            {
                "tender_name": self.name,
                "project_id": self.project_id.id,
                "owner_id": self.owner_id.id,
                "deadline": self.deadline,
                "bid_amount": self.estimated_amount,
                "note": self.note,
            }
        )
        self.write({"bid_id": bid.id, "state": "converted"})
        return {
            "type": "ir.actions.act_window",
            "res_model": "tender.bid",
            "res_id": bid.id,
            "view_mode": "form",
        }


class TenderDocument(models.Model):
    _name = "tender.document"
    _description = "标书文件"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "bid_id, sequence, id desc"

    sequence = fields.Integer("序号", default=10)
    name = fields.Char("文件名称", required=True, tracking=True)
    bid_id = fields.Many2one(
        "tender.bid", string="投标项目", required=True, ondelete="cascade", tracking=True
    )
    project_id = fields.Many2one(related="bid_id.project_id", store=True, readonly=True)
    company_id = fields.Many2one(
        related="project_id.company_id", store=True, readonly=True, string="所属公司"
    )
    document_type = fields.Selection(
        [
            ("qualification", "资格文件"),
            ("technical", "技术标"),
            ("commercial", "商务标"),
            ("other", "其他"),
        ],
        string="文件类型",
        default="technical",
        required=True,
        tracking=True,
    )
    version = fields.Char("版本")
    responsible_id = fields.Many2one("res.users", string="负责人", default=lambda self: self.env.user)
    deadline = fields.Datetime("计划完成时间")
    submitted_at = fields.Datetime("提交时间", readonly=True)
    note = fields.Text("编制说明")
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "tender_document_attachment_rel",
        "document_id",
        "attachment_id",
        string="文件附件",
    )
    state = fields.Selection(
        [
            ("draft", "草稿"),
            ("preparing", "编制中"),
            ("reviewed", "已复核"),
            ("submitted", "已提交"),
            ("archived", "已归档"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    processing_advisory = fields.Char("办理建议", compute="_compute_processing_advisory")

    @api.depends("version", "responsible_id", "deadline", "attachment_ids")
    def _compute_processing_advisory(self):
        for record in self:
            suggestions = []
            if not record.version:
                suggestions.append("建议补充版本号")
            if not record.responsible_id:
                suggestions.append("建议明确负责人")
            if not record.deadline:
                suggestions.append("建议补充计划完成时间")
            if not record.attachment_ids:
                suggestions.append("建议上传标书文件")
            record.processing_advisory = (
                "；".join(suggestions) if suggestions else "当前标书资料已完善"
            )

    def _check_operator(self):
        if self.env.su or self.env.user.has_group(
            "smart_construction_core.group_sc_cap_project_user"
        ) or self.env.user.has_group("smart_construction_core.group_sc_super_admin"):
            return
        raise UserError(_("你没有权限办理标书文件。"))

    def _set_state(self, source_states, target_state):
        self._check_operator()
        invalid = self.filtered(lambda item: item.state not in source_states)
        if invalid:
            raise UserError(_("当前状态不能执行该标书办理操作。"))
        values = {"state": target_state}
        if target_state == "submitted":
            values["submitted_at"] = fields.Datetime.now()
        self.write(values)
        suggestions = [
            item for item in self.mapped("processing_advisory") if item != "当前标书资料已完善"
        ]
        if suggestions:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "办理已完成，建议继续完善资料",
                    "message": "；".join(dict.fromkeys(suggestions)),
                    "type": "warning",
                    "sticky": False,
                },
            }
        return True

    def action_start(self):
        return self._set_state(("draft",), "preparing")

    def action_review(self):
        return self._set_state(("draft", "preparing"), "reviewed")

    def action_submit(self):
        return self._set_state(("draft", "preparing", "reviewed"), "submitted")

    def action_archive(self):
        return self._set_state(("submitted",), "archived")
