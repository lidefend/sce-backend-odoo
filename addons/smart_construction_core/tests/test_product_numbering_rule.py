# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "sc_gate", "product_numbering_rule")
class TestProductNumberingRule(TransactionCase):
    def setUp(self):
        super().setUp()
        self.user = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "numbering_config_admin", "login": "numbering_config_admin", "email": "numbering@invalid.local",
            "groups_id": [(6, 0, [self.env.ref("base.group_user").id, self.env.ref("smart_construction_core.group_sc_cap_config_admin").id])],
        })
        self.product_sequence = self.env["ir.sequence"].sudo().create({"name": "测试业务编号", "code": "sc.test.numbering", "prefix": "TEST-", "padding": 4})
        self.technical_sequence = self.env["ir.sequence"].sudo().create({"name": "测试技术编号", "code": "technical.test.numbering"})

    def test_action_and_record_rule_only_expose_product_sequences(self):
        action = self.env.ref("smart_construction_core.action_sc_product_numbering_rule_v1")
        self.assertEqual(action.res_model, "ir.sequence")
        self.assertIn("sc_product_configurable", action.domain)
        visible = self.env["ir.sequence"].with_user(self.user).search([("id", "in", [self.product_sequence.id, self.technical_sequence.id])])
        self.assertEqual(visible, self.product_sequence)
        self.product_sequence.with_user(self.user).write({"prefix": "NEW-"})
        with self.assertRaises(AccessError), self.env.cr.savepoint():
            self.product_sequence.with_user(self.user).write({"code": "sc.changed"})

        contract = self.env.ref("smart_construction_core.business_config_contract_product_numbering_rule_form_v1")
        self.assertEqual(contract.action_id, action)
