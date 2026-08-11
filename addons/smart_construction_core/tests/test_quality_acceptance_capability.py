# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "sc_gate", "quality_acceptance")
class TestQualityAcceptanceCapability(TransactionCase):
    def _operator(self):
        return self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "质量验收经办人",
                "login": "quality_acceptance_operator",
                "email": "quality-acceptance-operator@invalid.local",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref(
                                "smart_construction_core.group_sc_cap_project_user"
                            ).id,
                        ],
                    )
                ],
            }
        )

    def test_quality_acceptance_is_not_quality_issue_and_uses_advisories(self):
        operator = self._operator()
        project = self.env["project.project"].create({"name": "质量验收测试项目"})
        acceptance = self.env["sc.quality.acceptance"].with_user(operator).create(
            {
                "project_id": project.id,
                "name": "一层隐蔽工程验收",
                "acceptance_type": "hidden_work",
            }
        )

        with self.assertRaises(UserError):
            acceptance.with_user(operator).action_confirm()

        acceptance.with_user(operator).write({"result": "passed"})
        notification = acceptance.with_user(operator).action_confirm()

        self.assertEqual(acceptance.state, "confirmed")
        self.assertEqual(notification.get("tag"), "display_notification")
        self.assertIn("建议补充验收部位", acceptance.processing_advisory)
        self.assertIn("建议上传验收资料", acceptance.processing_advisory)
        self.assertEqual(
            self.env.ref(
                "smart_construction_core.action_sc_product_quality_acceptance_v1"
            ).res_model,
            "sc.quality.acceptance",
        )
