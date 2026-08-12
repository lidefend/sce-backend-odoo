# -*- coding: utf-8 -*-
from odoo.tests import TransactionCase
from odoo.tests.common import tagged


@tagged("post_install", "-at_install")
class TestTenderGuaranteeVisibleFields(TransactionCase):
    def test_document_number_falls_back_to_bid_number(self):
        project = self.env["project.project"].create({"name": "Guarantee Project"})
        bid = self.env["tender.bid"].create(
            {
                "tender_name": "Guarantee Bid",
                "project_id": project.id,
            }
        )
        guarantee = self.env["tender.guarantee"].create(
            {
                "bid_id": bid.id,
                "type": "out",
                "amount": 1000,
                "legacy_visible_document_no": "LEGACY-GUARANTEE-001",
            }
        )

        guarantee._compute_deposit_return_visible_fields()

        self.assertEqual(guarantee.deposit_document_no, bid.name)
