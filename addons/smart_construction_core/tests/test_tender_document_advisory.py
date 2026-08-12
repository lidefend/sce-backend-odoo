# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import AccessError


@tagged("post_install", "-at_install", "sc_gate", "tender_document")
class TestTenderDocumentAdvisory(TransactionCase):
    def _project_operator(self):
        return self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "招投标经办用户",
                "login": "tender_project_operator",
                "email": "tender-project-operator@invalid.local",
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

    def _project_reader(self):
        return self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "招投标只读用户",
                "login": "tender_project_reader",
                "email": "tender-project-reader@invalid.local",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref(
                                "smart_construction_core.group_sc_cap_project_read"
                            ).id,
                        ],
                    )
                ],
            }
        )

    def test_project_reader_can_open_tender_workspace_but_cannot_mutate(self):
        project = self.env["project.project"].create({"name": "只读招投标测试项目"})
        bid = self.env["tender.bid"].create(
            {"project_id": project.id, "tender_name": "只读招投标测试"}
        )
        application = self.env["tender.doc.purchase"].create({"bid_id": bid.id})
        reader = self._project_reader()

        reader_bid = bid.with_user(reader)
        self.assertEqual(reader_bid.read(["tender_name"])[0]["tender_name"], "只读招投标测试")
        self.assertEqual(
            application.with_user(reader).read(["bid_id"])[0]["bid_id"][0], bid.id
        )
        with self.assertRaises(AccessError):
            reader_bid.write({"note": "不允许只读用户修改"})

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

    def test_product_tender_surfaces_are_distinct_and_advisory_driven(self):
        operator = self._project_operator()
        opportunity = self.env["tender.opportunity"].with_user(operator).create(
            {"name": "待评估招标信息"}
        )

        opportunity.with_user(operator).action_follow()
        self.assertEqual(opportunity.state, "following")
        self.assertIn("建议补充招标编号", opportunity.processing_advisory)

        project = self.env["project.project"].create({"name": "标书工作台测试项目"})
        bid = self.env["tender.bid"].create(
            {"project_id": project.id, "tender_name": "标书工作台测试"}
        )
        document = self.env["tender.document"].with_user(operator).create(
            {"name": "技术标初稿", "bid_id": bid.id}
        )
        notification = document.with_user(operator).action_submit()

        self.assertEqual(document.state, "submitted")
        self.assertEqual(notification.get("tag"), "display_notification")
        self.assertIn("建议上传标书文件", document.processing_advisory)
        self.assertEqual(
            self.env.ref(
                "smart_construction_core.action_sc_product_tender_information_v1"
            ).res_model,
            "tender.opportunity",
        )
        self.assertEqual(
            self.env.ref(
                "smart_construction_core.action_sc_product_tender_document_v1"
            ).res_model,
            "tender.document",
        )
