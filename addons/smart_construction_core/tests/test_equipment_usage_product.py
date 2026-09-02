# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "sc_gate", "equipment_usage_product")
class TestEquipmentUsageProduct(TransactionCase):
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

    def test_shift_confirmation_is_capability_governed_and_creates_one_cost_fact(self):
        project_reader = self._user(
            "equipment_shift_reader",
            "smart_construction_core.group_sc_cap_project_read",
        )
        project_user = self._user(
            "equipment_shift_user",
            "smart_construction_core.group_sc_cap_project_user",
        )
        project_manager = self._user(
            "equipment_shift_manager",
            "smart_construction_core.group_sc_cap_project_manager",
        )
        project = self.env["project.project"].create(
            {
                "name": "机械台班测试项目",
                "company_id": self.env.company.id,
                "user_id": project_user.id,
                "operation_strategy": "direct",
            }
        )

        with self.assertRaises(AccessError):
            self.env["sc.equipment.usage"].with_user(project_reader).create(
                {
                    "project_id": project.id,
                    "equipment_name": "履带式挖掘机",
                    "usage_location": "一号作业面",
                    "operator_name": "测试操作员",
                    "usage_hours": 1,
                }
            )

        usage = self.env["sc.equipment.usage"].with_user(project_user).create(
            {
                "project_id": project.id,
                "equipment_name": "履带式挖掘机",
                "usage_location": "一号作业面",
                "operator_name": "测试操作员",
                "usage_qty": 2,
                "usage_hours": 3,
                "price_unit": 100,
            }
        )
        self.assertIn("建议关联来源设备申请", usage.processing_advisory)
        self.assertIn("建议上传台班依据", usage.processing_advisory)

        usage.action_submit()
        with self.assertRaises(UserError):
            usage.action_confirm()

        usage.with_user(project_manager).action_confirm()
        self.assertEqual(usage.state, "confirmed")
        self.assertEqual(usage.amount, 600)

        ledgers = self.env["project.cost.ledger"].search(
            [
                ("source_model", "=", "sc.equipment.usage"),
                ("source_id", "=", usage.id),
                ("source_line_id", "=", 0),
            ]
        )
        self.assertEqual(len(ledgers), 1)
        self.assertEqual(ledgers.qty, 6)
        self.assertEqual(ledgers.amount, 600)
        self.assertEqual(ledgers.cost_code_id.type, "machine")
        self.assertEqual(ledgers.recognition_stage, "consumption")
        self.assertEqual(ledgers.reporting_treatment, "operational_actual")

        usage.with_user(project_manager)._sync_project_cost_ledger()
        self.assertEqual(
            self.env["project.cost.ledger"].search_count(
                [("source_model", "=", "sc.equipment.usage"), ("source_id", "=", usage.id)]
            ),
            1,
        )

        action = self.env.ref("smart_construction_core.action_sc_equipment_usage")
        menu = self.env.ref("smart_construction_core.menu_sc_product_equipment_shift_v1")
        self.assertEqual(action.res_model, "sc.equipment.usage")
        self.assertEqual(menu.action, action)
        self.assertEqual(
            action.groups_id,
            self.env.ref("smart_construction_core.group_sc_cap_project_read"),
        )
