# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "sc_gate", "subcontract_cost_registration")
class TestSubcontractCostRegistration(TransactionCase):
    def _user(self, login, group_xmlid):
        return self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": login,
                "login": login,
                "email": "%s@invalid.local" % login,
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref(group_xmlid).id,
                        ],
                    )
                ],
            }
        )

    def test_registration_is_committed_cost_not_actual_cost_and_uses_project_capabilities(self):
        project_reader = self._user(
            "subcontract_cost_reader",
            "smart_construction_core.group_sc_cap_project_read",
        )
        project_user = self._user(
            "subcontract_cost_user",
            "smart_construction_core.group_sc_cap_project_user",
        )
        project_manager = self._user(
            "subcontract_cost_manager",
            "smart_construction_core.group_sc_cap_project_manager",
        )
        project = self.env["project.project"].create(
            {
                "name": "分包成本登记测试项目",
                "user_id": project_user.id,
                "operation_strategy": "direct",
            }
        )
        subcontractor = self.env["res.partner"].create(
            {"name": "分包成本登记测试单位", "supplier_rank": 1}
        )

        with self.assertRaises(AccessError):
            self.env["sc.subcontract.register"].with_user(project_reader).create(
                {
                    "project_id": project.id,
                    "subcontract_scope": "主体结构专业分包",
                    "subcontractor_id": subcontractor.id,
                }
            )

        registration = self.env["sc.subcontract.register"].with_user(
            project_user
        ).create(
            {
                "project_id": project.id,
                "subcontract_scope": "主体结构专业分包",
                "subcontractor_id": subcontractor.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "work_scope": "主体结构劳务及辅材",
                            "contract_qty": 1,
                            "unit_name": "项",
                            "registered_amount": 1000,
                        },
                    )
                ],
            }
        )
        self.assertIn("建议关联分包合同", registration.processing_advisory)
        self.assertIn("建议上传分包成本依据", registration.processing_advisory)
        with self.assertRaises(UserError):
            registration.action_register()

        registration.with_user(project_manager).action_register()
        self.assertEqual(registration.state, "active")
        self.assertEqual(registration.registered_amount, 1000)
        self.assertFalse(
            self.env["project.cost.ledger"].search(
                [
                    ("source_model", "=", "sc.subcontract.register"),
                    ("source_id", "=", registration.id),
                ]
            )
        )

        registration.with_user(project_manager).action_cancel()
        registration.with_user(project_manager).action_reset_draft()
        self.assertEqual(registration.state, "draft")

        action = self.env.ref("smart_construction_core.action_sc_subcontract_register")
        menu = self.env.ref("smart_construction_core.menu_sc_product_subcontract_cost_v1")
        self.assertEqual(action.res_model, "sc.subcontract.register")
        self.assertEqual(menu.action, action)
        self.assertEqual(
            action.groups_id,
            self.env.ref("smart_construction_core.group_sc_cap_project_read"),
        )
