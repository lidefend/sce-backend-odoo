# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ScApprovalScope(models.Model):
    _name = "sc.approval.scope"
    _description = "审批岗位人员"
    _order = "sequence, id"

    name = fields.Char(required=True, string="审批岗位")
    sequence = fields.Integer(default=10, index=True, string="顺序")
    scope_key = fields.Selection(
        selection="_selection_approval_scope",
        required=True,
        index=True,
        string="岗位编码",
    )
    group_id = fields.Many2one("res.groups", compute="_compute_group_id", store=True, readonly=True, string="执行权限组")
    user_ids = fields.Many2many(
        "res.users",
        compute="_compute_user_ids",
        inverse="_inverse_user_ids",
        string="已授权人员",
        readonly=True,
        help="由系统角色授权结果生成；请在用户管理中维护系统角色，审批岗位不授予权限。",
    )
    user_count = fields.Integer(compute="_compute_user_count", string="人数")
    note = fields.Text(string="说明")

    _sql_constraints = [
        ("sc_approval_scope_key_uniq", "unique(scope_key)", "审批岗位不能重复。"),
    ]

    @api.model
    def _selection_approval_scope(self):
        return self.env["sc.approval.policy"]._selection_approval_scope()

    @api.depends("scope_key")
    def _compute_group_id(self):
        Policy = self.env["sc.approval.policy"]
        for rec in self:
            group = Policy._group_for_approval_scope(rec.scope_key)
            rec.group_id = group.id if group else False

    def _compute_user_ids(self):
        for rec in self:
            rec.user_ids = rec.group_id.sudo().users if rec.group_id else False

    @api.depends("user_ids")
    def _compute_user_count(self):
        for rec in self:
            rec.user_count = len(rec.user_ids.filtered(lambda user: user.active and not user.share))

    def _inverse_user_ids(self):
        # Keep the legacy inverse as an explicit rejection for direct ORM/RPC writes.
        raise UserError(_("审批岗位不授予或撤销权限。请在用户管理中维护系统角色。"))

    def action_open_add_user_wizard(self):
        self.ensure_one()
        raise UserError(_("审批岗位不创建授权用户。请在用户管理中创建用户并维护系统角色。"))


class ScApprovalScopeUserWizard(models.TransientModel):
    _name = "sc.approval.scope.user.wizard"
    _description = "新增审批人员"

    scope_id = fields.Many2one("sc.approval.scope", required=True, readonly=True, string="审批岗位")
    scope_key = fields.Selection(related="scope_id.scope_key", readonly=True, string="岗位编码")
    name = fields.Char(required=True, string="姓名")
    login = fields.Char(required=True, string="登录名")
    email = fields.Char(string="邮箱")
    password = fields.Char(required=True, string="初始密码")

    def action_create_user(self):
        # Retained for stale clients and saved wizard records; never write users/groups.
        self.ensure_one()
        raise UserError(_("审批岗位不创建用户或授予权限。请在用户管理中创建用户并维护系统角色。"))
