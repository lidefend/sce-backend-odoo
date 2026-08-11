# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "sc_gate", "labor_product")
class TestLaborProductCapability(TransactionCase):
    def _user(self, login, group_xmlid):
        return self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": login,
                "login": login,
                "email": f"{login}@invalid.local",
                "groups_id": [
                    (
                        6,
                        0,
                        [self.env.ref("base.group_user").id, self.env.ref(group_xmlid).id],
                    )
                ],
            }
        )

    def test_labor_surfaces_use_project_capabilities_and_non_blocking_advisories(self):
        operator = self._user(
            "labor_product_operator", "smart_construction_core.group_sc_cap_project_user"
        )
        reader = self._user(
            "labor_product_reader", "smart_construction_core.group_sc_cap_project_read"
        )
        unrelated_internal = self._user(
            "labor_unrelated_internal", "smart_construction_core.group_sc_internal_user"
        )
        project = self.env["project.project"].create({"name": "劳务产品能力测试项目"})

        with self.assertRaises(AccessError):
            self.env["sc.labor.worker"].with_user(unrelated_internal).create(
                {"name": "越权人员", "project_id": project.id}
            )

        worker = self.env["sc.labor.worker"].with_user(operator).create(
            {"name": "张三", "project_id": project.id}
        )
        notification = worker.with_user(operator).action_activate()
        self.assertEqual(worker.state, "active")
        self.assertEqual(notification.get("tag"), "display_notification")
        self.assertIn("建议补充证件号码", worker.processing_advisory)
        self.assertEqual(worker.with_user(reader).read(["name"])[0]["name"], "张三")
        with self.assertRaises(AccessError):
            worker.with_user(reader).write({"trade": "木工"})

        deduction = self.env["sc.labor.deduction"].with_user(operator).create(
            {
                "project_id": project.id,
                "worker_id": worker.id,
                "amount": 100,
            }
        )
        deduction_notice = deduction.with_user(operator).action_confirm()
        self.assertEqual(deduction.state, "confirmed")
        self.assertEqual(deduction_notice.get("tag"), "display_notification")
        self.assertIn("建议补充扣款事由", deduction.processing_advisory)

        usage = self.env["sc.labor.usage"].with_user(operator).create(
            {
                "project_id": project.id,
                "labor_team": "一班",
                "work_content": "现场作业",
                "worker_qty": 1,
            }
        )
        self.assertTrue(usage.with_user(operator).action_submit())
        self.assertEqual(usage.state, "submitted")
        self.assertIn("建议补充用工单价", usage.processing_advisory)

        self.assertEqual(
            self.env.ref("smart_construction_core.action_sc_product_labor_realname_v1").res_model,
            "sc.labor.worker",
        )
        self.assertEqual(
            self.env.ref("smart_construction_core.action_sc_product_labor_deduction_v1").res_model,
            "sc.labor.deduction",
        )
