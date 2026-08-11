# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "sc_gate", "office_asset")
class TestOfficeAsset(TransactionCase):
    def test_asset_lifecycle_and_entry_contract(self):
        asset = self.env["sc.office.asset"].create({"asset_code": "OA-001", "name": "办公电脑", "category": "computer"})
        with self.assertRaises(UserError), self.env.cr.savepoint():
            asset.action_assign()
        employee = self.env["hr.employee"].create({"name": "资产保管人"})
        asset.custodian_id = employee
        asset.action_assign()
        self.assertEqual(asset.status, "in_use")
        asset.action_return()
        self.assertEqual(asset.status, "available")
        self.assertFalse(asset.custodian_id)
        action = self.env.ref("smart_construction_core.action_sc_product_office_asset_v1")
        self.assertEqual(action.res_model, "sc.office.asset")
        contract = self.env.ref("smart_construction_core.business_config_contract_office_asset_form_v1")
        self.assertEqual(contract.action_id, action)
