# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "sc_gate", "res_users_audience_group")
class TestResUsersAudienceGroupBoundary(TransactionCase):
    """Lock the superuser ``has_group`` pass-through against audience groups.

    ``smart_core`` restores "superuser can act" semantics inside
    ``res.users._has_group`` so capability guards keep working for shell, script
    and fixture flows.  That pass-through must never fabricate membership in the
    two groups Odoo core uses to classify *who a user is* (public / portal):
    ``_is_public``, ``res.partner.is_public`` and the mail channel-membership
    guard all read them as facts, and misclassifying OdooBot (uid 1) as a public
    user makes core reject fixture user provisioning.
    """

    def _probe_group(self):
        group = self.env["res.groups"].sudo().create(
            {"name": "Audience boundary probe group"}
        )
        self.env["ir.model.data"].sudo().create(
            {
                "module": "smart_core",
                "name": "test_audience_boundary_probe_group",
                "model": "res.groups",
                "res_id": group.id,
                "noupdate": True,
            }
        )
        return group, "smart_core.test_audience_boundary_probe_group"

    def test_superuser_keeps_capability_passthrough(self):
        group, xmlid = self._probe_group()
        self.assertFalse(group.users, "probe group must have no real members")
        su_env = api.Environment(self.env.cr, SUPERUSER_ID, {})
        self.assertTrue(
            su_env.user.has_group(xmlid),
            "superuser capability pass-through must survive for non-audience groups",
        )

    def test_superuser_is_not_public_or_portal(self):
        su_env = api.Environment(self.env.cr, SUPERUSER_ID, {})
        su_user = su_env.user
        self.assertFalse(su_user.has_group("base.group_public"))
        self.assertFalse(su_user.has_group("base.group_portal"))
        self.assertFalse(su_user._is_public())
        self.assertFalse(su_user._is_portal())
        self.assertFalse(su_user.partner_id.is_public)

    def test_real_audience_membership_is_still_reported(self):
        public_user = self.env.ref("base.public_user").sudo()
        self.assertTrue(public_user._is_public())
        portal_group = self.env.ref("base.group_portal")
        portal_user = (
            self.env["res.users"]
            .sudo()
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Audience boundary portal probe",
                    "login": "audience-boundary-portal-probe",
                    "company_id": self.env.company.id,
                    "company_ids": [(6, 0, [self.env.company.id])],
                    "groups_id": [(6, 0, [portal_group.id])],
                }
            )
        )
        self.assertTrue(portal_user.has_group("base.group_portal"))
        self.assertFalse(portal_user.has_group("base.group_public"))
