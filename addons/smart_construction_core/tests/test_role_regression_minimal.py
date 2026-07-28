# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase
from odoo.tests.common import tagged
from odoo.addons.smart_core.security.platform_admin import (
    PLATFORM_ADMIN_GROUP,
    SECURITY_ADMIN_GROUP,
    can_discover_platform_capabilities,
    can_manage_system_configuration,
)


@tagged("post_install", "-at_install", "sc_gate", "sc_perm", "role_regression_minimal")
class TestRoleRegressionMinimal(TransactionCase):
    """
    最小角色回归：验证典型角色对关键域动作的允许/拒绝。
    关注 action.groups_id 与用户组交集，防止菜单不可见但 action 绕过。
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env.ref("base.main_company")

        def _create(login, group_xmlids):
            groups = [(6, 0, [cls.env.ref(x).id for x in group_xmlids])]
            return cls.env["res.users"].with_context(no_reset_password=True).create(
                {
                    "name": login,
                    "login": login,
                    "email": f"{login}@example.com",
                    "company_id": company.id,
                    "company_ids": [(6, 0, [company.id])],
                    "groups_id": groups,
                }
            )

        cls.user_project_manager = _create(
            "role_project_manager",
            ["smart_construction_core.group_sc_cap_project_manager"],
        )
        cls.user_finance_user = _create(
            "role_finance_user",
            ["smart_construction_core.group_sc_cap_finance_user"],
        )
        cls.user_finance_manager = _create(
            "role_finance_manager",
            ["smart_construction_core.group_sc_cap_finance_manager"],
        )
        cls.user_material_manager = _create(
            "role_material_manager",
            ["smart_construction_core.group_sc_cap_material_manager"],
        )
        cls.user_platform_admin = _create(
            "role_platform_admin",
            [PLATFORM_ADMIN_GROUP],
        )
        cls.user_business_config_admin = _create(
            "role_business_config_admin",
            ["smart_construction_core.group_sc_cap_business_config_admin"],
        )
        cls.user_tenant_business_admin = _create(
            "role_tenant_business_admin",
            ["smart_construction_core.group_sc_role_business_admin"],
        )
        cls.user_contract_user = _create(
            "role_contract_user",
            ["smart_construction_core.group_sc_cap_contract_user"],
        )
        cls.user_break_glass = _create(
            "role_break_glass",
            ["base.group_system"],
        )
        cls.user_security_admin = _create(
            "role_security_admin",
            [SECURITY_ADMIN_GROUP],
        )

    def _allowed(self, user, action_xmlid):
        action = self.env.ref(action_xmlid)
        if not hasattr(action, "groups_id"):
            return True
        return bool(action.groups_id & user.groups_id)

    def test_role_action_matrix(self):
        cases = [
            # 项目域
            (self.user_project_manager, "smart_construction_core.action_project_wbs", True),
            (self.user_finance_user, "smart_construction_core.action_project_wbs", False),
            # 财务域
            (self.user_finance_user, "smart_construction_core.action_payment_request", True),
            (self.user_project_manager, "smart_construction_core.action_payment_request", False),
            # 物资域
            (self.user_material_manager, "smart_construction_core.action_project_material_plan", True),
            (self.user_finance_manager, "smart_construction_core.action_project_material_plan", False),
            # 合同域
            (self.user_contract_user, "smart_construction_core.action_construction_contract", True),
            (self.user_finance_user, "smart_construction_core.action_construction_contract", False),
            # 配置/工作流
            (self.user_platform_admin, "smart_construction_core.action_sc_workflow_def", True),
            (self.user_business_config_admin, "smart_construction_core.action_sc_workflow_def", False),
            (self.user_finance_user, "smart_construction_core.action_sc_workflow_def", False),
            (self.user_platform_admin, "smart_construction_core.action_sc_workflow_instance", False),
            (self.user_tenant_business_admin, "smart_construction_core.action_sc_workflow_instance", True),
            (self.user_tenant_business_admin, "smart_construction_core.action_sc_workflow_workitem", True),
            (self.user_tenant_business_admin, "smart_construction_core.action_sc_workflow_log", True),
            # 数据中心（只读组未包含在财务）
            (self.user_business_config_admin, "smart_construction_core.action_project_dictionary", True),
            (self.user_finance_manager, "smart_construction_core.action_project_dictionary", False),
        ]

        failures = []
        for user, action_xmlid, expected in cases:
            allowed = self._allowed(user, action_xmlid)
            if allowed != expected:
                failures.append(f"{user.login} vs {action_xmlid} expected {expected} got {allowed}")
        self.assertFalse(failures, "角色动作矩阵越权/缺权: %s" % "; ".join(failures))

    def test_non_superuser_admin_group_closure_has_no_custom_privilege_cycle(self):
        self.assertNotEqual(self.user_break_glass.id, self.env.ref("base.user_root").id)
        self.assertNotEqual(self.user_platform_admin.id, self.env.ref("base.user_root").id)

        self.assertTrue(self.user_break_glass.has_group("base.group_erp_manager"))
        self.assertFalse(self.user_break_glass.has_group("project.group_project_manager"))
        self.assertFalse(
            self.user_break_glass.has_group(
                "smart_construction_core.group_sc_task_entry_access"
            )
        )
        self.assertFalse(
            self.user_break_glass.has_group(
                "smart_construction_core.group_sc_cap_settlement_read"
            )
        )
        self.assertTrue(
            self.user_project_manager.has_group(
                "smart_construction_core.group_sc_task_entry_access"
            )
        )

        self.assertTrue(can_discover_platform_capabilities(self.user_platform_admin))
        self.assertTrue(can_manage_system_configuration(self.user_platform_admin))
        self.assertFalse(can_discover_platform_capabilities(self.user_break_glass))
        self.assertFalse(can_manage_system_configuration(self.user_break_glass))

    def test_security_admin_identity_is_independent(self):
        self.assertTrue(self.user_security_admin.has_group(SECURITY_ADMIN_GROUP))
        self.assertFalse(self.user_security_admin.has_group(PLATFORM_ADMIN_GROUP))
        self.assertFalse(self.user_security_admin.has_group("base.group_system"))
        self.assertFalse(
            self.user_security_admin.has_group(
                "smart_construction_core.group_sc_role_business_admin"
            )
        )

    def test_workflow_definition_and_runtime_permissions_are_split(self):
        definition = self.env["sc.workflow.def"].with_user(self.user_platform_admin)
        runtime = self.env["sc.workflow.instance"].with_user(self.user_platform_admin)
        tenant_runtime = self.env["sc.workflow.instance"].with_user(
            self.user_tenant_business_admin
        )

        self.assertTrue(definition.check_access_rights("read", raise_exception=False))
        self.assertFalse(runtime.check_access_rights("read", raise_exception=False))
        self.assertFalse(runtime.check_access_rights("create", raise_exception=False))
        self.assertTrue(tenant_runtime.check_access_rights("read", raise_exception=False))
        self.assertTrue(tenant_runtime.check_access_rights("create", raise_exception=False))

    def test_workflow_runtime_is_scoped_by_allowed_company_without_count_leak(self):
        main_company = self.env.ref("base.main_company")
        other_company = self.env["res.company"].create(
            {"name": "ADMIN_VIS_P2 synthetic workflow company"}
        )
        main_definition = self.env["sc.workflow.def"].create(
            {
                "name": "ADMIN_VIS_P2 main workflow definition",
                "code": "admin_vis_p2_main",
                "model_name": "project.project",
                "company_id": main_company.id,
            }
        )
        other_definition = self.env["sc.workflow.def"].create(
            {
                "name": "ADMIN_VIS_P2 other workflow definition",
                "code": "admin_vis_p2_other",
                "model_name": "project.project",
                "company_id": other_company.id,
            }
        )
        main_instance = self.env["sc.workflow.instance"].create(
            {
                "workflow_def_id": main_definition.id,
                "company_id": main_company.id,
                "model_name": "project.project",
                "res_id": 1001,
            }
        )
        other_instance = self.env["sc.workflow.instance"].create(
            {
                "workflow_def_id": other_definition.id,
                "company_id": other_company.id,
                "model_name": "project.project",
                "res_id": 1002,
            }
        )

        Runtime = self.env["sc.workflow.instance"].with_user(
            self.user_tenant_business_admin
        )
        visible_ids = Runtime.search(
            [("id", "in", [main_instance.id, other_instance.id])]
        ).ids
        self.assertEqual(visible_ids, [main_instance.id])
        with self.assertRaises(AccessError):
            Runtime.browse(other_instance.id).read(["name"])

        platform_definition = main_definition.with_user(self.user_platform_admin)
        self.assertEqual(platform_definition.instance_count, 0)

    def test_platform_admin_business_orm_channels_fail_closed(self):
        project = self.env["project.project"].create(
            {"name": "ADMIN_VIS_P2 synthetic restricted project"}
        )
        Project = self.env["project.project"].with_user(self.user_platform_admin)

        self.assertFalse(Project.check_access_rights("read", raise_exception=False))
        self.assertFalse(Project.check_access_rights("create", raise_exception=False))
        with self.assertRaises(AccessError):
            Project.search([("id", "=", project.id)])
        with self.assertRaises(AccessError):
            Project.browse(project.id).read(["name"])
        with self.assertRaises(AccessError):
            Project.read_group(
                [("id", "=", project.id)],
                ["id:count"],
                [],
            )
        with self.assertRaises(AccessError):
            Project.create({"name": "ADMIN_VIS_P2 forbidden create"})

    def test_platform_admin_cannot_expand_own_security_boundary(self):
        other_company = self.env["res.company"].create(
            {"name": "ADMIN_VIS_P2 synthetic other company"}
        )
        own_user = self.user_platform_admin.with_user(self.user_platform_admin)

        with self.assertRaises(AccessError):
            own_user.write(
                {
                    "groups_id": [
                        (4, self.env.ref("project.group_project_manager").id)
                    ]
                }
            )
        with self.assertRaises(AccessError):
            own_user.write({"company_ids": [(4, other_company.id)]})
