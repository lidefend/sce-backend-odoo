# -*- coding: utf-8 -*-
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "sc_gate", "daily_contract_settlement")
class TestDailyContractSettlement(TransactionCase):
    def _user(self, login, group_xmlid):
        return self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": login,
                "login": login,
                "email": "%s@invalid.local" % login,
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id, self.env.ref(group_xmlid).id])],
            }
        )

    def setUp(self):
        super().setUp()
        self.contract_user = self._user(
            "daily_settlement_contract_user",
            "smart_construction_core.group_sc_cap_contract_user",
        )
        self.project = self.env["project.project"].create(
            {
                "name": "日常合同结算测试项目",
                "user_id": self.contract_user.id,
                "company_id": self.env.company.id,
                "operation_strategy": "direct",
            }
        )
        self.partner = self.env["res.partner"].create({"name": "日常合同往来单位"})

    def _contract(self, direction="expense", name="日常采购合同"):
        return self.env["sc.general.contract"].create(
            {
                "contract_name": name,
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_direction": direction,
                "amount_total": 1000,
                "currency_id": self.env.company.currency_id.id,
                "state": "confirmed",
            }
        )

    def _settlement(self, contract):
        settlement = self.env["sc.settlement.order"].with_context(
            default_contract_source_kind="general_contract"
        ).with_user(self.contract_user).create(
            {"general_contract_id": contract.id, "title": "日常合同首期结算"}
        )
        self.env["sc.settlement.order.line"].with_user(self.contract_user).create(
            {"settlement_id": settlement.id, "name": "首期结算", "qty": 1, "price_unit": 300}
        )
        return settlement

    def test_general_contract_is_explicit_exclusive_settlement_source(self):
        contract = self._contract()
        settlement = self._settlement(contract)
        self.assertEqual(settlement.contract_source_kind, "general_contract")
        self.assertEqual(settlement.general_contract_id, contract)
        self.assertFalse(settlement.contract_id)
        self.assertEqual(settlement.settlement_type, "out")
        self.assertEqual(settlement.project_id, self.project)
        self.assertEqual(settlement.partner_id, self.partner)
        self.assertEqual(settlement.source_contract_model, "sc.general.contract")
        self.assertEqual(settlement.source_contract_res_id, contract.id)
        self.assertEqual(settlement.line_ids.general_contract_id, contract)
        self.assertFalse(settlement.line_ids.contract_id)
        settlement._check_line_contracts_or_raise()

        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            settlement.write({"settlement_type": "in"})

        action = self.env.ref("smart_construction_core.action_sc_product_general_contract_settlement_v1")
        self.assertEqual(action.res_model, "sc.settlement.order")
        self.assertIn("general_contract", action.domain)
        income_action = self.env.ref("smart_construction_core.action_sc_settlement_order_income")
        expense_action = self.env.ref("smart_construction_core.action_sc_settlement_order_expense")
        self.assertIn("contract_source_kind", income_action.domain)
        self.assertIn("contract_source_kind", expense_action.domain)
        contract_surface = self.env.ref(
            "smart_construction_core.business_config_contract_daily_contract_settlement_form_v1"
        )
        self.assertEqual(contract_surface.action_id, action)
        self.assertEqual(
            contract_surface.contract_json["view_orchestration"]["context"]["contract_source_authority"],
            "sc.general.contract",
        )

    def test_unknown_direction_is_not_submittable_and_downstream_identity_is_retained(self):
        neutral = self._contract(direction="neutral", name="方向待确认合同")
        neutral_settlement = self._settlement(neutral)
        with self.assertRaises(UserError):
            neutral_settlement._check_line_contracts_or_raise()

        settlement = self._settlement(self._contract())
        payment = self.env["payment.request"].create(
            {
                "type": "pay",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "settlement_id": settlement.id,
                "amount": 100,
            }
        )
        self.assertEqual(payment.settlement_contract_source_model, "sc.general.contract")
        self.assertEqual(payment.settlement_contract_source_res_id, settlement.general_contract_id.id)

        invoice = self.env["sc.invoice.registration"].create(
            {
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "settlement_id": settlement.id,
                "direction": "input",
                "invoice_no": "DAILY-SETTLEMENT-001",
                "amount_total": 100,
            }
        )
        self.assertEqual(invoice.settlement_contract_source_model, "sc.general.contract")
        self.assertEqual(invoice.settlement_contract_source_res_id, settlement.general_contract_id.id)
