# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


def _advisory_notification(title, advisories, completed_label):
    suggestions = [item for item in advisories if item and item != completed_label]
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


class ScSiteVariation(models.Model):
    _name = "sc.site.variation"
    _description = "工程签证与现场变更"
    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
        "sc.effective.document.change.mixin",
    ]
    _order = "event_date desc, id desc"

    name = fields.Char("签证单号", required=True, default="新建", copy=False, tracking=True)
    subject = fields.Char("签证/变更事项", required=True, tracking=True)
    project_id = fields.Many2one(
        "project.project", string="项目", required=True, index=True, tracking=True
    )
    company_id = fields.Many2one(
        related="project_id.company_id", store=True, readonly=True, string="所属公司"
    )
    contract_id = fields.Many2one(
        "construction.contract", string="关联合同", index=True, tracking=True
    )
    partner_id = fields.Many2one(
        related="contract_id.partner_id", store=True, readonly=True, string="合同相对方"
    )
    event_type = fields.Selection(
        [
            ("site_visa", "工程签证"),
            ("design_change", "设计变更"),
            ("scope_change", "范围变更"),
            ("instruction", "现场指令"),
            ("other", "其他"),
        ],
        string="业务类型",
        default="site_visa",
        required=True,
        tracking=True,
    )
    variation_scope = fields.Selection(
        [
            ("general", "项目签证变更"),
            ("subcontract", "分包签证费用"),
        ],
        string="费用归属",
        default="general",
        required=True,
        index=True,
        tracking=True,
        help="同一签证变更对象按业务归属投影到项目施工或分包成本工作区。",
    )
    event_date = fields.Date("发生日期", default=fields.Date.context_today, tracking=True)
    location = fields.Char("发生部位")
    cause = fields.Char("发生原因")
    description = fields.Text("事实描述")
    quantity_impact = fields.Text("工程量影响")
    estimated_amount_delta = fields.Monetary(
        "预计价款影响", currency_field="currency_id", tracking=True
    )
    estimated_duration_days = fields.Integer("预计工期影响（天）")
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id.id, required=True
    )
    responsible_id = fields.Many2one(
        "res.users", string="经办人", default=lambda self: self.env.user
    )
    signer_ids = fields.Many2many(
        "res.partner",
        "sc_site_variation_signer_rel",
        "variation_id",
        "partner_id",
        string="确认单位/人员",
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "sc_site_variation_attachment_rel",
        "variation_id",
        "attachment_id",
        string="现场依据",
    )
    contract_change_ids = fields.One2many(
        "sc.contract.change", "source_site_variation_id", string="形成的合同变更", readonly=True
    )
    state = fields.Selection(
        [
            ("draft", "草稿"),
            ("submitted", "待确认"),
            ("confirmed", "已确认"),
            ("rejected", "已驳回"),
            ("cancelled", "已取消"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    processing_advisory = fields.Char("办理建议", compute="_compute_processing_advisory")

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for values in vals_list:
            if values.get("name", "新建") == "新建":
                values["name"] = sequence.next_by_code("sc.site.variation") or _("工程签证")
        return super().create(vals_list)

    @api.depends(
        "contract_id",
        "variation_scope",
        "event_date",
        "location",
        "cause",
        "description",
        "quantity_impact",
        "signer_ids",
        "attachment_ids",
    )
    def _compute_processing_advisory(self):
        for record in self:
            suggestions = []
            if not record.contract_id:
                suggestions.append(
                    "建议关联分包合同"
                    if record.variation_scope == "subcontract"
                    else "建议关联受影响合同"
                )
            if not record.event_date:
                suggestions.append("建议补充发生日期")
            if not record.location:
                suggestions.append("建议补充发生部位")
            if not record.cause:
                suggestions.append("建议补充发生原因")
            if not record.description:
                suggestions.append("建议补充事实描述")
            if not record.quantity_impact:
                suggestions.append("建议补充工程量影响")
            if not record.signer_ids:
                suggestions.append("建议补充确认单位/人员")
            if not record.attachment_ids:
                suggestions.append("建议上传现场依据")
            record.processing_advisory = (
                "；".join(suggestions) if suggestions else "当前签证资料已完善"
            )

    @api.constrains("variation_scope", "contract_id")
    def _check_variation_scope_contract(self):
        for record in self:
            if (
                record.variation_scope == "subcontract"
                and record.contract_id
                and record.contract_id.expense_contract_category_id.sudo().code
                not in ("subcontract", "labor")
            ):
                raise ValidationError(_("分包签证费用只能关联专业分包或劳务分包合同。"))

    def _sc_change_snapshot_fields(self):
        return (
            "project_id",
            "contract_id",
            "variation_scope",
            "event_type",
            "event_date",
            "subject",
            "estimated_amount_delta",
            "estimated_duration_days",
            "signer_ids",
        )

    def _check_project_operator(self):
        if self.env.su or self.env.user.has_group(
            "smart_construction_core.group_sc_cap_project_user"
        ) or self.env.user.has_group("smart_construction_core.group_sc_super_admin"):
            return
        raise UserError(_("你没有权限办理工程签证。"))

    def _check_project_manager(self):
        if self.env.su or self.env.user.has_group(
            "smart_construction_core.group_sc_cap_project_manager"
        ) or self.env.user.has_group("smart_construction_core.group_sc_super_admin"):
            return
        raise UserError(_("只有项目审批人员可以确认工程签证。"))

    def action_submit(self):
        self._check_project_operator()
        if self.filtered(lambda record: record.state != "draft"):
            raise UserError(_("只有草稿状态的工程签证可以提交。"))
        self.write({"state": "submitted"})
        return _advisory_notification(
            "签证已提交，建议继续完善资料",
            self.mapped("processing_advisory"),
            "当前签证资料已完善",
        )

    def action_confirm(self):
        self._check_project_manager()
        if self.filtered(lambda record: record.state != "submitted"):
            raise UserError(_("只有待确认状态的工程签证可以确认。"))
        self.write({"state": "confirmed"})
        self._sc_mark_change_effective()
        return _advisory_notification(
            "签证已确认，建议继续完善资料",
            self.mapped("processing_advisory"),
            "当前签证资料已完善",
        )

    def action_reject(self):
        self._check_project_manager()
        if self.filtered(lambda record: record.state != "submitted"):
            raise UserError(_("只有待确认状态的工程签证可以驳回。"))
        self.write({"state": "rejected"})
        return True

    def action_create_contract_change(self):
        self.ensure_one()
        if self.state != "confirmed":
            raise UserError(_("只有已确认的工程签证才能形成合同变更。"))
        if not self.contract_id:
            raise UserError(_("形成合同变更必须关联受影响合同。"))
        if self.contract_change_ids:
            change = self.contract_change_ids[0]
        else:
            change = self.env["sc.contract.change"].create(
                {
                    "contract_id": self.contract_id.id,
                    "source_site_variation_id": self.id,
                    "subject": self.subject,
                    "reason": self.cause or self.description,
                    "amount_delta": self.estimated_amount_delta,
                    "duration_delta_days": self.estimated_duration_days,
                }
            )
        return {
            "type": "ir.actions.act_window",
            "res_model": "sc.contract.change",
            "res_id": change.id,
            "view_mode": "form",
        }


class ScContractChange(models.Model):
    _name = "sc.contract.change"
    _description = "合同变更"
    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
        "sc.effective.document.change.mixin",
    ]
    _order = "change_date desc, id desc"

    name = fields.Char("变更单号", required=True, default="新建", copy=False, tracking=True)
    contract_id = fields.Many2one(
        "construction.contract", string="合同", required=True, index=True, tracking=True
    )
    project_id = fields.Many2one(
        related="contract_id.project_id", store=True, readonly=True, string="项目"
    )
    company_id = fields.Many2one(
        related="project_id.company_id", store=True, readonly=True, string="所属公司"
    )
    partner_id = fields.Many2one(
        related="contract_id.partner_id", store=True, readonly=True, string="合同相对方"
    )
    source_site_variation_id = fields.Many2one(
        "sc.site.variation", string="来源工程签证", index=True, readonly=True
    )
    subject = fields.Char("变更事项", required=True, tracking=True)
    change_type = fields.Selection(
        [
            ("price", "价款变更"),
            ("scope", "范围变更"),
            ("schedule", "工期变更"),
            ("terms", "条款变更"),
            ("comprehensive", "综合变更"),
        ],
        string="变更类型",
        default="comprehensive",
        required=True,
        tracking=True,
    )
    change_date = fields.Date("变更日期", default=fields.Date.context_today, tracking=True)
    reason = fields.Text("变更原因")
    before_summary = fields.Text("变更前内容")
    after_summary = fields.Text("变更后内容")
    amount_delta = fields.Monetary("价款增减", currency_field="currency_id", tracking=True)
    duration_delta_days = fields.Integer("工期增减（天）")
    currency_id = fields.Many2one(
        related="contract_id.currency_id", store=True, readonly=True
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "sc_contract_change_attachment_rel",
        "change_id",
        "attachment_id",
        string="变更依据",
    )
    settlement_adjustment_ids = fields.One2many(
        "sc.settlement.adjustment", "contract_change_id", string="形成的结算调整", readonly=True
    )
    state = fields.Selection(
        [
            ("draft", "草稿"),
            ("submitted", "待生效"),
            ("effective", "已生效"),
            ("rejected", "已驳回"),
            ("cancelled", "已取消"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    processing_advisory = fields.Char("办理建议", compute="_compute_processing_advisory")

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for values in vals_list:
            if values.get("name", "新建") == "新建":
                values["name"] = sequence.next_by_code("sc.contract.change") or _("合同变更")
        return super().create(vals_list)

    @api.depends(
        "source_site_variation_id",
        "change_date",
        "reason",
        "before_summary",
        "after_summary",
        "attachment_ids",
    )
    def _compute_processing_advisory(self):
        for record in self:
            suggestions = []
            if not record.source_site_variation_id:
                suggestions.append("建议关联来源工程签证（如适用）")
            if not record.change_date:
                suggestions.append("建议补充变更日期")
            if not record.reason:
                suggestions.append("建议补充变更原因")
            if not record.before_summary:
                suggestions.append("建议补充变更前内容")
            if not record.after_summary:
                suggestions.append("建议补充变更后内容")
            if not record.attachment_ids:
                suggestions.append("建议上传变更依据")
            record.processing_advisory = (
                "；".join(suggestions) if suggestions else "当前合同变更资料已完善"
            )

    def _sc_change_snapshot_fields(self):
        return (
            "contract_id",
            "source_site_variation_id",
            "subject",
            "change_type",
            "change_date",
            "amount_delta",
            "duration_delta_days",
            "before_summary",
            "after_summary",
        )

    def _check_contract_operator(self):
        if self.env.su or self.env.user.has_group(
            "smart_construction_core.group_sc_cap_contract_user"
        ) or self.env.user.has_group("smart_construction_core.group_sc_super_admin"):
            return
        raise UserError(_("你没有权限办理合同变更。"))

    def _check_contract_manager(self):
        if self.env.su or self.env.user.has_group(
            "smart_construction_core.group_sc_cap_contract_manager"
        ) or self.env.user.has_group("smart_construction_core.group_sc_super_admin"):
            return
        raise UserError(_("只有合同审批人员可以使合同变更生效。"))

    def action_submit(self):
        self._check_contract_operator()
        if self.filtered(lambda record: record.state != "draft"):
            raise UserError(_("只有草稿状态的合同变更可以提交。"))
        self.write({"state": "submitted"})
        return _advisory_notification(
            "合同变更已提交，建议继续完善资料",
            self.mapped("processing_advisory"),
            "当前合同变更资料已完善",
        )

    def action_effective(self):
        self._check_contract_manager()
        if self.filtered(lambda record: record.state != "submitted"):
            raise UserError(_("只有待生效状态的合同变更可以生效。"))
        self.write({"state": "effective"})
        self._sc_mark_change_effective()
        return _advisory_notification(
            "合同变更已生效，建议继续完善资料",
            self.mapped("processing_advisory"),
            "当前合同变更资料已完善",
        )

    def action_reject(self):
        self._check_contract_manager()
        if self.filtered(lambda record: record.state != "submitted"):
            raise UserError(_("只有待生效状态的合同变更可以驳回。"))
        self.write({"state": "rejected"})
        return True

    def action_create_settlement_adjustment(self):
        self.ensure_one()
        if self.state != "effective":
            raise UserError(_("只有已生效的合同变更才能形成结算调整。"))
        if not self.amount_delta:
            raise UserError(_("该合同变更没有价款影响，无需形成结算调整。"))
        if self.settlement_adjustment_ids:
            adjustment = self.settlement_adjustment_ids[0]
        else:
            adjustment = self.env["sc.settlement.adjustment"].create(
                {
                    "project_id": self.project_id.id,
                    "contract_id": self.contract_id.id,
                    "partner_id": self.partner_id.id,
                    "item_name": self.subject,
                    "adjustment_type": "addition" if self.amount_delta > 0 else "deduction",
                    "amount": abs(self.amount_delta),
                    "currency_id": self.currency_id.id,
                    "contract_change_id": self.id,
                }
            )
        return {
            "type": "ir.actions.act_window",
            "res_model": "sc.settlement.adjustment",
            "res_id": adjustment.id,
            "view_mode": "form",
        }


class ConstructionContractChangeSummary(models.Model):
    _inherit = "construction.contract"

    change_ids = fields.One2many("sc.contract.change", "contract_id", string="合同变更")

    @api.depends("amount_total", "change_ids.state", "change_ids.amount_delta")
    def _compute_final_amount(self):
        for contract in self:
            delta = sum(
                contract.change_ids.filtered(lambda change: change.state == "effective").mapped(
                    "amount_delta"
                )
            )
            contract.amount_change = delta
            contract.amount_final = (contract.amount_total or 0.0) + delta
