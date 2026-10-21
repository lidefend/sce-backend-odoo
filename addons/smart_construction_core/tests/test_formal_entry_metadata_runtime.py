# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.addons.smart_construction_core.models.support.formal_entry_metadata_extensions import (
    active_unresolved_model_errors,
)


class TestFormalEntryMetadataRuntime(TransactionCase):
    def _action_with_runtime_missing_model(self, name, model_name):
        action = self.env["ir.actions.act_window"].create(
            {"name": name, "res_model": "res.partner", "view_mode": "tree,form"}
        )
        self.env.cr.execute("UPDATE ir_act_window SET res_model = %s WHERE id = %s", [model_name, action.id])
        action.invalidate_recordset(["res_model"])
        return action

    def test_active_unresolved_menu_fails_closed_and_inactive_menu_does_not(self):
        action = self._action_with_runtime_missing_model(
            "unresolved-negative-fixture", "sc.unregistered.negative.fixture"
        )
        menu = self.env["ir.ui.menu"].create(
            {"name": "unresolved-negative-fixture", "action": "ir.actions.act_window,%s" % action.id, "active": True}
        )
        failures = active_unresolved_model_errors(self.env, ("sc.",), ("sc.legacy.",))
        self.assertEqual([row for row in failures if row["menu_id"] == menu.id][0]["error"], "active_unresolved_model")
        menu.active = False
        failures = active_unresolved_model_errors(self.env, ("sc.",), ("sc.legacy.",))
        self.assertFalse([row for row in failures if row["menu_id"] == menu.id])
