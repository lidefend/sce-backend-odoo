# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import AccessError
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval
from odoo.addons.smart_core.delivery.runtime_route_authority import build_runtime_route_authority


class ProjectProjectFinancial(models.Model):
    _inherit = "project.project"
    _sc_readonly_navigation_button_methods = ("action_open_project_contracts",)

    sc_project_contract_entry_available = fields.Boolean(
        string="项目合同入口可用", compute="_compute_project_contract_entry_available",
        help="仅在当前账号拥有已发布的合同阅读入口时提供关联导航。",
    )

    def _project_contract_entry(self):
        authority = build_runtime_route_authority(self.env)
        for bucket in ("contextual_actions", "primary_actions", "role_home_actions"):
            for row in authority.get(bucket) or []:
                if (isinstance(row, dict) and row.get("model") == "construction.contract"
                        and row.get("allowed_operation") == "read" and row.get("action_id")
                        and not (row.get("context_requirements") or {}).get("required_query")):
                    return row
        return None

    @api.depends_context("uid", "company", "allowed_company_ids")
    def _compute_project_contract_entry_available(self):
        available = bool(self._project_contract_entry())
        for project in self:
            project.sc_project_contract_entry_available = available

    def action_open_project_budgets(self):
        """从项目详情页打开当前项目的预算列表。"""
        self.ensure_one()
        action = self.env.ref("smart_construction_core.action_project_budget").read()[0]

        action["domain"] = [("project_id", "=", self.id)]
        ctx = dict(self.env.context)
        ctx.update({"default_project_id": self.id})
        action["context"] = ctx
        return action

    def action_open_project_contracts(self):
        """从项目详情页打开当前项目的合同列表。"""
        self.ensure_one()
        self.check_access_rights("read")
        self.check_access_rule("read")
        self.env["construction.contract"].check_access_rights("read")
        entry = self._project_contract_entry()
        if not entry:
            raise AccessError(_("当前账号的发布范围未提供项目合同列表入口。"))
        action = self.env["ir.actions.act_window"].browse(entry["action_id"]).read()[0]

        ctx = dict(self.env.context)
        declared_context = action.get("context") or {}
        if isinstance(declared_context, str):
            declared_context = safe_eval(declared_context, {"uid": self.env.uid, "context": ctx,
                "active_id": self.id, "active_ids": self.ids, "active_model": self._name})
        ctx.update(declared_context)
        ctx["default_project_id"] = self.id
        original_domain = action.get("domain") or []
        if isinstance(original_domain, str):
            original_domain = safe_eval(original_domain, {"uid": self.env.uid, "context": ctx})
        action["domain"] = expression.AND([original_domain, [("project_id", "=", self.id)]])
        if entry.get("menu_id"):
            action["menu_id"] = entry["menu_id"]
        action["context"] = ctx
        return action
