# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "sc_gate", "tender_document")
class TestTenderDocumentAdvisory(TransactionCase):
    def test_incomplete_document_submits_with_non_blocking_advisory(self):
        project = self.env["project.project"].create({"name": "投标办理建议测试项目"})
        bid = self.env["tender.bid"].create(
            {
                "project_id": project.id,
                "tender_name": "投标办理建议测试",
            }
        )
        application = self.env["tender.doc.purchase"].create(
            {
                "bid_id": bid.id,
                "apply_date": False,
                "amount": 0,
            }
        )

        notification = application.action_submit()

        self.assertEqual(application.state, "submitted")
        self.assertEqual(notification.get("tag"), "display_notification")
        self.assertIn("建议补充申请日期", application.processing_advisory)
        self.assertIn("建议补充有效金额", application.processing_advisory)
        self.assertIn("建议补充收款账户", application.processing_advisory)

    def test_complete_document_submits_without_warning(self):
        project = self.env["project.project"].create({"name": "完整投标资料测试项目"})
        bid = self.env["tender.bid"].create(
            {
                "project_id": project.id,
                "tender_name": "完整投标资料测试",
            }
        )
        application = self.env["tender.doc.purchase"].create(
            {
                "bid_id": bid.id,
                "amount": 100,
                "payment_method": "银行转账",
                "receipt_partner_name": "测试收款单位",
                "receipt_bank_account": "TEST-ACCOUNT",
            }
        )

        self.assertTrue(application.action_submit())
        self.assertEqual(application.processing_advisory, "当前办理资料已完善")
