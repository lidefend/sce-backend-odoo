# -*- coding: utf-8 -*-
"""Real Odoo cursor request-scope validation for principal group xmlids.

The host-runnable ``test_principal_group_signature_request_scope.py`` proves the
memo logic with a fake cursor; this ORM test proves the same memo works on a
real Odoo cursor and that ``principal_group_signature`` never silently degrades
to an empty signature for a grouped principal.
"""
from unittest.mock import patch

from odoo import api
from odoo.tests.common import TransactionCase, tagged

from ..delivery.runtime_route_authority import (
    _request_cached_user_group_xmlids,
    principal_group_signature,
)
from ..identity.identity_resolver import IdentityResolver


@tagged("post_install", "-at_install", "principal_group_request_scope_orm")
class TestPrincipalGroupSignatureRequestScopeORM(TransactionCase):
    def test_native_implied_group_without_xmlid_invalidates_cached_authority(self):
        from ..delivery import runtime_route_authority
        parent = self.env["res.groups"].create({"name": "Delivery parent without XMLID"})
        child = self.env["res.groups"].create({"name": "Delivery child without XMLID"})
        user = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Native group cache actor", "login": "native-group-cache-actor",
            "groups_id": [(6, 0, [parent.id, self.env.ref("base.group_user").id])],
        })
        env = user.with_user(user).env
        before_xmlids = _request_cached_user_group_xmlids(env)
        before_signature = principal_group_signature(env)
        self.env.registry.clear_cache()
        with patch.object(runtime_route_authority, "_build_runtime_route_authority",
                          side_effect=lambda current: {"native_child_allowed": child.id in current.user.groups_id.ids}):
            self.assertFalse(runtime_route_authority.published_route_authority(env)["native_child_allowed"])
            parent.write({"implied_ids": [(4, child.id)]})
            self.assertIn(child, user.groups_id)
            self.assertEqual(before_xmlids, _request_cached_user_group_xmlids(env))
            self.assertNotEqual(before_signature, principal_group_signature(env))
            self.assertTrue(runtime_route_authority.published_route_authority(env)["native_child_allowed"])

    def test_real_cursor_resolves_and_signs_group_xmlids(self):
        env = self.env
        xmlids = _request_cached_user_group_xmlids(env)
        self.assertTrue(xmlids)
        self.assertEqual(xmlids, IdentityResolver(env).user_group_xmlids(env.user))

        signature = principal_group_signature(env)
        self.assertEqual(len(signature), 40)
        self.assertRegex(signature, r"^[0-9a-f]{40}$")

    def test_same_cursor_keeps_one_stable_signature(self):
        first = principal_group_signature(self.env)
        second = principal_group_signature(self.env)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 40)

    def test_new_cursor_recomputes_without_cross_request_leak(self):
        first_xmlids = _request_cached_user_group_xmlids(self.env)
        first_signature = principal_group_signature(self.env)

        # A fresh cursor models a new request transaction. The memo is keyed by
        # the cursor object, so a new cursor must derive its own entry instead
        # of reusing the previous request's snapshot.
        with self.registry.cursor() as new_cr:
            new_env = api.Environment(new_cr, self.env.uid, self.env.context)
            second_xmlids = _request_cached_user_group_xmlids(new_env)
            second_signature = principal_group_signature(new_env)

        self.assertEqual(first_xmlids, second_xmlids)
        self.assertEqual(first_signature, second_signature)
        self.assertEqual(len(second_signature), 40)
