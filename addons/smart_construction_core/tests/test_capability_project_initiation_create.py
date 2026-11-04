# -*- coding: utf-8 -*-
from __future__ import annotations

from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_construction_core.handlers.project_initiation_enter import (
    ProjectInitiationEnterHandler,
)
from odoo.addons.smart_construction_core.services.project_creation_service import (
    ProjectCreationService,
)


@tagged("post_install", "-at_install", "cap01c_project_initiation_create")
class TestCapabilityProjectInitiationCreate(TransactionCase):
    """C1 project.initiation.create 能力承诺验证（最小范围）。

    只验证 SCE 新增语义：输入契约、创建结果、默认值、条件性初始化、错误映射。
    Odoo 原生 ORM / ACL / 事务 / 注册事实直接信任，不重复测试。
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        base_user = cls.env.ref("base.group_user")

        def make_user(login, capability_group):
            groups = [base_user.id]
            if capability_group:
                groups.append(cls.env.ref(capability_group).id)
            return cls.env["res.users"].with_context(no_reset_password=True).create(
                {
                    "name": login,
                    "login": login,
                    "email": f"{login}@example.invalid",
                    "company_id": cls.company.id,
                    "company_ids": [(6, 0, [cls.company.id])],
                    "groups_id": [(6, 0, groups)],
                }
            )

        cls.manager_user = make_user(
            "cap01c_manager", "smart_construction_core.group_sc_cap_project_manager"
        )
        cls.reader_user = make_user(
            "cap01c_reader", "smart_construction_core.group_sc_cap_project_read"
        )
    @classmethod
    def _run(cls, user, payload):
        env = cls.env(user=user, su=False)
        handler = ProjectInitiationEnterHandler(
            env, context={"trace_id": "cap01c-0123456789abcdef"}, payload=payload
        )
        return handler.handle(payload=payload, ctx={})

    def _count_projects(self):
        return self.env["project.project"].sudo().search_count([])

    def test_01_normal_create_produces_project_record(self):
        before = self._count_projects()
        result = self._run(self.manager_user, {"name": "C1-01 测试项目"})
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["data"]["record"]["model"], "project.project")
        project = self.env["project.project"].browse(result["data"]["record"]["id"])
        self.assertTrue(project.exists())
        self.assertEqual(project.name, "C1-01 测试项目")
        self.assertEqual(self._count_projects(), before + 1)

    def test_02_defaults_apply(self):
        result = self._run(self.manager_user, {"name": "C1-02 测试项目"})
        self.assertTrue(result["ok"], result)
        project = self.env["project.project"].browse(result["data"]["record"]["id"])
        self.assertEqual(project.manager_id, self.manager_user)
        self.assertEqual(project.phase_key, "initiation")
        self.assertEqual(project.lifecycle_state, "draft")

    def test_03_bootstrap_conditional_task_root(self):
        result = self._run(self.manager_user, {"name": "C1-03 测试项目"})
        self.assertTrue(result["ok"], result)
        project = self.env["project.project"].browse(result["data"]["record"]["id"])
        # manager has project.task create access -> a single task root node is created.
        tasks = self.env["project.task"].sudo().search([("project_id", "=", project.id)])
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks.name, "项目根任务（Project Root Task）")
        # bootstrap message was posted.
        messages = self.env["mail.message"].sudo().search(
            [("model", "=", "project.project"), ("res_id", "=", project.id)]
        )
        self.assertTrue(any("项目初始化已完成" in (m.body or "") for m in messages))

    def test_03b_bootstrap_no_duplicate_task_root(self):
        result = self._run(self.manager_user, {"name": "C1-03b 测试项目"})
        self.assertTrue(result["ok"], result)
        project = self.env["project.project"].browse(result["data"]["record"]["id"])
        # Re-running bootstrap must not create a second task root.
        service = ProjectCreationService(self.env(user=self.manager_user))
        service.post_create_bootstrap(project)
        tasks = self.env["project.task"].sudo().search([("project_id", "=", project.id)])
        self.assertEqual(len(tasks), 1)

    def test_04_missing_name_rejected_no_record(self):
        before = self._count_projects()
        result = self._run(self.manager_user, {"name": "   "})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "MISSING_PARAMS")
        self.assertEqual(self._count_projects(), before)

    def test_05_capability_authorization_boundary(self):
        """错误契约：无创建能力的主体被 Odoo 拒绝时，handler 返回 PERMISSION_DENIED。"""
        before = self._count_projects()
        result = self._run(self.reader_user, {"name": "C1-05 只读主体测试"})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "PERMISSION_DENIED")
        self.assertEqual(self._count_projects(), before)

    def test_06_validation_failure_consistent_data(self):
        before = self._count_projects()
        with patch.object(
            ProjectCreationService,
            "normalize_create_vals",
            side_effect=UserError("服务端业务校验失败：无效的项目阶段"),
        ):
            result = self._run(self.manager_user, {"name": "C1-06 测试项目"})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "BUSINESS_RULE_FAILED")
        self.assertEqual(self._count_projects(), before)
