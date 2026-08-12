# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "sc_gate", "partner_blacklist")
class TestPartnerBlacklistCapability(TransactionCase):
    def _create_user(self, login, group_xmlid):
        return self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": login,
                "login": login,
                "email": f"{login}@invalid.local",
                "groups_id": [
                    (
                        6,
                        0,
                        [self.env.ref("base.group_user").id, self.env.ref(group_xmlid).id],
                    )
                ],
            }
        )

    def test_blacklist_uses_sc_contact_capability_and_non_blocking_advisory(self):
        contact_manager = self._create_user(
            "partner_blacklist_contact_manager",
            "smart_construction_core.group_sc_cap_contact_manager",
        )
        project_manager = self._create_user(
            "partner_blacklist_project_manager",
            "smart_construction_core.group_sc_cap_project_manager",
        )
        partner = self.env["res.partner"].create({"name": "Blacklist Capability Partner"})

        with self.assertRaises(UserError):
            partner.with_user(project_manager).action_sc_add_blacklist()

        notification = partner.with_user(contact_manager).action_sc_add_blacklist()
        self.assertTrue(partner.sc_blacklisted)
        self.assertEqual(notification.get("tag"), "display_notification")
        self.assertIn("建议补充列入原因", partner.sc_blacklist_advisory)

        partner.with_user(contact_manager).write(
            {
                "sc_blacklist_reason": "履约风险观察",
                "sc_blacklist_review_date": "2026-09-01",
            }
        )
        self.assertEqual(partner.sc_blacklist_advisory, "治理信息已完善")
        partner.with_user(contact_manager).action_sc_remove_blacklist()
        self.assertFalse(partner.sc_blacklisted)

