# -*- coding: utf-8 -*-
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.fields import Command
from odoo.tests.common import tagged
from .business_case import BusinessTransactionCase


@tagged("post_install", "-at_install", "runtime_user_management")
class TestRuntimeUserManagement(BusinessTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # The suite owns a registered synthetic company inside the rollback transaction.
        cls.env.user.write({"company_ids": [(4, cls.env.company.id)]})

    def _create_runtime_user(self, login, name, managed=False):
        return self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "login": login,
                "name": name,
                "email": "%s@example.test" % login,
                "sc_runtime_user_managed": managed,
            }
        )

    def _create_business_config_admin(self, login):
        internal_group = self.env.ref("base.group_user")
        config_group = self.env.ref("smart_construction_core.group_sc_cap_business_config_admin")
        return self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "login": login,
                "name": login,
                "company_id": self.env.company.id,
                "company_ids": [(6, 0, self.env.company.ids)],
                "groups_id": [(6, 0, (internal_group | config_group).ids)],
            }
        )

    def test_business_admin_assigns_owner_role_without_platform_authority(self):
        admin = self._create_business_config_admin("owner_role_admin")
        subject = self._create_runtime_user("owner_role_subject", "Owner Role Subject")
        role = self.env.ref("smart_construction_core.group_sc_role_owner")
        self.assertTrue(role.sc_assignable_user_permission)
        subject.with_user(admin).write({"sc_user_role_group_ids": [(6, 0, role.ids)]})
        self.assertIn(role, subject.groups_id)
        self.assertFalse(subject.has_group("base.group_system"))
        subject.with_user(admin).write({"sc_user_role_group_ids": [(6, 0, [])]})
        self.assertNotIn(role, subject.groups_id)

    def test_product_account_defaults_are_initialized_and_remain_configurable(self):
        Default = self.env["ir.default"].sudo()
        self.assertEqual(Default._get("res.users", "lang"), "zh_CN")
        self.assertEqual(Default._get("res.users", "tz"), "Asia/Shanghai")
        admin = self._create_business_config_admin("account_defaults_admin")
        Users = self.env["res.users"].with_user(admin).with_context(no_reset_password=True)
        user = Users.create({"name": "Default Account", "login": "default_account", "password": "synthetic-account-default"})
        self.assertEqual((user.lang, user.tz), ("zh_CN", "Asia/Shanghai"))
        user.write({"lang": "en_US", "tz": "UTC"})
        self.assertEqual((user.lang, user.tz), ("en_US", "UTC"))
        Default.set("res.users", "lang", "en_US")
        Default.set("res.users", "tz", "Europe/Paris", company_id=self.env.company.id)
        self.env["res.users"]._sc_initialize_account_defaults({"lang": "zh_CN", "tz": "Asia/Shanghai"})
        self.assertEqual(Default._get("res.users", "lang"), "en_US")
        self.assertEqual(Default._get("res.users", "tz", company_id=self.env.company.id), "Europe/Paris")
        self.assertEqual((user.lang, user.tz), ("en_US", "UTC"))
        next_user = Users.create({"name": "Configured Defaults", "login": "configured_defaults", "password": "synthetic-account-default"})
        self.assertEqual((next_user.lang, next_user.tz), ("en_US", "Europe/Paris"))

    def test_business_config_admin_can_export_update_identity_without_system_authority(self):
        admin = self._create_business_config_admin("business_import_export_admin")
        self.assertTrue(admin.has_group("base.group_allow_export"))
        self.assertFalse(admin.has_group("base.group_system"))
        job = self.env["hr.job"].create({"name": "Import Update Identity", "company_id": self.env.company.id})
        exported = job.with_user(admin).export_data(["id", "name"])["datas"]
        self.assertEqual(exported, [[job.get_external_id()[job.id], job.name]])
        self.assertTrue(exported[0][0])
        experience = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Export Denied Experience", "login": "export_denied_experience",
            "groups_id": [(6, 0, self.env.ref("smart_construction_core.group_sc_role_experience").ids)],
        })
        self.assertFalse(experience.has_group("base.group_allow_export"))
        with self.assertRaises(UserError):
            job.with_user(experience).export_data(["id", "name"])

    def test_department_manager_uses_native_acl_with_private_fields_protected(self):
        admin = self._create_business_config_admin("department_public_manager_admin")
        employee = self.env["hr.employee"].create({"name": "Public Department Manager", "company_id": self.env.company.id})
        employee.flush_recordset()  # The native public model is a SQL view.
        department = self.env["hr.department"].create({"name": "Public Manager Department", "company_id": self.env.company.id})
        member = self.env["hr.employee"].create({"name": "Department Member", "company_id": self.env.company.id,
                                                  "department_id": department.id})
        private = self.env["hr.employee"].with_user(admin)
        self.assertTrue(private.check_access_rights("read", raise_exception=False))
        self.assertTrue(private.check_access_rights("write", raise_exception=False))
        department.with_user(admin).write({"sc_manager_public_id": employee.id})
        self.assertEqual(department.manager_id, employee)
        self.assertEqual(member.parent_id, employee)
        public = department.with_user(admin).sc_manager_public_id
        self.assertEqual(public.id, employee.id)
        self.assertEqual(public.name, employee.name)
        self.assertEqual(department.with_user(admin).search([("sc_manager_public_id", "=", employee.id)]), department)
        self.assertFalse(admin.has_group("hr.group_hr_user"))
        for field in ("private_email", "identification_id", "bank_account_id"):
            self.assertNotIn(field, private.fields_get())
            with self.assertRaises(AccessError):
                private.browse(employee.id).read([field])
            with self.assertRaises(AccessError):
                private.browse(employee.id).write({field: False})
        department.with_user(admin).write({"sc_manager_public_id": False})
        self.assertFalse(department.manager_id)
        self.assertFalse(member.parent_id)

    def test_office_asset_custodian_contract_and_native_assignment(self):
        from odoo.addons.smart_core.app_config_engine.services.assemblers.page_assembler import PageAssembler
        admin = self._create_business_config_admin("asset_configuration_admin")
        employee = self.env['hr.employee'].create({'name': 'Synthetic Custodian', 'company_id': self.env.company.id})
        actor_env = self.env(user=admin, su=False)
        assembler = PageAssembler(actor_env, actor_env['ir.model'].sudo().env)
        self.assertTrue(assembler._safe_model_can_read('hr.employee'))
        self.assertEqual(actor_env['hr.employee'].browse(employee.id).read(['name'])[0]['name'], employee.name)
        asset = actor_env['sc.office.asset'].create({
            'name': 'Synthetic Configuration Asset', 'asset_code': 'CONFIG-CUSTODIAN',
            'custodian_id': employee.id, 'company_id': self.env.company.id,
        })
        asset.action_assign()
        self.assertEqual(asset.status, 'in_use')
        asset.action_return()
        self.assertFalse(asset.custodian_id)
        self.assertEqual(asset.status, 'available')

    def test_department_public_manager_rejects_other_company(self):
        admin = self._create_business_config_admin("department_other_company_admin")
        other = self.env["res.company"].create({"name": "Department Manager Other Company"})
        admin.write({"company_ids": [(4, other.id)]})
        employee = self.env["hr.employee"].create({"name": "Other Company Manager", "company_id": other.id})
        department = self.env["hr.department"].create({"name": "Scoped Department", "company_id": self.env.company.id})
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            department.with_user(admin).with_context(allowed_company_ids=[self.env.company.id, other.id]).write({"sc_manager_public_id": employee.id})
        self.assertFalse(department.manager_id)

    def test_department_manager_cascade_preserves_native_company_scope(self):
        admin = self._create_business_config_admin("shared_department_manager_admin")
        other = self.env["res.company"].create({"name": "Shared Department Other Company"})
        department = self.env["hr.department"].create({"name": "Shared Department", "company_id": False})
        member = self.env["hr.employee"].create({"name": "Other Company Member", "company_id": other.id,
                                                  "department_id": department.id})
        manager = self.env["hr.employee"].create({"name": "Visible Manager", "company_id": self.env.company.id})
        manager.flush_recordset()
        department.with_user(admin).write({"sc_manager_public_id": manager.id})
        self.assertEqual(department.manager_id, manager)
        self.assertFalse(member.parent_id)
        with self.assertRaises(AccessError), self.env.cr.savepoint():
            member.with_user(admin).write({"parent_id": manager.id})
        self.assertFalse(member.parent_id)

    def test_managed_internal_login_counts_as_runtime_company_user(self):
        user = self._create_runtime_user("runtime_user_scope", "正式用户", managed=True)

        users = self.env["res.users"].search([("sc_runtime_company_real_user", "=", True)])

        self.assertIn(user, users)

    def test_unmanaged_login_is_excluded_from_runtime_company_user(self):
        user = self._create_runtime_user("runtime_unmanaged_scope", "非受管用户")

        users = self.env["res.users"].search([("sc_runtime_company_real_user", "=", True)])

        self.assertNotIn(user, users)

    def test_unmanaged_internal_user_is_available_to_company_maintainer(self):
        user = self._create_runtime_user("runtime_legacy_internal", "历史内部用户")

        users = self.env["res.users"].search([("sc_runtime_company_maintainable", "=", True)])

        self.assertIn(user, users)

    def test_privileged_user_is_not_available_to_company_maintainer(self):
        user = self._create_runtime_user("runtime_privileged", "特权用户")
        user.write({"groups_id": [(4, self.env.ref("base.group_system").id)]})

        users = self.env["res.users"].search([("sc_runtime_company_maintainable", "=", True)])

        self.assertNotIn(user, users)

    def test_template_user_is_not_available_to_company_maintainer(self):
        template_user = self.env.ref("base.default_user", raise_if_not_found=False)
        if not template_user:
            self.skipTest("base.default_user is not installed")

        users = self.env["res.users"].search([("sc_runtime_company_maintainable", "=", True)])

        self.assertNotIn(template_user, users)

    def test_runtime_management_rejects_privileged_target_write(self):
        user = self._create_runtime_user("runtime_privileged_write", "特权用户")
        user.write({"groups_id": [(4, self.env.ref("base.group_system").id)]})

        with self.assertRaises(ValidationError):
            user.with_context(sc_runtime_user_management=True)._sc_check_runtime_user_management_targets()

    def test_runtime_source_login_uses_canonical_login(self):
        user = self._create_runtime_user("runtime_display_scope", "正式用户", managed=True)

        self.assertEqual(user.sc_runtime_source_login, "runtime_display_scope")

    def test_runtime_source_login_is_searchable(self):
        user = self._create_runtime_user("runtime_search_original", "正式用户", managed=True)

        users = self.env["res.users"].search([("sc_runtime_source_login", "ilike", "search_original")])

        self.assertIn(user, users)

    def test_runtime_user_creation_requires_explicit_initial_password(self):
        Users = self.env["res.users"].with_context(sc_runtime_user_management=True)

        with self.assertRaises(ValidationError):
            Users._sc_runtime_user_safe_vals({"login": "boundary_user", "name": "Boundary User"})

    def test_runtime_user_creation_accepts_context_secret_without_default(self):
        Users = self.env["res.users"].with_context(
            sc_runtime_user_management=True,
            sc_default_initial_password="runtime-only-secret",
        )

        vals = Users._sc_runtime_user_safe_vals({"login": "boundary_user", "name": "Boundary User"})

        self.assertEqual(vals["password"], "runtime-only-secret")

    def test_runtime_user_safe_vals_accepts_orm_command_enum(self):
        admin = self._create_business_config_admin("runtime_command_enum_admin")
        Users = self.env["res.users"].with_user(admin).with_context(
            sc_runtime_user_management=True,
            sc_default_initial_password="runtime-only-secret",
        )

        vals = Users._sc_runtime_user_safe_vals(
            {
                "login": "runtime_command_enum_user",
                "name": "Runtime Command Enum User",
                "company_id": self.env.company.id,
                "company_ids": [Command.set([self.env.company.id])],
            }
        )

        self.assertEqual(vals["company_id"], self.env.company.id)
        self.assertEqual(vals["company_ids"], [Command.set([self.env.company.id])])

    def test_runtime_user_company_must_be_in_multi_company_scope(self):
        Users = self.env["res.users"].with_context(
            sc_runtime_user_management=True,
            sc_default_initial_password="runtime-only-secret",
        )

        with self.assertRaises(ValidationError):
            Users._sc_runtime_user_safe_vals(
                {
                    "login": "invalid_company_scope",
                    "name": "Invalid Company Scope",
                    "company_id": self.env.company.id,
                    "company_ids": [(6, 0, [])],
                }
            )

    def test_runtime_user_incremental_company_commands_preserve_main_company(self):
        other_company = self.env["res.company"].create({"name": "Runtime Scope Other Company"})
        self.env.user.write({"company_ids": [(4, other_company.id)]})
        user = self._create_runtime_user("runtime_company_commands", "Runtime Company Commands")
        Users = self.env["res.users"].with_context(sc_runtime_user_management=True)

        with self.assertRaises(ValidationError):
            Users._sc_runtime_user_safe_vals(
                {"company_ids": [(3, self.env.company.id), (4, other_company.id)]},
                existing_user=user,
            )

    def test_personnel_main_company_change_cannot_expand_allowed_companies(self):
        admin = self._create_business_config_admin("personnel_company_scope_admin")
        other_company = self.env["res.company"].create({"name": "Synthetic Other Company"})
        admin.write({"company_ids": [(4, other_company.id)]})
        user = self._create_runtime_user("personnel_company_scope_target", "人员公司范围测试")
        before = (user.company_id.id, set(user.company_ids.ids), set(user.groups_id.ids))
        with self.assertRaises(ValidationError):
            user.with_user(admin).with_context(sc_runtime_user_management=True).write(
                {"company_id": other_company.id})
        self.assertEqual((user.company_id.id, set(user.company_ids.ids), set(user.groups_id.ids)), before)

    def test_runtime_user_creation_rejects_inline_project_authorization(self):
        admin = self._create_business_config_admin("runtime_inline_assignment_admin")
        project = self.env["project.project"].create(
            {"name": "Runtime Inline Assignment Project", "company_id": self.env.company.id}
        )
        Users = self.env["res.users"].with_user(admin).with_context(
            sc_runtime_user_management=True,
            sc_default_initial_password="runtime-only-secret",
        )

        with self.assertRaises(ValidationError):
            Users.create(
                {
                    "login": "runtime_inline_assignment_user",
                    "name": "Runtime Inline Assignment User",
                    "company_id": self.env.company.id,
                    "company_ids": [(6, 0, self.env.company.ids)],
                    "sc_project_member_assignment_ids": [
                        (0, 0, {"project_id": project.id, "source": "manual"})
                    ],
                }
            )

        self.assertFalse(
            self.env["res.users"].with_context(active_test=False).search(
                [("login", "=", "runtime_inline_assignment_user")]
            )
        )

    def test_profile_only_payload_does_not_touch_account_or_authorization_facts(self):
        user = self._create_runtime_user("profile_payload_boundary", "Profile Payload Boundary")
        Users = self.env["res.users"].with_context(sc_runtime_user_management=True)

        vals = Users._sc_runtime_user_safe_vals(
            {"name": "Profile Payload Updated", "phone": "synthetic-phone"},
            existing_user=user,
        )

        self.assertEqual(vals["name"], "Profile Payload Updated")
        self.assertEqual(vals["phone"], "synthetic-phone")
        self.assertNotIn("active", vals)
        self.assertNotIn("password", vals)
        self.assertNotIn("company_id", vals)
        self.assertNotIn("company_ids", vals)
        self.assertNotIn("groups_id", vals)
        self.assertNotIn("sc_project_member_assignment_ids", vals)

    def test_runtime_management_requires_project_for_new_assignment(self):
        admin = self._create_business_config_admin("runtime_assignment_project_required_admin")
        target = self._create_runtime_user(
            "runtime_assignment_project_required_target",
            "Runtime Assignment Project Required Target",
        )

        with self.assertRaises(ValidationError):
            target.with_user(admin).with_context(sc_runtime_user_management=True).write(
                {
                    "sc_project_member_assignment_ids": [
                        (0, 0, {"source": "manual", "note": "missing project"})
                    ]
                }
            )

        self.assertFalse(
            self.env["sc.project.member.assignment"].search(
                [("user_id", "=", target.id)]
            )
        )

    def test_runtime_management_preserves_project_assignment_create_and_update(self):
        admin = self._create_business_config_admin("runtime_assignment_admin")
        user = self._create_runtime_user("runtime_assignment_user", "Runtime Assignment User")
        project = self.env["project.project"].create(
            {"name": "Runtime Assignment Project", "company_id": self.env.company.id}
        )
        managed_user = user.with_user(admin).with_context(sc_runtime_user_management=True)

        managed_user.write(
            {
                "sc_project_member_assignment_ids": [
                    (
                        0,
                        0,
                        {
                            "project_id": project.id,
                            "company_id": self.env.company.id,
                            "source": "manual",
                            "active": True,
                            "note": "initial assignment",
                        },
                    )
                ]
            }
        )
        assignment = self.env["sc.project.member.assignment"].search(
            [("project_id", "=", project.id), ("user_id", "=", user.id)]
        )
        self.assertEqual(len(assignment), 1)
        self.assertEqual(assignment.note, "initial assignment")

        managed_user.write(
            {
                "sc_project_member_assignment_ids": [
                    (
                        1,
                        assignment.id,
                        {
                            "project_id": project.id,
                            "active": False,
                            "note": "archived assignment",
                        },
                    )
                ]
            }
        )

        self.assertFalse(assignment.active)
        self.assertEqual(assignment.note, "archived assignment")

        managed_user.write(
            {
                "sc_project_member_assignment_ids": [
                    (1, assignment.id, {"project_id": project.id, "active": True})
                ]
            }
        )

        self.assertTrue(assignment.active)
        self.assertEqual(assignment.project_id, project)

    def test_runtime_management_rejects_project_reassignment_without_follower_changes(self):
        admin = self._create_business_config_admin("runtime_reassignment_admin")
        target = self._create_runtime_user("runtime_reassignment_target", "Runtime Reassignment Target")
        source_project = self.env["project.project"].create(
            {"name": "Runtime Reassignment Source", "company_id": self.env.company.id}
        )
        target_project = self.env["project.project"].create(
            {"name": "Runtime Reassignment Target", "company_id": self.env.company.id}
        )
        managed_user = target.with_user(admin).with_context(sc_runtime_user_management=True)
        managed_user.write(
            {
                "sc_project_member_assignment_ids": [
                    (0, 0, {"project_id": source_project.id, "source": "manual"})
                ]
            }
        )
        assignment = self.env["sc.project.member.assignment"].search(
            [("project_id", "=", source_project.id), ("user_id", "=", target.id)]
        )
        self.assertIn(target.partner_id, source_project.message_partner_ids)
        self.assertNotIn(target.partner_id, target_project.message_partner_ids)

        with self.assertRaises(ValidationError):
            managed_user.write(
                {
                    "sc_project_member_assignment_ids": [
                        (1, assignment.id, {"project_id": target_project.id})
                    ]
                }
            )

        assignment.invalidate_recordset()
        source_project.invalidate_recordset()
        target_project.invalidate_recordset()
        self.assertEqual(assignment.project_id, source_project)
        self.assertIn(target.partner_id, source_project.message_partner_ids)
        self.assertNotIn(target.partner_id, target_project.message_partner_ids)

    def test_runtime_management_prevalidates_assignment_before_profile_write(self):
        admin = self._create_business_config_admin("runtime_atomic_admin")
        target = self._create_runtime_user("runtime_atomic_target", "Runtime Atomic Target")
        project = self.env["project.project"].create(
            {"name": "Runtime Atomic Project", "company_id": self.env.company.id}
        )
        assignment = self.env["sc.project.member.assignment"].create(
            {"project_id": project.id, "user_id": target.id, "source": "manual"}
        )

        with self.assertRaises(ValidationError):
            target.with_user(admin).with_context(sc_runtime_user_management=True).write(
                {
                    "name": "Runtime Atomic Changed",
                    "sc_project_member_assignment_ids": [
                        (1, assignment.id, {"project_id": False, "note": "must not change"})
                    ],
                }
            )

        target.invalidate_recordset()
        assignment.invalidate_recordset()
        self.assertEqual(target.name, "Runtime Atomic Target")
        self.assertFalse(assignment.note)
        self.assertEqual(assignment.project_id, project)

    def test_runtime_management_rejects_assignment_outside_actor_company_scope(self):
        admin = self._create_business_config_admin("runtime_company_scope_admin")
        target = self._create_runtime_user("runtime_company_scope_target", "Runtime Company Scope Target")
        other_company = self.env["res.company"].create({"name": "Runtime Assignment Other Company"})
        other_project = self.env["project.project"].create(
            {"name": "Runtime Assignment Other Project", "company_id": other_company.id}
        )

        with self.assertRaises(AccessError):
            target.with_user(admin).with_context(
                sc_runtime_user_management=True,
                allowed_company_ids=admin.company_ids.ids,
            ).write(
                {
                    "sc_project_member_assignment_ids": [
                        (0, 0, {"project_id": other_project.id, "source": "manual"})
                    ]
                }
            )

        self.assertFalse(
            self.env["sc.project.member.assignment"].search(
                [("project_id", "=", other_project.id), ("user_id", "=", target.id)]
            )
        )

    def test_inactive_assignment_read_keeps_active_default_and_company_rule(self):
        admin = self._create_business_config_admin("runtime_inactive_scope_admin")
        other_company = self.env["res.company"].create({"name": "Runtime Inactive Other Company"})
        target = self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "login": "runtime_inactive_scope_target",
                "name": "Runtime Inactive Scope Target",
                "company_id": self.env.company.id,
                "company_ids": [(6, 0, [self.env.company.id, other_company.id])],
            }
        )
        own_project = self.env["project.project"].create(
            {"name": "Runtime Inactive Own Project", "company_id": self.env.company.id}
        )
        other_project = self.env["project.project"].create(
            {"name": "Runtime Inactive Other Project", "company_id": other_company.id}
        )
        own_assignment = self.env["sc.project.member.assignment"].create(
            {"project_id": own_project.id, "user_id": target.id, "active": False}
        )
        other_assignment = self.env["sc.project.member.assignment"].create(
            {"project_id": other_project.id, "user_id": target.id, "active": False}
        )
        Assignment = self.env["sc.project.member.assignment"].with_user(admin)
        domain = [("id", "in", [own_assignment.id, other_assignment.id])]

        self.assertFalse(Assignment.search(domain), "default active_test must still hide inactive rows")
        visible = Assignment.with_context(active_test=False).search(domain)

        self.assertIn(own_assignment, visible)
        self.assertNotIn(other_assignment, visible)

    def test_runtime_management_rejects_cross_user_assignment_commands(self):
        admin = self._create_business_config_admin("runtime_assignment_boundary_admin")
        target = self._create_runtime_user("runtime_assignment_target", "Runtime Assignment Target")
        other = self._create_runtime_user("runtime_assignment_other", "Runtime Assignment Other")
        project = self.env["project.project"].create(
            {"name": "Runtime Assignment Boundary Project", "company_id": self.env.company.id}
        )
        assignment = self.env["sc.project.member.assignment"].create(
            {"project_id": project.id, "user_id": other.id, "note": "unchanged"}
        )

        with self.assertRaises(ValidationError):
            target.with_user(admin).with_context(sc_runtime_user_management=True).write(
                {
                    "sc_project_member_assignment_ids": [
                        (1, assignment.id, {"note": "must not change"})
                    ]
                }
            )

        self.assertEqual(assignment.note, "unchanged")

    def test_runtime_management_rejects_project_assignment_delete_command(self):
        admin = self._create_business_config_admin("runtime_assignment_delete_admin")
        target = self._create_runtime_user("runtime_assignment_delete_user", "Runtime Assignment Delete")
        project = self.env["project.project"].create(
            {"name": "Runtime Assignment Delete Project", "company_id": self.env.company.id}
        )
        assignment = self.env["sc.project.member.assignment"].create(
            {"project_id": project.id, "user_id": target.id}
        )

        with self.assertRaises(ValidationError):
            target.with_user(admin).with_context(sc_runtime_user_management=True).write(
                {"sc_project_member_assignment_ids": [(2, assignment.id, False)]}
            )

        self.assertTrue(assignment.exists())

    def test_runtime_management_rejects_multi_user_assignment_commands(self):
        admin = self._create_business_config_admin("runtime_assignment_multi_admin")
        first = self._create_runtime_user("runtime_assignment_multi_first", "Runtime Assignment First")
        second = self._create_runtime_user("runtime_assignment_multi_second", "Runtime Assignment Second")
        project = self.env["project.project"].create(
            {"name": "Runtime Assignment Multi Project", "company_id": self.env.company.id}
        )

        with self.assertRaises(ValidationError):
            (first | second).with_user(admin).with_context(sc_runtime_user_management=True).write(
                {
                    "sc_project_member_assignment_ids": [
                        (0, 0, {"project_id": project.id, "source": "manual"})
                    ]
                }
            )

        self.assertFalse(
            self.env["sc.project.member.assignment"].search(
                [("project_id", "=", project.id), ("user_id", "in", (first | second).ids)]
            )
        )

    def test_security_changes_increment_token_epoch(self):
        user = self._create_runtime_user("token_epoch_boundary", "Token Epoch Boundary")
        before = user.token_version

        user.write({"active": False})

        self.assertEqual(user.token_version, before + 1)

    def test_profile_changes_do_not_increment_token_epoch(self):
        user = self._create_runtime_user("profile_epoch_boundary", "Profile Epoch Boundary")
        before = user.token_version

        user.write({"name": "Profile Epoch Boundary Updated"})

        self.assertEqual(user.token_version, before)
