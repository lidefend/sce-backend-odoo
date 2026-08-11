# -*- coding: utf-8 -*-
import ast

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class ScCurrentAccountWorkspace(models.TransientModel):
    _name = "sc.current.account.workspace"
    _description = "往来款办理工作台"

    project_id = fields.Many2one("project.project", string="项目", required=True)
    partner_id = fields.Many2one("res.partner", string="承包人/往来单位")
    business_date = fields.Date(string="办理日期", default=fields.Date.context_today)
    note = fields.Text(string="办理说明")
    processing_advisory = fields.Char(string="办理提示", compute="_compute_processing_advisory")

    @api.depends("partner_id", "business_date", "note")
    def _compute_processing_advisory(self):
        for record in self:
            suggestions = []
            if not record.partner_id:
                suggestions.append("办理承包人借还款前请选择承包人/往来单位")
            if not record.business_date:
                suggestions.append("建议补充办理日期")
            if not record.note:
                suggestions.append("建议补充办理说明")
            record.processing_advisory = "；".join(suggestions) if suggestions else "往来办理上下文已完善"

    def _check_finance_operator(self):
        if (
            self.env.su
            or self.env.user.has_group("smart_construction_core.group_sc_cap_finance_user")
            or self.env.user.has_group("smart_construction_core.group_sc_cap_finance_manager")
            or self.env.user.has_group("smart_construction_core.group_sc_super_admin")
        ):
            self.project_id.check_access_rights("read")
            self.project_id.check_access_rule("read")
            return
        raise AccessError(_("你没有往来款办理权限。"))

    def _action_values(self, action_xmlid, label, *, require_partner=False):
        self.ensure_one()
        self._check_finance_operator()
        if require_partner and not self.partner_id:
            raise UserError(_("办理承包人借还款必须先选择承包人/往来单位。"))
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
                "current_project_id": self.project_id.id,
            }
        )
        if self.partner_id:
            context.update(
                {
                    "default_partner_id": self.partner_id.id,
                    "current_partner_id": self.partner_id.id,
                }
            )
        if self.business_date:
            context.update(
                {
                    "default_document_date": self.business_date,
                    "default_date_claim": self.business_date,
                    "default_operation_date": self.business_date,
                }
            )
        if self.note:
            context.update(
                {
                    "default_note": self.note,
                    "default_purpose": self.note,
                    "default_summary": self.note,
                    "default_operation_reason": self.note,
                }
            )
        result.update(
            {
                "name": "%s / %s" % (self.project_id.display_name, label),
                "views": [(False, "form")],
                "view_mode": "form",
                "res_id": False,
                "target": "current",
                "context": context,
            }
        )
        return result

    def action_project_borrow_company(self):
        return self._action_values(
            "smart_construction_core.action_sc_financing_loan_project_borrow_company",
            "项目借公司款",
        )

    def action_project_repay_company(self):
        return self._action_values(
            "smart_construction_core.action_sc_expense_claim_project_repay_company",
            "项目还公司款",
        )

    def action_contractor_borrow_project(self):
        return self._action_values(
            "smart_construction_core.action_sc_financing_loan_contractor_project_borrow",
            "承包人借项目款",
            require_partner=True,
        )

    def action_contractor_repay_project(self):
        return self._action_values(
            "smart_construction_core.action_sc_expense_claim_contractor_project_repay",
            "承包人还项目款",
            require_partner=True,
        )

    def action_account_transfer(self):
        return self._action_values(
            "smart_construction_core.action_sc_fund_account_between_user",
            "账户间资金调拨",
        )

    def action_view_current_account(self):
        self.ensure_one()
        self._check_finance_operator()
        action = self.env.ref(
            "smart_construction_core.action_sc_finance_project_counterparty_position",
            raise_if_not_found=False,
        )
        if not action:
            raise UserError(_("项目与对象资金往来台账入口不存在。"))
        result = action.sudo().read()[0]
        domain = [("project_id", "=", self.project_id.id)]
        if self.partner_id:
            domain.append(("partner_id", "=", self.partner_id.id))
        result.update(
            {
                "name": "%s / 往来款台账" % self.project_id.display_name,
                "domain": domain,
                "context": {"search_default_group_counterparty_type": 1},
                "target": "current",
            }
        )
        return result
