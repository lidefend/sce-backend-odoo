# -*- coding: utf-8 -*-
"""Permission-boundary regression for Native View Projection.

project_native_view must call get_view()/fields_get() with the caller's own
environment.  A user without project.project read access must therefore get a
strictly pruned field set, never the superuser's full view.
"""
from __future__ import annotations

from odoo.tests.common import TransactionCase

from odoo.addons.smart_core.core.native_view_projection import project_native_view


class TestNativeViewPermissionProjection(TransactionCase):
    def test_unprivileged_user_gets_pruned_field_subset(self):
        admin_view = project_native_view(
            self.env,
            "project.project",
            action_id=590,
            view_id=1776,
            view_type="form",
        )
        admin_fields = {occurrence.field_code for occurrence in admin_view.fields}

        user = (
            self.env["res.users"]
            .sudo()
            .create({
                "name": "NoRead Project Probe",
                "login": "noread_project_probe_%s" % self.env.uid,
                "groups_id": [],
            })
        )
        try:
            restricted_env = self.env(user=user.id)
            restricted_view = project_native_view(
                restricted_env,
                "project.project",
                action_id=590,
                view_id=1776,
                view_type="form",
            )
        finally:
            user.sudo().unlink()

        restricted_fields = {
            occurrence.field_code for occurrence in restricted_view.fields
        }
        self.assertTrue(admin_fields, "admin projection must expose fields")
        self.assertTrue(restricted_fields, "restricted projection must expose its allowed fields")
        self.assertTrue(restricted_fields <= admin_fields)
        # The boundary proof: the restricted user must not see every admin field.
        self.assertLess(len(restricted_fields), len(admin_fields))

