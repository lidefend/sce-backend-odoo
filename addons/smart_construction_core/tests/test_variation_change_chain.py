# -*- coding: utf-8 -*-
import json

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "sc_gate", "variation_change_chain")
class TestVariationChangeChain(TransactionCase):
    def _user(self, login, *group_xmlids):
        return self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": login,
                "login": login,
                "email": f"{login}@invalid.local",
                "groups_id": [
                    (
                        6,
                        0,
                        [self.env.ref("base.group_user").id]
                        + [self.env.ref(xmlid).id for xmlid in group_xmlids],
                    )
                ],
            }
        )

    def test_site_fact_contract_change_and_settlement_adjustment_are_distinct(self):
        project_operator = self._user(
            "variation_project_operator",
            "smart_construction_core.group_sc_cap_project_user",
        )
        project_manager = self._user(
            "variation_project_manager",
            "smart_construction_core.group_sc_cap_project_manager",
        )
        contract_operator = self._user(
            "variation_contract_operator",
            "smart_construction_core.group_sc_cap_project_read",
            "smart_construction_core.group_sc_cap_contract_user",
        )
        contract_manager = self._user(
            "variation_contract_manager",
            "smart_construction_core.group_sc_cap_contract_manager",
        )
        settlement_operator = self._user(
            "variation_settlement_operator",
            "smart_construction_core.group_sc_cap_contract_read",
            "smart_construction_core.group_sc_cap_settlement_user",
        )

        project = self.env["project.project"].create({"name": "签证变更链路测试项目"})
        partner = self.env["res.partner"].create({"name": "签证变更链路相对方"})
        contract = self.env["construction.contract"].create(
            {
                "subject": "签证变更链路合同",
                "type": "in",
                "project_id": project.id,
                "partner_id": partner.id,
                "amount_final": 1000,
            }
        )
        subcontract = self.env["construction.contract"].create(
            {
                "subject": "签证变更链路专业分包合同",
                "type": "in",
                "project_id": project.id,
                "partner_id": partner.id,
                "expense_contract_category_id": self.env.ref(
                    "smart_construction_core.dict_expense_contract_category_subcontract"
                ).id,
                "amount_final": 500,
            }
        )

        site_variation = self.env["sc.site.variation"].with_user(project_operator).create(
            {
                "project_id": project.id,
                "contract_id": contract.id,
                "subject": "新增现场排水措施",
                "estimated_amount_delta": 120,
                "estimated_duration_days": 2,
            }
        )
        submit_notice = site_variation.with_user(project_operator).action_submit()
        self.assertEqual(submit_notice.get("tag"), "display_notification")
        site_variation.with_user(project_manager).action_confirm()
        self.assertEqual(site_variation.state, "confirmed")
        self.assertEqual(site_variation.sc_change_revision, 1)
        self.assertEqual(
            json.loads(site_variation.sc_change_current_snapshot)["subject"],
            "新增现场排水措施",
        )

        contract_action = site_variation.with_user(
            contract_operator
        ).action_create_contract_change()
        contract_change = self.env["sc.contract.change"].browse(contract_action["res_id"])
        self.assertEqual(contract_change.source_site_variation_id, site_variation)
        self.assertEqual(contract_change.contract_id, contract)
        self.assertEqual(contract_change.amount_delta, 120)
        self.assertFalse(contract_change.settlement_adjustment_ids)

        contract_change.with_user(contract_operator).action_submit()
        contract_change.with_user(contract_manager).action_effective()
        self.assertEqual(contract_change.state, "effective")
        self.assertEqual(contract.amount_change, 120)
        self.assertEqual(contract.amount_final, (contract.amount_total or 0) + 120)

        settlement_action = contract_change.with_user(
            settlement_operator
        ).action_create_settlement_adjustment()
        adjustment = self.env["sc.settlement.adjustment"].browse(
            settlement_action["res_id"]
        )
        self.assertEqual(adjustment.contract_change_id, contract_change)
        self.assertEqual(adjustment.source_site_variation_id, site_variation)
        self.assertEqual(adjustment.adjustment_type, "addition")
        self.assertEqual(adjustment.amount, 120)

        self.assertEqual(
            self.env.ref("smart_construction_core.action_sc_product_site_variation_v1").res_model,
            "sc.site.variation",
        )
        self.assertEqual(
            self.env.ref("smart_construction_core.action_sc_contract_change").res_model,
            "sc.contract.change",
        )

        subcontract_variation = self.env["sc.site.variation"].with_context(
            default_variation_scope="subcontract"
        ).with_user(project_operator).create(
            {
                "project_id": project.id,
                "contract_id": subcontract.id,
                "subject": "分包范围新增排水沟",
                "estimated_amount_delta": 80,
            }
        )
        self.assertEqual(subcontract_variation.variation_scope, "subcontract")
        subcontract_action = self.env.ref(
            "smart_construction_core.action_sc_product_subcontract_variation_v1"
        )
        subcontract_menu = self.env.ref(
            "smart_construction_core.menu_sc_product_subcontract_variation_v1"
        )
        self.assertEqual(subcontract_action.res_model, "sc.site.variation")
        self.assertEqual(subcontract_action.domain, "[('variation_scope', '=', 'subcontract')]")
        self.assertEqual(subcontract_menu.action, subcontract_action)

        unanchored_subcontract_variation = self.env["sc.site.variation"].with_context(
            default_variation_scope="subcontract"
        ).with_user(project_operator).create(
            {
                "project_id": project.id,
                "subject": "待补充分包合同的现场签证",
            }
        )
        self.assertIn(
            "建议关联分包合同",
            unanchored_subcontract_variation.processing_advisory,
        )
        unanchored_subcontract_variation.with_user(project_operator).action_submit()
        unanchored_subcontract_variation.with_user(project_manager).action_confirm()
        self.assertEqual(unanchored_subcontract_variation.state, "confirmed")

        with self.assertRaises(ValidationError):
            self.env["sc.site.variation"].with_user(project_operator).create(
                {
                    "project_id": project.id,
                    "contract_id": contract.id,
                    "variation_scope": "subcontract",
                    "subject": "错误归入分包费用的普通合同签证",
                }
            )
