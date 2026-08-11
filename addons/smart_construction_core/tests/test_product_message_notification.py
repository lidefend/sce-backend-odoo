# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "sc_gate", "product_message_notification")
class TestProductMessageNotification(TransactionCase):
    def test_product_entry_uses_native_recipient_notification_authority(self):
        action = self.env.ref("smart_construction_core.action_sc_product_message_notification_v1")
        self.assertEqual(action.res_model, "mail.notification")
        self.assertIn("sc_is_current_recipient", action.domain)
        contract = self.env.ref("smart_construction_core.business_config_contract_mail_notification_form_v1")
        self.assertEqual(contract.action_id, action)

    def test_recipient_filter_and_read_lifecycle(self):
        current_partner = self.env.user.partner_id
        other_partner = self.env["res.partner"].create({"name": "其他消息收件人"})
        message = self.env["mail.message"].create({"subject": "项目提醒", "body": "请检查项目资料", "message_type": "notification"})
        own = self.env["mail.notification"].create({"mail_message_id": message.id, "res_partner_id": current_partner.id, "notification_type": "inbox"})
        other = self.env["mail.notification"].create({"mail_message_id": message.id, "res_partner_id": other_partner.id, "notification_type": "inbox"})
        found = self.env["mail.notification"].search([("sc_is_current_recipient", "=", True), ("id", "in", (own | other).ids)])
        self.assertEqual(found, own)
        own.action_sc_mark_read()
        self.assertTrue(own.is_read)
        self.assertTrue(own.read_date)
        own.action_sc_mark_unread()
        self.assertFalse(own.is_read)
        self.assertFalse(own.read_date)
