# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_core.security.intent_permission import _menu_visible_for_user


@tagged("post_install", "-at_install", "smart_core", "intent_permission_menu_visibility")
class TestIntentPermissionMenuVisibility(TransactionCase):
    """The intent menu gate must mirror the runtime navigation interpretation.

    A parent menu configured with a stricter group must never hide a child menu
    the user can actually see (``docs/product/formal_product_boundary_v1.md`` and
    ``docs/security/SC_Permission_Blueprint.md``). The previous ancestor walk
    denied such children (e.g. 会计科目表 under 会计 for read-only finance users).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Menu = cls.env["ir.ui.menu"]
        cls.group_held = cls.env["res.groups"].create({"name": "T Menu Held"})
        cls.group_missing = cls.env["res.groups"].create({"name": "T Menu Missing"})
        # Deterministic read authority for the action model so the canonical
        # visibility rule (own group + action model read) is what is exercised.
        cls.env["ir.model.access"].create(
            {
                "name": "T Menu Held res.partner read",
                "model_id": cls.env.ref("base.model_res_partner").id,
                "group_id": cls.group_held.id,
                "perm_read": True,
            }
        )
        cls.user = cls.env["res.users"].create(
            {
                "name": "T Menu User",
                "login": "t_intent_menu_visibility",
                "groups_id": [
                    (6, 0, [cls.env.ref("base.group_user").id, cls.group_held.id])
                ],
            }
        )

    def _action(self, name):
        return self.env["ir.actions.act_window"].create(
            {"name": name, "res_model": "res.partner", "view_mode": "tree,form"}
        )

    def _menu(self, name, *, groups=None, parent=None):
        vals = {"name": name, "action": f"ir.actions.act_window,{self._action(name).id}"}
        if groups is not None:
            vals["groups_id"] = [(6, 0, [groups.id])]
        if parent is not None:
            vals["parent_id"] = parent.id
        return self.Menu.create(vals)

    def test_child_visible_when_parent_group_missing(self):
        parent = self.Menu.create(
            {"name": "T Parent 会计", "groups_id": [(6, 0, [self.group_missing.id])]}
        )
        child = self._menu("T Child 会计科目表", groups=self.group_held, parent=parent)
        self.assertTrue(_menu_visible_for_user(child, self.user))

    def test_menu_with_missing_group_is_invisible(self):
        menu = self._menu("T Denied", groups=self.group_missing)
        self.assertFalse(_menu_visible_for_user(menu, self.user))

    def test_menu_without_groups_is_visible(self):
        menu = self._menu("T Open")
        self.assertTrue(_menu_visible_for_user(menu, self.user))
