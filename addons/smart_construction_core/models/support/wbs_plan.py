# -*- coding: utf-8 -*-
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ConstructionWbsPlan(models.Model):
    _name = "construction.wbs.plan"
    _description = "WBS 版本"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "project_id, id desc"

    name = fields.Char("WBS 版本名称", required=True, tracking=True)
    version_code = fields.Char("版本", required=True, default="V1.0", tracking=True)
    project_id = fields.Many2one("project.project", string="项目", required=True, index=True, ondelete="cascade", tracking=True)
    company_id = fields.Many2one("res.company", related="project_id.company_id", store=True, readonly=True)
    state = fields.Selection(
        [("draft", "草稿"), ("validated", "校验通过"), ("published", "已发布"), ("adjusting", "调整中"), ("archived", "已归档")],
        string="发布状态", required=True, default="draft", tracking=True, index=True,
    )
    validation_state = fields.Selection(
        [("pending", "待校验"), ("passed", "通过"), ("failed", "未通过")],
        string="完整性", required=True, default="pending", tracking=True,
    )
    validation_message = fields.Text("校验说明", readonly=True)
    validated_by_id = fields.Many2one("res.users", string="校验人", readonly=True)
    validated_at = fields.Datetime("校验时间", readonly=True)
    published_by_id = fields.Many2one("res.users", string="发布人", readonly=True)
    published_at = fields.Datetime("发布时间", readonly=True)
    source_plan_id = fields.Many2one("construction.wbs.plan", string="来源版本", readonly=True, ondelete="restrict")
    node_ids = fields.One2many("construction.work.breakdown", "plan_id", string="WBS 节点")
    node_count = fields.Integer("节点数", compute="_compute_node_count")
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("project_version_unique", "unique(project_id, version_code)", "同一项目的 WBS 版本号不能重复。"),
    ]

    @api.depends("node_ids")
    def _compute_node_count(self):
        for rec in self:
            rec.node_count = len(rec.node_ids)

    @api.model
    def _ensure_initial_plan(self, project):
        plan = self.search([("project_id", "=", project.id)], order="id desc", limit=1)
        if plan:
            return plan
        return self.create({"name": f"{project.display_name} WBS", "version_code": "V1.0", "project_id": project.id})

    def _validation_errors(self):
        self.ensure_one()
        errors = []
        if not self.node_ids:
            errors.append("至少需要一个 WBS 节点")
        codes = [str(code).strip() for code in self.node_ids.mapped("code") if str(code or "").strip()]
        if len(codes) != len(set(codes)):
            errors.append("存在重复 WBS 编码")
        if self.node_ids.filtered(lambda node: not node.level_type):
            errors.append("存在未设置节点角色的节点")
        if self.node_ids.filtered(lambda node: node.parent_id and node.parent_id.plan_id != self):
            errors.append("存在跨版本上级关系")
        return errors

    def action_validate_plan(self):
        all_passed = True
        for rec in self:
            if rec.state not in {"draft", "adjusting", "validated"}:
                raise UserError("只有草稿、调整中或已校验的 WBS 版本可以执行校验。")
            errors = rec._validation_errors()
            rec.write({
                "validation_state": "failed" if errors else "passed",
                "validation_message": "；".join(errors) if errors else "结构完整性校验通过。",
                "validated_by_id": self.env.user.id,
                "validated_at": fields.Datetime.now(),
                "state": rec.state if errors else "validated",
            })
            if errors:
                all_passed = False
        return all_passed

    def action_publish_plan(self):
        for rec in self:
            if rec.state != "validated" or rec.validation_state != "passed":
                raise UserError("WBS 必须先通过完整性校验才能发布。")
            previous = self.search([("project_id", "=", rec.project_id.id), ("state", "=", "published"), ("id", "!=", rec.id)])
            previous.write({"state": "archived", "active": False})
            rec.write({"state": "published", "published_by_id": self.env.user.id, "published_at": fields.Datetime.now(), "active": True})
        return True

    def _next_revision_code(self):
        self.ensure_one()
        match = re.fullmatch(r"V(\d+)\.(\d+)", self.version_code or "")
        return f"V{match.group(1)}.{int(match.group(2)) + 1}" if match else f"{self.version_code or 'V1.0'}.1"

    def action_start_adjustment(self):
        self.ensure_one()
        if self.state != "published":
            raise UserError("只有已发布的 WBS 版本可以发起调整。")
        revision = self.create({
            "name": self.name,
            "version_code": self._next_revision_code(),
            "project_id": self.project_id.id,
            "state": "adjusting",
            "validation_state": "pending",
            "source_plan_id": self.id,
        })
        mapping = {}
        for node in self.node_ids.sorted(lambda row: (row.level, row.sequence, row.id)):
            clone = node.copy({
                "plan_id": revision.id,
                "parent_id": mapping.get(node.parent_id.id, False),
                "source_key": False,
                "boq_version_id": False,
            })
            mapping[node.id] = clone.id
        return revision._form_action()

    def action_archive_plan(self):
        self.write({"state": "archived", "active": False})
        return True

    def _governance_contract(self):
        self.ensure_one()
        updated_by = self.write_uid.display_name or "-"
        updated_at = fields.Datetime.to_string(self.write_date) if self.write_date else "-"
        return {
            "facts": [
                {"key": "version", "label": "版本", "value": self.version_code},
                {"key": "state", "label": "状态", "value": dict(self._fields["state"].selection).get(self.state, self.state)},
                {"key": "validation", "label": "完整性", "value": dict(self._fields["validation_state"].selection).get(self.validation_state, self.validation_state)},
                {"key": "updated", "label": "最近更新", "value": f"{updated_by} / {updated_at}"},
            ]
        }

    def action_open_structure(self):
        self.ensure_one()
        action = self.project_id.action_open_wbs_planning()
        context = dict(action.get("context") or {})
        context.update({
            "default_project_id": self.project_id.id,
            "default_plan_id": self.id,
        })
        action.update({"name": f"WBS 计划 · {self.version_code}", "domain": [("plan_id", "=", self.id)], "context": context})
        return action

    def _form_action(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window", "name": self.display_name,
            "res_model": self._name, "res_id": self.id, "view_mode": "form", "target": "current",
        }

    def unlink(self):
        if self.filtered(lambda rec: rec.state == "published"):
            raise UserError("已发布的 WBS 版本不可删除。")
        return super().unlink()
