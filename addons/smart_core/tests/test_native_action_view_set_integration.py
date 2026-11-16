from __future__ import annotations

from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_core.app_config_engine.services.assemblers.page_assembler import PageAssembler
from odoo.addons.smart_core.app_config_engine.services.dispatchers.action_dispatcher import ActionDispatcher
from odoo.addons.smart_core.app_config_engine.services.resolvers.action_resolver import ActionResolver
from odoo.addons.smart_core.core.native_action_view_set import (
    NATIVE_ACTION_VIEW_OVERRIDE_AUTHORIZED,
    has_authorized_action_view_override,
)
from odoo.addons.smart_core.handlers.ui_contract_preview import build_projection_environments


@tagged("post_install", "-at_install", "smart_core", "native_action_view_set")
class TestNativeActionViewSetIntegration(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tree = cls.env["ir.ui.view"].create({
            "name": "P0-1 native action tree",
            "model": "res.partner",
            "type": "tree",
            "arch": '<tree><field name="name"/></tree>',
        })
        cls.form = cls.env["ir.ui.view"].create({
            "name": "P0-1 native action form",
            "model": "res.partner",
            "type": "form",
            "arch": '<form><sheet><field name="name"/></sheet></form>',
        })
        cls.unbound_form = cls.env["ir.ui.view"].create({
            "name": "P0-1 unbound form",
            "model": "res.partner",
            "type": "form",
            "arch": '<form><sheet><field name="display_name"/></sheet></form>',
        })
        cls.search = cls.env["ir.ui.view"].create({
            "name": "P0-1 native action search",
            "model": "res.partner",
            "type": "search",
            "arch": '<search><field name="name"/></search>',
        })
        cls.action = cls.env["ir.actions.act_window"].create({
            "name": "P0-1 native action identity",
            "res_model": "res.partner",
            "view_mode": "tree,form,pivot",
            "view_id": cls.tree.id,
            "search_view_id": cls.search.id,
            "view_ids": [
                (0, 0, {"sequence": 20, "view_mode": "tree", "view_id": cls.tree.id}),
                (0, 0, {"sequence": 10, "view_mode": "form", "view_id": cls.form.id}),
            ],
        })

    def _verified_preview_env(self):
        token = "p0-1-preview-%s" % self._testMethodName
        self.env["ui.business.config.change.set"].sudo().create({
            "name": "P0-1 preview authority",
            "state": "ready",
            "preview_token": token,
            "preview_expires_at": fields.Datetime.now() + timedelta(minutes=5),
        })
        actor, _metadata = build_projection_environments(
            self.env,
            self.env,
            {"preview_token": token},
            {},
        )
        return actor

    def _dispatch_model(self, *, env=None, action_id=None, view_id=None):
        source, _versions = ActionDispatcher(
            env or self.env,
            self.env["ir.model"].sudo().env,
        ).dispatch({
            "subject": "model",
            "model": "res.partner",
            "action_id": self.action.id if action_id is None else action_id,
            "view_type": "form",
            "view_id": view_id,
        })
        return source

    def test_resolver_preserves_effective_action_views_and_identity(self):
        info = ActionResolver(self.env).as_action_info(self.action)

        effective_types = [
            "tree" if str(view_type).lower() == "list" else str(view_type).lower()
            for _view_id, view_type in self.action.views
        ]
        self.assertEqual(
            [row["viewType"] for row in info["views"][:len(effective_types)]],
            effective_types,
        )
        self.assertEqual(info["view_set"]["orderAuthority"], "ir.actions.act_window.views")
        self.assertEqual(info["view_set"]["supplementedViewTypes"], [])
        self.assertEqual(info["view_id"], self.tree.id)
        self.assertEqual(info["view_type"], "tree")
        self.assertEqual(info["search_view_id"], self.search.id)
        self.assertNotIn("menuId", info)
        self.assertNotIn("sceneKey", info)

    def test_resolver_keeps_action_xmlid_without_menu_identity(self):
        action = self.env.ref("base.action_partner_form")
        info = ActionResolver(self.env).as_action_info(action)

        self.assertEqual(info["xml_id"], "base.action_partner_form")
        self.assertEqual(info["res_model"], "res.partner")
        self.assertNotIn("menuId", info)
        self.assertNotIn("sceneKey", info)

    def test_normalized_action_identity_survives_a_second_projection(self):
        resolver = ActionResolver(self.env)
        info = resolver.as_action_info(self.action)
        normalized = resolver.normalize_action_dict(info)

        self.assertEqual(normalized["view_id"], info["view_id"])
        self.assertEqual(normalized["view_type"], info["view_type"])
        self.assertEqual(normalized["view_mode"], info["view_mode"])
        self.assertEqual(normalized["view_set"], info["view_set"])
        self.assertEqual(normalized["search_view_id"], info["search_view_id"])
        self.assertEqual(normalized["search_view_xmlid"], info["search_view_xmlid"])

    def test_requested_view_must_match_action_candidate(self):
        info = ActionResolver(self.env).as_action_info(self.action)

        PageAssembler._validate_requested_action_view(
            info,
            requested_view_id=self.form.id,
            requested_view_type="form",
        )
        with self.assertRaisesRegex(ValueError, "ACTION_VIEW_REQUEST_OVERRIDE_DENIED"):
            PageAssembler._validate_requested_action_view(
                info,
                requested_view_id=self.unbound_form.id,
                requested_view_type="form",
            )

    def test_requested_view_never_skips_an_incomplete_action_identity(self):
        with self.assertRaisesRegex(ValueError, "ACTION_VIEW_SET_UNRESOLVED"):
            PageAssembler._validate_requested_action_view(
                {"id": self.action.id, "name": self.action.name},
                requested_view_id=self.form.id,
                requested_view_type="form",
            )

    def test_authorized_override_is_the_only_non_candidate_path(self):
        info = ActionResolver(self.env).as_action_info(self.action)

        PageAssembler._validate_requested_action_view(
            info,
            requested_view_id=self.unbound_form.id,
            requested_view_type="form",
            authorized_override=True,
        )

    def test_action_dispatch_rejects_unbound_view(self):
        with self.assertRaisesRegex(ValueError, "ACTION_VIEW_REQUEST_OVERRIDE_DENIED"):
            ActionDispatcher(
                self.env,
                self.env["ir.model"].sudo().env,
            ).dispatch({
                "subject": "action",
                "action_id": self.action.id,
                "view_type": "form",
                "view_id": self.unbound_form.id,
            })

    def test_model_dispatch_uses_the_complete_action_view_set(self):
        bound = self._dispatch_model(view_id=self.form.id)
        self.assertEqual(bound["action_identity"]["action_id"], self.action.id)
        self.assertEqual(bound["view_id"], self.form.id)

        with self.assertRaisesRegex(ValueError, "ACTION_VIEW_REQUEST_OVERRIDE_DENIED"):
            self._dispatch_model(view_id=self.unbound_form.id)

    def test_model_dispatch_without_action_keeps_model_view_projection(self):
        source = self._dispatch_model(action_id=0, view_id=self.unbound_form.id)

        self.assertNotIn("action_identity", source)
        self.assertEqual(source["view_id"], self.unbound_form.id)

    def test_model_dispatch_rejects_unresolved_action_identity(self):
        with self.assertRaisesRegex(ValueError, "ACTION_IDENTITY_UNRESOLVED"):
            self._dispatch_model(action_id=999999999, view_id=self.form.id)

    def test_model_dispatch_accepts_only_verified_preview_override(self):
        verified = self._dispatch_model(
            env=self._verified_preview_env(),
            view_id=self.unbound_form.id,
        )
        self.assertEqual(verified["view_id"], self.unbound_form.id)

        fake_context = {
            **self.env.context,
            NATIVE_ACTION_VIEW_OVERRIDE_AUTHORIZED: True,
        }
        fake_env, _metadata = build_projection_environments(
            self.env,
            self.env,
            {},
            fake_context,
        )
        with self.assertRaisesRegex(ValueError, "ACTION_VIEW_REQUEST_OVERRIDE_DENIED"):
            self._dispatch_model(env=fake_env, view_id=self.unbound_form.id)

    def test_only_verified_preview_marks_request_view_override_authority(self):
        actor = self._verified_preview_env()
        self.assertTrue(has_authorized_action_view_override(actor.context))

        unverified_context = {
            NATIVE_ACTION_VIEW_OVERRIDE_AUTHORIZED: True,
        }
        actor, _metadata = build_projection_environments(
            self.env,
            self.env,
            {},
            unverified_context,
        )
        self.assertFalse(has_authorized_action_view_override(actor.context))

    def test_page_assembler_publishes_internal_action_identity_carrier(self):
        source, _versions = ActionDispatcher(self.env, self.env["ir.model"].sudo().env).dispatch({
            "subject": "action",
            "action_id": self.action.id,
            "view_type": "tree",
        })

        self.assertEqual(source["action_identity"]["action_id"], self.action.id)
        self.assertEqual(source["action_identity"]["search_view_id"], self.search.id)
        self.assertEqual(
            source["action_view_set"]["orderAuthority"],
            "ir.actions.act_window.views",
        )
        self.assertIn("tree", source["views"])
        self.assertIn("form", source["views"])
