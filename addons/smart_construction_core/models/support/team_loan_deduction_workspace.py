# -*- coding: utf-8 -*-
import ast

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class ScTeamLoanDeductionWorkspace(models.TransientModel):
    _name = "sc.team.loan.deduction.workspace"
    _description = "班组借扣款办理工作台"

    project_id = fields.Many2one("project.project", string="项目", required=True)
    partner_id = fields.Many2one("res.partner", string="班组/承包人", required=True)
    business_date = fields.Date("办理日期", default=fields.Date.context_today)
    note = fields.Text("办理说明")
    processing_advisory = fields.Char("办理提示", compute="_compute_processing_advisory")

    @api.depends("business_date", "note")
    def _compute_processing_advisory(self):
        for record in self:
            suggestions = []
            if not record.business_date:
                suggestions.append("建议补充办理日期")
            if not record.note:
                suggestions.append("建议补充办理说明")
            record.processing_advisory = "；".join(suggestions) if suggestions else "办理上下文已完善"

    def _check_project_operator(self):
        is_manager = (
            self.env.su
            or self.env.user.has_group("smart_construction_core.group_sc_cap_project_manager")
            or self.env.user.has_group("smart_construction_core.group_sc_super_admin")
        )
        if is_manager:
            return
        if self.env.user.has_group("smart_construction_core.group_sc_cap_project_user"):
            project = self.project_id.sudo()
            is_member = (
                project.user_id == self.env.user
                or self.env.user.partner_id in project.message_partner_ids
            )
            if not is_member:
                raise AccessError(_("你不能为当前非本人负责或未关注的项目办理班组借扣款。"))
            return
        raise AccessError(_("你没有项目班组借扣款办理权限。"))

    def _action_values(self, action_xmlid, label):
        self.ensure_one()
        self._check_project_operator()
        action = self.env.ref(action_xmlid, raise_if_not_found=False)
        if not action:
            raise UserError(_("正式办理入口不存在，请检查产品配置。"))
        result = action.sudo().read()[0]
        raw_context = result.get("context") or {}
        if isinstance(raw_context, str):
            try:
                raw_context = ast.literal_eval(raw_context)
            except (SyntaxError, ValueError):
                raw_context = {}
        context = dict(raw_context) if isinstance(raw_context, dict) else {}
        context.update(
            {
                "default_project_id": self.project_id.id,
                "default_partner_id": self.partner_id.id,
                "current_project_id": self.project_id.id,
                "current_partner_id": self.partner_id.id,
            }
        )
        if self.business_date:
            context.update(
                {
                    "default_document_date": self.business_date,
                    "default_date_claim": self.business_date,
                }
            )
        if self.note:
            context.update({"default_note": self.note, "default_purpose": self.note})
        result.update(
            {
                "name": "%s / %s / %s" % (self.project_id.display_name, self.partner_id.display_name, label),
                "views": [(False, "form")],
                "view_mode": "form",
                "res_id": False,
                "target": "current",
                "context": context,
            }
        )
        return result

    def action_register_loan(self):
        return self._action_values(
            "smart_construction_core.action_sc_financing_loan_contractor_project_borrow",
            "借款登记",
        )

    def action_register_deduction(self):
        return self._action_values(
            "smart_construction_core.action_sc_expense_claim_deduction_bill",
            "扣款登记",
        )

    def action_view_account(self):
        self.ensure_one()
        self._check_project_operator()
        action = self.env.ref(
            "smart_construction_core.action_sc_finance_project_counterparty_position",
            raise_if_not_found=False,
        )
        if not action:
            raise UserError(_("项目往来台账入口不存在。"))
        result = action.sudo().read()[0]
        result.update(
            {
                "name": "%s / %s / 借扣款台账" % (
                    self.project_id.display_name,
                    self.partner_id.display_name,
                ),
                "domain": [
                    ("project_id", "=", self.project_id.id),
                    ("partner_id", "=", self.partner_id.id),
                ],
                "context": {"search_default_counterparty_partner": 1},
                "target": "current",
            }
        )
        return result
