# -*- coding: utf-8 -*-
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_core.delivery import runtime_route_authority
from odoo.addons.smart_core.delivery.runtime_route_authority import menu_publication_decision
from odoo.addons.smart_core.security.intent_permission import _published_menu_decision


def _authority(*, pairs=(), containers=()):
    """A published route authority declaration for the current principal."""
    return {
        "primary_actions": [{"menu_id": menu_id, "action_id": action_id} for menu_id, action_id in pairs],
        "menu_containers": [{"menu_id": menu_id} for menu_id in containers],
    }


@tagged("post_install", "-at_install", "smart_core", "intent_permission_menu_visibility")
class TestIntentPermissionMenuPublication(TransactionCase):
    """The intent menu gate must consume the published navigation authority.

    Native menu existence or visibility is not release authorization
    (``.agent/decisions/contract-first.yaml``), and one navigation contract owns
    both the rendered tree and its route authority
    (``addons/smart_core/handlers/system_init.py``). The gate therefore decides
    from the published route authority and fails closed when it is unavailable.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Menu = cls.env["ir.ui.menu"]
        cls.group_held = cls.env["res.groups"].create({"name": "T Publication Held"})
        cls.env["ir.model.access"].create(
            {
                "name": "T Publication res.partner read",
                "model_id": cls.env.ref("base.model_res_partner").id,
                "group_id": cls.group_held.id,
                "perm_read": True,
            }
        )
        cls.user = cls.env["res.users"].create(
            {
                "name": "T Publication User",
                "login": "t_intent_menu_publication",
                "groups_id": [(6, 0, [cls.env.ref("base.group_user").id, cls.group_held.id])],
            }
        )

    def _native_menu(self, name):
        action = self.env["ir.actions.act_window"].create(
            {"name": name, "res_model": "res.partner", "view_mode": "tree,form"}
        )
        menu = self.Menu.create({"name": name, "action": f"ir.actions.act_window,{action.id}"})
        return menu, action

    def test_declared_pair_is_authorized_and_mismatched_pair_is_not(self):
        authority = _authority(pairs=[(182, 291)])
        self.assertTrue(menu_publication_decision(authority, 182, 291))
        self.assertFalse(menu_publication_decision(authority, 182, 999))

    def test_declared_container_is_authorized_without_action(self):
        self.assertTrue(menu_publication_decision(_authority(containers=[181]), 181, 0))

    def test_native_visible_menu_without_publication_is_denied(self):
        menu, action = self._native_menu("T Unpublished Menu")
        # Baseline first: the menu genuinely is natively visible to this user,
        # so the denial below proves publication is what decides.
        visible = {int(menu_id) for menu_id in self.Menu.with_user(self.user)._visible_menu_ids(debug=False)}
        self.assertIn(int(menu.id), visible)
        self.assertFalse(menu_publication_decision(_authority(pairs=[(999, 999)]), menu.id, action.id))

    def test_unavailable_authority_fails_closed(self):
        self.assertIsNone(menu_publication_decision({}, 182, 291))
        with patch.object(runtime_route_authority, "build_runtime_route_authority", return_value={}):
            self.assertIsNone(_published_menu_decision(self.env, 182, 291))

    def test_gate_consumes_declared_authority(self):
        authority = _authority(pairs=[(182, 291)])
        with patch.object(runtime_route_authority, "build_runtime_route_authority", return_value=authority):
            self.assertIs(_published_menu_decision(self.env, 182, 291), True)
        with patch.object(runtime_route_authority, "build_runtime_route_authority", return_value=_authority()):
            self.assertIs(_published_menu_decision(self.env, 182, 291), False)
