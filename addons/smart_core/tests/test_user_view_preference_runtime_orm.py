# -*- coding: utf-8 -*-
"""Runtime lock on the user view preference surface (R5).

The preference surface is a P0 platform mechanism with three responsibilities
that must not be confused:

* the backend owns the *identity* (``action_id`` / ``model``) and *refuses* an
  illegal or mismatched identity before any read or write;
* the stored projection (``projection=stored``) returns storage facts only and
  must never compile a page or resolve a list profile;
* the effective projection reads the declared list policy (declared columns and
  ``preference_policy``) from shared facts, with no page assembler and no empty
  policy fallback.

The product contract itself is *applied* exactly once, by the frontend
consumer, against the declared ``preference_policy``.  The server never reorders
the declared contract with a stored user choice.  This module locks that split
against the real ORM, ACL and stored data - the pure-python boundary tests
cannot see ``get_view``, record rules or the unique scope constraint.
"""

from unittest import mock

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_core.app_config_engine.services.assemblers import page_assembler
from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler
from odoo.addons.smart_core.handlers.user_view_preference import (
    UserViewPreferenceGetHandler,
    UserViewPreferenceSetHandler,
)

TAG = "user_view_preference_runtime"


@tagged("post_install", "-at_install", TAG)
class TestUserViewPreferenceRuntime(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Preference = self.env["sc.user.view.preference"]
        self.uid = self.env.uid

    # ------------------------------------------------------------------ helpers
    def _get(self, **params):
        return UserViewPreferenceGetHandler(self.env, payload=params).handle()

    def _set(self, **params):
        return UserViewPreferenceSetHandler(self.env, payload=params).handle()

    def _own_rows(self, **extra):
        domain = [("user_id", "=", self.uid)] + list(extra.items())
        return self.Preference.search(domain)

    @staticmethod
    def _profile_with_columns(payload):
        """Locate the declared list profile inside a ui.contract.v2 payload."""
        found = []

        def walk(node):
            if isinstance(node, dict):
                if isinstance(node.get("columns"), list) and isinstance(node.get("preference_policy"), dict):
                    found.append(node)
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(payload)
        return found

    # --------------------------------------- requirement 1: illegal identities
    def test_missing_identity_is_refused_for_read_and_write(self):
        before = self._own_rows()
        for result in (self._get(), self._set()):
            self.assertFalse(result["ok"], result)
            self.assertEqual(result["code"], 400, result)
            self.assertIn("action_id", result["error"]["message"])
        self.assertEqual(self._own_rows(), before)

    def test_unregistered_model_sentinel_can_never_be_written(self):
        before = self._own_rows()
        for name in ("unknown", "model:unknown", "ghost.model"):
            result = self._set(model=name, preference_key="list_columns", preference={})
            self.assertFalse(result["ok"], result)
            self.assertEqual(result["code"], 400, result)
        self.assertEqual(self._own_rows(), before)
        # The legacy sentinel can never appear in a stored scope either.
        self.assertFalse(self.Preference.search([("scope_key", "like", "model:unknown")]))

    def test_model_action_mismatch_is_refused_before_write(self):
        action = self.env.ref("base.action_partner_form")
        before = self._own_rows()
        for result in (
            self._get(action_id=action.id, model="res.users", preference_key="list_columns"),
            self._set(action_id=action.id, model="res.users", preference_key="list_columns", preference={}),
        ):
            self.assertFalse(result["ok"], result)
            self.assertEqual(result["code"], 400, result)
            self.assertIn("不一致", result["error"]["message"])
        self.assertEqual(self._own_rows(), before)

    def test_unknown_action_and_non_list_action_are_refused(self):
        before = self._own_rows()
        unknown = self._set(action_id=99999999, preference_key="list_columns", preference={})
        self.assertFalse(unknown["ok"], unknown)
        self.assertEqual(unknown["code"], 400, unknown)

        act_url = self.env["ir.actions.act_url"].create({
            "name": "R5 probe non-list action",
            "url": "https://example.invalid/probe",
            "target": "self",
        })
        non_list = self._set(action_id=act_url.id, preference_key="list_columns", preference={})
        self.assertFalse(non_list["ok"], non_list)
        self.assertEqual(non_list["code"], 400, non_list)
        self.assertIn("列表表面", non_list["error"]["message"])
        self.assertEqual(self._own_rows(), before)

    # ------------------------------------------- requirement 1: legal identity
    def test_action_identity_resolves_the_authoritative_model(self):
        action = self.env.ref("base.action_partner_form")
        result = self._set(
            action_id=action.id,
            preference_key="list_columns",
            view_type="list",
            preference={"visible_columns": ["display_name"], "column_order": ["display_name"]},
        )
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["data"]["scope_key"], "ui:list_columns:list:action:%s" % action.id)
        self.assertEqual(result["data"]["preference"]["visible_columns"], ["display_name"])

        stored = self._get(action_id=action.id, preference_key="list_columns", view_type="list", projection="stored")
        self.assertTrue(stored["ok"], stored)
        self.assertEqual(stored["data"]["scope_key"], "ui:list_columns:list:action:%s" % action.id)
        self.assertEqual(stored["data"]["preference"]["visible_columns"], ["display_name"])

    def test_model_only_identity_is_scoped_without_a_company_component(self):
        result = self._set(
            model="res.partner",
            preference_key="list_columns",
            view_type="list",
            preference={"visible_columns": ["display_name"], "column_order": ["display_name"]},
        )
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["data"]["scope_key"], "ui:list_columns:list:model:res.partner")

    def test_set_response_declares_only_the_declared_surface(self):
        """The write still lands, but no environment-assigned handle is returned.

        ``UserViewPreferenceContract`` declares ``scope_key`` and ``preference``
        only. The row id is assigned by whichever database served the request,
        so returning it would hand the caller an undeclared, unstable identity;
        a caller must resolve its own row through the declared scope instead.
        """
        result = self._set(
            model="res.partner",
            preference_key="list_columns",
            view_type="list",
            preference={"visible_columns": ["display_name"], "column_order": ["display_name"]},
        )
        self.assertTrue(result["ok"], result)
        self.assertEqual(sorted(result["data"]), ["preference", "scope_key"])
        self.assertEqual(result["data"]["preference"]["visible_columns"], ["display_name"])
        row = self.Preference.search([
            ("user_id", "=", self.uid),
            ("scope_key", "=", result["data"]["scope_key"]),
        ], limit=1)
        self.assertTrue(row, "the declared write must still persist a usable row")
        self.assertEqual(row.value_json["visible_columns"], ["display_name"])

    # ------------------------------------- requirement 3: no page assembly
    def test_preference_paths_never_instantiate_the_page_assembler(self):
        self.assertTrue(self._set(
            model="res.partner",
            preference_key="list_columns",
            view_type="list",
            preference={"visible_columns": ["display_name"], "column_order": ["display_name"]},
        )["ok"])

        instantiations = []
        original_init = page_assembler.PageAssembler.__init__

        def counting_init(instance, *args, **kwargs):
            instantiations.append(1)
            return original_init(instance, *args, **kwargs)

        with mock.patch.object(page_assembler.PageAssembler, "__init__", counting_init):
            with mock.patch.object(
                page_assembler.PageAssembler,
                "assemble_page_contract",
                side_effect=AssertionError("stored/effective preference must not compile a page"),
            ):
                stored = self._get(model="res.partner", preference_key="list_columns", projection="stored")
                effective = self._get(model="res.partner", preference_key="list_columns", view_type="list")

        self.assertTrue(stored["ok"], stored)
        self.assertEqual(stored["data"]["policy_source"], "current_page_contract")
        self.assertTrue(effective["ok"], effective)
        self.assertEqual(instantiations, [])

    def test_effective_projection_always_declares_a_policy_never_an_empty_one(self):
        result = self._get(model="res.partner", preference_key="list_columns", view_type="list")
        self.assertTrue(result["ok"], result)
        contract = result["meta"]["preference_contract"]
        self.assertTrue(contract["columns"], contract)
        self.assertTrue(contract["preference_policy"]["must_request_columns"], contract)
        self.assertIsInstance(contract["preference_policy"]["allow_order"], bool)

    # ------------------------------- requirement 4: applied exactly once
    def test_server_never_applies_a_stored_order_to_the_declared_contract(self):
        handler = UiContractV2Handler(self.env, su_env=self.env["ir.model"].sudo().env)
        params = {"op": "model", "model": "res.partner", "view_type": "list"}

        before = handler.handle(dict(params))
        before = before.to_legacy_dict() if hasattr(before, "to_legacy_dict") else before
        profiles = self._profile_with_columns(before)
        self.assertTrue(profiles, "the list contract must declare a list profile")
        declared = list(profiles[0]["columns"])
        self.assertGreaterEqual(len(declared), 2, declared)

        reordered = list(reversed(declared))
        stored_write = self._set(
            model="res.partner",
            preference_key="list_columns",
            view_type="list",
            preference={
                "visible_columns": reordered,
                "column_order": reordered,
                "column_widths": {},
                "hidden_columns": [],
            },
        )
        self.assertTrue(stored_write["ok"], stored_write)
        self.assertEqual(stored_write["data"]["preference"]["column_order"], reordered)

        after = handler.handle(dict(params))
        after = after.to_legacy_dict() if hasattr(after, "to_legacy_dict") else after
        after_profiles = self._profile_with_columns(after)
        self.assertTrue(after_profiles, "the list contract must declare a list profile")
        self.assertEqual(after_profiles[0]["columns"], declared)

        # The user choice is handed to the single frontend consumer unchanged.
        effective = self._get(model="res.partner", preference_key="list_columns", view_type="list")
        self.assertTrue(effective["ok"], effective)
        self.assertEqual(effective["data"]["preference"]["column_order"], reordered)

    def test_a_missing_declared_policy_is_refused_not_defaulted(self):
        # No declared list surface resolves -> the effective read refuses. It must
        # not answer with an empty policy (which would read as "nothing allowed").
        with mock.patch(
            "odoo.addons.smart_core.core.list_preference_policy.ListPreferencePolicy.project",
            side_effect=__import__(
                "odoo.addons.smart_core.core.list_preference_policy", fromlist=["x"]
            ).ListPreferencePolicyError(422, "list preference policy unavailable"),
        ):
            result = self._get(model="res.partner", preference_key="list_columns", view_type="list")
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["code"], 422, result)
