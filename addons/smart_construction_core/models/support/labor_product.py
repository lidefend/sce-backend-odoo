# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


def _warning_notification(title, suggestions):
    if not suggestions:
        return True
    return {
        "type": "ir.actions.client",
        "tag": "display_notification",
        "params": {
            "title": title,
            "message": "；".join(dict.fromkeys(suggestions)),
            "type": "warning",
            "sticky": False,
        },
    }


class ScLaborWorker(models.Model):
    _name = "sc.labor.worker"
    _description = "劳务实名人员"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "project_id, labor_team, name"

    name = fields.Char("姓名", required=True, tracking=True)
    project_id = fields.Many2one(
        "project.project", string="项目", required=True, index=True, tracking=True
    )
    company_id = fields.Many2one(
        related="project_id.company_id", store=True, readonly=True, string="所属公司"
    )
    contractor_id = fields.Many2one("res.partner", string="劳务单位", index=True, tracking=True)
    labor_team = fields.Char("班组", index=True, tracking=True)
    trade = fields.Char("工种", index=True)
    id_type = fields.Selection(
        [("id_card", "居民身份证"), ("passport", "护照"), ("other", "其他证件")],
        string="证件类型",
        default="id_card",
    )
    id_number = fields.Char("证件号码", index=True, tracking=True)
    phone = fields.Char("联系电话")
    gender = fields.Selection([("male", "男"), ("female", "女"), ("other", "其他")], string="性别")
    entry_date = fields.Date("进场日期")
    exit_date = fields.Date("退场日期")
    emergency_contact = fields.Char("紧急联系人")
    emergency_phone = fields.Char("紧急联系电话")
    state = fields.Selection(
        [("draft", "待进场"), ("active", "在场"), ("exited", "已退场")],
        default="draft",
        required=True,
        tracking=True,
    )
    note = fields.Text("备注")
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "sc_labor_worker_attachment_rel",
        "worker_id",
        "attachment_id",
        string="实名资料",
    )
    processing_advisory = fields.Char("办理建议", compute="_compute_processing_advisory")

    _sql_constraints = [
        (
            "project_identity_unique",
            "unique(project_id, id_type, id_number)",
            "同一项目下相同证件号码的实名人员不能重复登记。",
        )
    ]

    @api.depends(
        "contractor_id", "labor_team", "trade", "id_number", "phone", "entry_date", "attachment_ids"
    )
    def _compute_processing_advisory(self):
        for worker in self:
            suggestions = []
            if not worker.id_number:
                suggestions.append("建议补充证件号码")
            if not worker.contractor_id:
                suggestions.append("建议补充劳务单位")
            if not worker.labor_team:
                suggestions.append("建议补充班组")
            if not worker.trade:
                suggestions.append("建议补充工种")
            if not worker.phone:
                suggestions.append("建议补充联系电话")
            if not worker.entry_date:
                suggestions.append("建议补充进场日期")
            if not worker.attachment_ids:
                suggestions.append("建议上传实名资料")
            worker.processing_advisory = (
                "；".join(suggestions) if suggestions else "当前实名信息已完善"
            )

    def _check_operator(self):
        if self.env.su or self.env.user.has_group(
            "smart_construction_core.group_sc_cap_project_user"
        ) or self.env.user.has_group("smart_construction_core.group_sc_super_admin"):
            return
        raise UserError(_("你没有权限维护劳务实名人员。"))

    def action_activate(self):
        self._check_operator()
        invalid = self.filtered(lambda worker: worker.state != "draft")
        if invalid:
            raise UserError(_("只有待进场人员可以办理进场。"))
        today = fields.Date.context_today(self)
        for worker in self:
            values = {"state": "active"}
            if not worker.entry_date:
                values["entry_date"] = today
            worker.write(values)
        suggestions = [
            item for item in self.mapped("processing_advisory") if item != "当前实名信息已完善"
        ]
        return _warning_notification("进场办理已完成，建议继续完善实名信息", suggestions)

    def action_exit(self):
        self._check_operator()
        invalid = self.filtered(lambda worker: worker.state != "active")
        if invalid:
            raise UserError(_("只有在场人员可以办理退场。"))
        self.write({"state": "exited", "exit_date": fields.Date.context_today(self)})
        return True


class ScLaborDeduction(models.Model):
    _name = "sc.labor.deduction"
    _description = "劳务扣款"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "deduction_date desc, id desc"

    name = fields.Char("扣款单号", required=True, default="新建", copy=False, tracking=True)
    project_id = fields.Many2one(
        "project.project", string="项目", required=True, index=True, tracking=True
    )
    company_id = fields.Many2one(
        related="project_id.company_id", store=True, readonly=True, string="所属公司"
    )
    deduction_date = fields.Date("扣款日期", default=fields.Date.context_today, tracking=True)
    contractor_id = fields.Many2one("res.partner", string="劳务单位", index=True, tracking=True)
    labor_team = fields.Char("班组", index=True)
    worker_id = fields.Many2one("sc.labor.worker", string="实名人员", index=True)
    usage_id = fields.Many2one("sc.labor.usage", string="关联用工记录", index=True)
    deduction_type = fields.Selection(
        [
            ("quality", "质量扣款"),
            ("safety", "安全扣款"),
            ("attendance", "考勤扣款"),
            ("material", "材料扣款"),
            ("other", "其他扣款"),
        ],
        string="扣款类型",
        default="other",
        required=True,
        tracking=True,
    )
    reason = fields.Char("扣款事由", tracking=True)
    amount = fields.Monetary("扣款金额", currency_field="currency_id", required=True, tracking=True)
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id.id, required=True
    )
    state = fields.Selection(
        [("draft", "草稿"), ("confirmed", "已确认"), ("cancelled", "已取消")],
        default="draft",
        required=True,
        tracking=True,
    )
    note = fields.Text("备注")
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "sc_labor_deduction_attachment_rel",
        "deduction_id",
        "attachment_id",
        string="扣款依据",
    )
    processing_advisory = fields.Char("办理建议", compute="_compute_processing_advisory")

    _sql_constraints = [
        ("amount_nonnegative", "CHECK(amount >= 0)", "劳务扣款金额不能为负数。")
    ]

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for values in vals_list:
            if values.get("name", "新建") == "新建":
                values["name"] = sequence.next_by_code("sc.labor.deduction") or _("劳务扣款")
        return super().create(vals_list)

    @api.depends(
        "contractor_id", "labor_team", "worker_id", "usage_id", "reason", "amount", "attachment_ids"
    )
    def _compute_processing_advisory(self):
        for deduction in self:
            suggestions = []
            if not deduction.contractor_id:
                suggestions.append("建议补充劳务单位")
            if not deduction.labor_team:
                suggestions.append("建议补充班组")
            if not deduction.worker_id and not deduction.usage_id:
                suggestions.append("建议关联实名人员或用工记录")
            if not deduction.reason:
                suggestions.append("建议补充扣款事由")
            if not deduction.amount:
                suggestions.append("建议补充扣款金额")
            if not deduction.attachment_ids:
                suggestions.append("建议上传扣款依据")
            deduction.processing_advisory = (
                "；".join(suggestions) if suggestions else "当前扣款资料已完善"
            )

    def _check_operator(self):
        if self.env.su or self.env.user.has_group(
            "smart_construction_core.group_sc_cap_project_user"
        ) or self.env.user.has_group("smart_construction_core.group_sc_super_admin"):
            return
        raise UserError(_("你没有权限办理劳务扣款。"))

    def action_confirm(self):
        self._check_operator()
        invalid = self.filtered(lambda deduction: deduction.state != "draft")
        if invalid:
            raise UserError(_("只有草稿状态的劳务扣款可以确认。"))
        if self.filtered(lambda deduction: deduction.amount <= 0):
            raise UserError(_("确认劳务扣款必须填写大于零的金额，否则无法形成成本事实。"))
        self.write({"state": "confirmed"})
        suggestions = [
            item for item in self.mapped("processing_advisory") if item != "当前扣款资料已完善"
        ]
        return _warning_notification("扣款已确认，建议继续完善依据", suggestions)

    def action_cancel(self):
        self._check_operator()
        self.filtered(lambda deduction: deduction.state != "cancelled").write(
            {"state": "cancelled"}
        )
        return True

