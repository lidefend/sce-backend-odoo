# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.addons.smart_core.security.group_assignment import GroupAuthorityGap, apply_commands


class ResGroups(models.Model):
    _inherit = "res.groups"

    sc_assignable_user_permission = fields.Boolean(string="可由用户配置管理员分配的角色", default=False, index=True)


class ResUsers(models.Model):
    _inherit = "res.users"

    login = fields.Char(string="登录账号")
    name = fields.Char(string="姓名")
    phone = fields.Char(string="手机号")
    email = fields.Char(string="邮箱")
    sc_runtime_source_login = fields.Char(
        string="用户名",
        compute="_compute_sc_runtime_profile_fields",
        search="_search_sc_runtime_source_login",
    )
    sc_runtime_company_real_user = fields.Boolean(
        string="公司真实用户",
        compute="_compute_sc_runtime_company_real_user",
        search="_search_sc_runtime_company_real_user",
    )
    sc_runtime_user_managed = fields.Boolean(
        string="用户配置管理员维护",
        default=False,
        index=True,
        copy=False,
    )
    sc_runtime_company_maintainable = fields.Boolean(
        string="公司内部人员可维护",
        compute="_compute_sc_runtime_company_maintainable",
        search="_search_sc_runtime_company_maintainable",
    )

    sc_user_role_group_ids = fields.Many2many(
        "res.groups",
        "sc_runtime_user_role_group_rel",
        "user_id",
        "group_id",
        string="用户角色",
        compute="_compute_sc_user_role_group_ids",
        inverse="_inverse_sc_user_role_group_ids",
        store=False,
    )
    sc_user_permission_group_ids = fields.Many2many(
        "res.groups",
        string="用户权限组",
        compute="_compute_sc_user_role_group_ids",
        inverse="_inverse_sc_user_permission_group_ids",
        store=False,
    )

    @api.model
    def _sc_internal_group(self):
        return self.env.ref("smart_construction_core.group_sc_internal_user", raise_if_not_found=False)

    @api.model
    def _sc_assignable_groups(self):
        return self.env["res.groups"].sudo().search([("sc_assignable_user_permission", "=", True)])

    def _compute_sc_runtime_profile_fields(self):
        for user in self:
            user.sc_runtime_source_login = (user.login or "").strip()

    @api.model
    def _search_sc_runtime_source_login(self, operator, value):
        if operator not in ("=", "!=", "like", "not like", "ilike", "not ilike"):
            operator = "ilike"
        return [("login", operator, value)]

    @api.model
    def _sc_runtime_company_real_user_ids(self):
        users = self.env["res.users"].sudo().with_context(active_test=False).search(
            [
                ("sc_runtime_user_managed", "=", True),
                ("share", "=", False),
                ("login", "!=", False),
            ]
        )
        return users.ids

    def _compute_sc_runtime_company_real_user(self):
        real_user_ids = set(self._sc_runtime_company_real_user_ids())
        for user in self:
            user.sc_runtime_company_real_user = user.id in real_user_ids

    def _search_sc_runtime_company_real_user(self, operator, value):
        real_user_ids = self._sc_runtime_company_real_user_ids()
        positive = operator in ("=", "==") and bool(value) or operator in ("!=", "<>") and not bool(value)
        return [("id", "in" if positive else "not in", real_user_ids)]

    @api.model
    def _sc_runtime_privileged_groups(self):
        xmlids = (
            "base.group_system",
            "smart_construction_core.group_sc_cap_config_admin",
            "smart_core.group_smart_core_admin",
        )
        return self.env["res.groups"].sudo().browse([
            group.id
            for xmlid in xmlids
            if (group := self.env.ref(xmlid, raise_if_not_found=False))
        ])

    @api.model
    def _sc_runtime_company_maintainable_user_ids(self):
        internal_group = self.env.ref("base.group_user", raise_if_not_found=False)
        if not internal_group:
            return []
        template_user = self.env.ref("base.default_user", raise_if_not_found=False)
        domain = [
            ("share", "=", False),
            ("login", "!=", False),
            ("company_id", "in", self.env.user.company_ids.ids),
            ("groups_id", "in", [internal_group.id]),
        ]
        if template_user:
            domain.append(("id", "!=", template_user.id))
        privileged = self._sc_runtime_privileged_groups()
        if privileged:
            domain.append(("groups_id", "not in", privileged.ids))
        return self.sudo().with_context(active_test=False).search(domain).ids

    @api.depends_context("uid", "allowed_company_ids")
    def _compute_sc_runtime_company_maintainable(self):
        maintainable_ids = set(self._sc_runtime_company_maintainable_user_ids())
        for user in self:
            user.sc_runtime_company_maintainable = user.id in maintainable_ids

    @api.model
    def _search_sc_runtime_company_maintainable(self, operator, value):
        maintainable_ids = self._sc_runtime_company_maintainable_user_ids()
        positive = operator in ("=", "==") and bool(value) or operator in ("!=", "<>") and not bool(value)
        return [("id", "in" if positive else "not in", maintainable_ids)]

    def _sc_check_runtime_user_management_targets(self):
        maintainable_ids = set(self._sc_runtime_company_maintainable_user_ids())
        if any(user.id not in maintainable_ids for user in self):
            raise ValidationError(_("只能维护当前公司范围内的非特权内部用户。"))

    @api.depends("groups_id", "sc_group_authority_state")
    def _compute_sc_user_role_group_ids(self):
        assignable = self._sc_assignable_groups()
        for user in self:
            try:
                roots = user._sc_explicit_group_roots(lock=False)
                roles = assignable.browse(sorted(roots)) & assignable
            except GroupAuthorityGap:
                # Legacy effective-role display only; never accepted as assignment provenance.
                roles = user.groups_id & assignable
            user.sc_user_role_group_ids = roles
            user.sc_user_permission_group_ids = roles

    def _inverse_assignable_user_groups(self, field_name):
        assignable = self._sc_assignable_groups()
        internal_group = self._sc_internal_group()
        for user in self:
            target_ids = user._sc_role_group_projection(
                assignable.ids, [(6, 0, user[field_name].ids)],
                internal_group.ids if internal_group and not user.share else [],
            )
            user.groups_id = [(6, 0, sorted(target_ids))]

    def _inverse_sc_user_role_group_ids(self):
        self._inverse_assignable_user_groups("sc_user_role_group_ids")

    def _inverse_sc_user_permission_group_ids(self):
        self._inverse_assignable_user_groups("sc_user_permission_group_ids")

    @api.model
    def _sc_runtime_user_management_allowed(self):
        return bool(
            (self.env.context.get("sc_runtime_user_management")
             or (not self.env.su and not self.env.user.has_group("base.group_system")))
            and self.env.user.has_group("smart_construction_core.group_sc_cap_business_config_admin")
        )

    @api.model
    def _sc_group_ids_from_commands(self, commands):
        ids = set()
        if not commands:
            return ids
        if isinstance(commands, (int, str)):
            try:
                return {int(commands)}
            except Exception:
                return set()
        for command in commands:
            if isinstance(command, int):
                ids.add(command)
                continue
            if not isinstance(command, (list, tuple)) or not command:
                continue
            op = int(command[0] or 0)
            if op == 6 and len(command) > 2 and isinstance(command[2], (list, tuple)):
                ids = {int(group_id) for group_id in command[2] if int(group_id or 0) > 0}
            elif op == 4 and len(command) > 1 and int(command[1] or 0) > 0:
                ids.add(int(command[1]))
            elif op == 3 and len(command) > 1:
                ids.discard(int(command[1] or 0))
            elif op == 5:
                ids.clear()
        return ids

    @api.model
    def _sc_relational_ids_after_commands(self, commands, initial_ids=None):
        if commands is None:
            return set(initial_ids or [])
        try:
            # Only membership edits: never pass related-record CRUD into sudo.
            return apply_commands(set(initial_ids or []), commands)
        except GroupAuthorityGap as error:
            raise ValidationError(_("公司访问范围只能关联或移除已有公司，关系命令不合法。")) from error

    @api.model
    def _sc_runtime_user_safe_vals(self, vals, existing_user=False):
        allowed_fields = {
            "login",
            "name",
            "active",
            "phone",
            "email",
            "company_id",
            "company_ids",
            "password",
            "image_1920",
            "sc_personnel_department_id",
            "sc_personnel_job_id",
            "sc_personnel_active",
        }
        safe_vals = {key: vals[key] for key in allowed_fields if key in vals}
        safe_vals["share"] = False
        safe_vals["sc_runtime_user_managed"] = True

        allowed_company_ids = set(self.env.user.company_ids.ids)
        initial_company_ids = set(existing_user.company_ids.ids) if existing_user else set()
        target_company_ids = self._sc_relational_ids_after_commands(
            vals.get("company_ids"), initial_ids=initial_company_ids
        )
        if target_company_ids - allowed_company_ids:
            raise ValidationError(_("不能授予当前管理员公司范围之外的多公司权限。"))
        company_id = int(vals.get("company_id") or (existing_user.company_id.id if existing_user else self.env.company.id))
        if company_id not in allowed_company_ids:
            raise ValidationError(_("所属公司必须位于当前管理员的公司范围内。"))
        if ("company_ids" in vals or (existing_user and "company_id" in vals)) and company_id not in target_company_ids:
            raise ValidationError(_("所属公司必须包含在用户的多公司访问范围内。"))
        if not existing_user and "company_ids" not in vals:
            safe_vals["company_ids"] = [(6, 0, [company_id])]

        for field_name, model_name in (
            ("sc_personnel_department_id", "hr.department"),
            ("sc_personnel_job_id", "hr.job"),
        ):
            related_id = vals.get(field_name)
            if related_id is None or related_id is False or related_id == 0:
                continue
            if type(related_id) is not int or related_id <= 0:
                raise ValidationError(_("部门或岗位引用不合法。"))
            related = self.env[model_name].browse(related_id).exists()
            if not related:
                raise ValidationError(_("部门或岗位不存在。"))
            related.check_access_rights("read")
            related.check_access_rule("read")
            if related.company_id and related.company_id.id != company_id:
                raise ValidationError(_("部门或岗位必须属于人员所属公司。"))

        role_commands = vals.get("sc_user_role_group_ids")
        if role_commands is None:
            role_commands = vals.get("sc_user_permission_group_ids")
        if role_commands is not None:
            assignable = self._sc_assignable_groups()
            internal_group = self._sc_internal_group()
            if existing_user:
                target_ids = existing_user._sc_role_group_projection(
                    assignable.ids, role_commands, internal_group.ids,
                )
            else:
                try:
                    requested_ids = apply_commands(set(), role_commands)
                except GroupAuthorityGap as error:
                    raise ValidationError(_("角色分配命令不合法：%s") % str(error)) from error
                if requested_ids - set(assignable.ids):
                    raise ValidationError(_("角色请求包含不可分配的权限组。"))
                target_ids = requested_ids | set(internal_group.ids)
            safe_vals["groups_id"] = [(6, 0, sorted(target_ids))]
        elif not existing_user:
            internal_group = self._sc_internal_group()
            if internal_group:
                safe_vals["groups_id"] = [(4, internal_group.id)]

        if not existing_user and not safe_vals.get("password"):
            initial_password = self.env.context.get("sc_default_initial_password")
            if not initial_password:
                raise ValidationError(_("创建用户必须通过受控运行时提供初始密码。"))
            safe_vals["password"] = initial_password
        return safe_vals

    @api.model
    def _sc_runtime_project_assignment_vals(self, vals, target_user, existing_assignment=False):
        if not isinstance(vals, dict):
            raise ValidationError(_("项目成员授权内容不合法。"))
        allowed_fields = {"project_id", "active", "source", "note"}
        tolerated_derived_fields = {"company_id", "user_id"}
        unexpected_fields = set(vals) - allowed_fields - tolerated_derived_fields
        if unexpected_fields:
            raise ValidationError(_("项目成员授权包含不允许维护的字段。"))

        if vals.get("user_id") and int(vals["user_id"]) != target_user.id:
            raise ValidationError(_("项目成员授权必须属于当前维护人员。"))

        try:
            incoming_project_id = int(vals.get("project_id") or 0) if "project_id" in vals else 0
        except (TypeError, ValueError):
            raise ValidationError(_("项目成员授权引用的项目不合法。"))

        if existing_assignment:
            project_id = existing_assignment.project_id.id
            if "project_id" in vals and incoming_project_id != project_id:
                raise ValidationError(_("已建立的项目成员授权不得更换或清空项目；请停用旧授权后新增目标项目授权。"))
        else:
            project_id = incoming_project_id
            if project_id <= 0:
                raise ValidationError(_("新增项目成员授权必须指定有效项目。"))

        project = self.env["project.project"].browse(project_id).exists()
        if not project:
            raise ValidationError(_("项目成员授权引用的项目不存在。"))
        project.check_access_rights("read")
        project.check_access_rule("read")
        if vals.get("company_id") and int(vals["company_id"]) != project.company_id.id:
            raise ValidationError(_("项目成员授权的公司必须与项目公司一致。"))

        update_fields = allowed_fields - {"project_id"} if existing_assignment else allowed_fields
        return {field_name: vals[field_name] for field_name in update_fields if field_name in vals}

    @api.model
    def _sc_prepare_runtime_project_assignment_commands(self, target_user, commands):
        if commands is None:
            return []
        if not isinstance(commands, (list, tuple)):
            raise ValidationError(_("项目成员授权命令不合法。"))

        Assignment = self.env["sc.project.member.assignment"]
        prepared = []
        for command in commands:
            if not isinstance(command, (list, tuple)) or len(command) < 2:
                raise ValidationError(_("项目成员授权命令不合法。"))
            operation = int(command[0] or 0)
            record_id = int(command[1] or 0)
            command_vals = command[2] if len(command) > 2 else {}
            if operation == 0:
                assignment_vals = self._sc_runtime_project_assignment_vals(
                    command_vals,
                    target_user,
                )
                assignment_vals["user_id"] = target_user.id
                prepared.append(("create", Assignment, assignment_vals))
                continue
            if operation == 1 and record_id > 0:
                assignment = Assignment.with_context(active_test=False).search(
                    [("id", "=", record_id), ("user_id", "=", target_user.id)],
                    limit=1,
                )
                if not assignment:
                    raise ValidationError(_("项目成员授权不存在或不属于当前维护人员。"))
                assignment_vals = self._sc_runtime_project_assignment_vals(
                    command_vals,
                    target_user,
                    existing_assignment=assignment,
                )
                prepared.append(("write", assignment, assignment_vals))
                continue
            raise ValidationError(_("项目成员授权只能新增、修改或停用，不能删除或重新归属。"))
        return prepared

    @api.model
    def _sc_apply_prepared_runtime_project_assignment_commands(self, prepared):
        for operation, recordset, assignment_vals in prepared:
            if operation == "create":
                recordset.create(assignment_vals)
            elif assignment_vals:
                recordset.write(assignment_vals)

    @api.model
    def _sc_runtime_user_sudo_context(self):
        # Defaults are client input too: never let ORM defaults reintroduce
        # fields excluded from the validated payload at a sudo boundary.
        context = {key: value for key, value in self.env.context.items()
                   if not key.startswith("default_")}
        context.update(sc_runtime_user_management_sudo=True, no_reset_password=True)
        return context

    @api.model_create_multi
    def create(self, vals_list):
        if self._sc_runtime_user_management_allowed() and not (self.env.su and self.env.context.get("sc_runtime_user_management_sudo")):
            if any(vals.get("sc_project_member_assignment_ids") for vals in vals_list):
                raise ValidationError(_("请先保存人员，再维护项目成员授权。"))
            self.check_access_rights("create")
            safe_vals_list = [self._sc_runtime_user_safe_vals(dict(vals or {})) for vals in vals_list]
            # A create rule can depend on the resulting record. Roll back the
            # delegated creation and its relations if the original caller is denied.
            with self.env.cr.savepoint():
                users = self.sudo().with_context(
                    self._sc_runtime_user_sudo_context()
                ).create(safe_vals_list).with_env(self.env)
                users.check_access_rule("create")
            return users

        internal_group = self._sc_internal_group()
        for vals in vals_list:
            if vals.get("share"):
                continue
            commands = list(vals.get("groups_id") or [])
            if internal_group and not commands:
                commands.append((4, internal_group.id))
            if internal_group and self.env.context.get("sc_runtime_user_management"):
                commands.append((4, internal_group.id))
            if commands:
                vals["groups_id"] = commands
            if self.env.context.get("sc_runtime_user_management") and not vals.get("password"):
                initial_password = self.env.context.get("sc_default_initial_password")
                if not initial_password:
                    raise ValidationError(_("创建用户必须通过受控运行时提供初始密码。"))
                vals["password"] = initial_password
        return super().create(vals_list)

    def write(self, vals):
        # Preserve native self-service, whose field set and checks are server-owned.
        if (not self.env.su and self.ids == [self.env.uid]
                and set(vals).issubset(self.SELF_WRITEABLE_FIELDS)):
            return super().write(vals)
        if self._sc_runtime_user_management_allowed() and not (self.env.su and self.env.context.get("sc_runtime_user_management_sudo")):
            self.check_access_rights("write")
            self.check_access_rule("write")
            self._sc_check_runtime_user_management_targets()
            assignment_commands = vals.get("sc_project_member_assignment_ids")
            if assignment_commands is not None and len(self) != 1:
                raise ValidationError(_("项目成员授权必须逐个人员维护。"))
            for user in self:
                safe_vals = self._sc_runtime_user_safe_vals(dict(vals or {}), existing_user=user)
                prepared_assignments = self._sc_prepare_runtime_project_assignment_commands(
                    user,
                    assignment_commands,
                )
                user.sudo().with_context(
                    self._sc_runtime_user_sudo_context()
                ).write(safe_vals)
                self._sc_apply_prepared_runtime_project_assignment_commands(prepared_assignments)
            return True
        return super().write(vals)
