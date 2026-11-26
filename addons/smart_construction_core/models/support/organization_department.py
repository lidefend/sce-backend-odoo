# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class HrDepartment(models.Model):
    _name = "hr.department"
    _inherit = ["hr.department", "sc.delete.guard.mixin"]
    _description = "组织架构"
    _sc_delete_guard_blocker_models = (
        "hr.department",
        "hr.employee",
        "hr.job",
        "sc.contract.event",
        "sc.document.admin.document",
        "sc.hr.payroll.document",
        "sc.office.admin.document",
        "sc.plan",
        "sc.plan.line",
        "sc.subcontract.request",
    )
    _sc_delete_guard_include_models = _sc_delete_guard_blocker_models

    # Native public employee rows share the employee identity; manager_id
    # remains the single business fact. Do not grant private HR read access.
    sc_manager_public_id = fields.Many2one(
        "hr.employee.public", string="部门负责人",
        compute="_compute_sc_manager_public_id", inverse="_inverse_sc_manager_public_id",
        search="_search_sc_manager_public_id",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )

    @api.depends("manager_id")
    def _compute_sc_manager_public_id(self):
        for department in self:
            department.sc_manager_public_id = department.manager_id.id

    def _inverse_sc_manager_public_id(self):
        for department in self:
            manager = department.sc_manager_public_id
            if manager:
                manager.check_access_rights("read")
                manager.check_access_rule("read")
                if department.company_id and manager.company_id and manager.company_id != department.company_id:
                    raise ValidationError(_("部门负责人必须属于部门所在公司。"))
            department.manager_id = manager.id

    @api.model
    def _search_sc_manager_public_id(self, operator, value):
        return [("manager_id", operator, value)]

    def _setup_complete(self):
        super()._setup_complete()
        labels = {
            "name": "部门名称",
            "active": "有效",
            "company_id": "公司",
            "manager_id": "负责人",
            "parent_id": "上级部门",
            "child_ids": "下级部门",
            "message_follower_ids": "关注人",
            "message_ids": "沟通记录",
        }
        for field_name, label in labels.items():
            if field_name in self._fields:
                self._fields[field_name].string = label

    def unlink(self):
        active_departments = self.filtered("active")
        if active_departments:
            raise UserError("请先停用部门后再删除。")
        self._sc_raise_delete_blockers(action_label="删除部门")
        return super().unlink()
