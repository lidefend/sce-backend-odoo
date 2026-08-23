# -*- coding: utf-8 -*-
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged

from ..seed.steps import step_payment_request_floorplan_demo as fixture_step


@tagged("post_install", "-at_install", "payment_request_fixture_ownership")
class TestPaymentRequestFloorplanFixtureOwnership(TransactionCase):
    def _values(self, name):
        contract = self.env.ref("smart_construction_demo.sc_demo_contract_in_069_payment")
        return {
            "name": name,
            "type": "pay",
            "project_id": contract.project_id.id,
            "contract_id": contract.id,
            "partner_id": contract.partner_id.id,
            "amount": 1.0,
            "date_request": "2025-08-22",
        }

    def test_reset_refuses_unowned_same_name_record(self):
        name = "TEST-DEMO-PR-UNOWNED"
        xmlid = "smart_construction_demo.test_payment_request_floorplan_unowned"
        unowned = self.env["payment.request"].sudo().create(self._values(name))

        with patch.object(fixture_step, "FIXTURE_NAME", name), patch.object(fixture_step, "FIXTURE_XMLID", xmlid):
            with self.assertRaisesRegex(RuntimeError, "refuses to delete or adopt unowned"):
                fixture_step.run(self.env)

        self.assertTrue(unowned.exists())
        self.assertFalse(self.env.ref(xmlid, raise_if_not_found=False))

    def test_reset_replaces_only_xmlid_owned_record_and_rebinds_owner(self):
        name = "TEST-DEMO-PR-OWNED"
        xmlid = "smart_construction_demo.test_payment_request_floorplan_owned"
        unrelated = self.env["payment.request"].sudo().create(self._values("TEST-DEMO-PR-UNRELATED"))

        with patch.object(fixture_step, "FIXTURE_NAME", name), patch.object(fixture_step, "FIXTURE_XMLID", xmlid):
            first = fixture_step.run(self.env)
            first_record = self.env.ref(xmlid)
            self.assertEqual(first_record.id, first["payment_request_id"])

            second = fixture_step.run(self.env)
            second_record = self.env.ref(xmlid)

        self.assertFalse(first_record.exists())
        self.assertNotEqual(first["payment_request_id"], second["payment_request_id"])
        self.assertEqual(second_record.id, second["payment_request_id"])
        self.assertEqual(second_record.name, name)
        self.assertTrue(unrelated.exists())
