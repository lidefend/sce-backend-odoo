# -*- coding: utf-8 -*-
import importlib.util
import json
from pathlib import Path

from odoo.tests.common import TransactionCase

from odoo.addons.smart_construction_core.models.support.formal_entry_metadata_extensions import (
    active_unresolved_model_errors,
)


MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "17.0.0.82"
    / "post-migration.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("smart_construction_core_17_0_0_82_post", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestOrphanHandoffUiMigration(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.migration = _load_migration()

    def _xmlid(self, record, name):
        return self.env["ir.model.data"].create(
            {
                "module": "external_customer_legacy_handoff",
                "name": name,
                "model": record._name,
                "res_id": record.id,
                "noupdate": True,
            }
        )

    def _action_with_runtime_missing_model(self, name, model_name):
        action = self.env["ir.actions.act_window"].create(
            {"name": name, "res_model": "res.partner", "view_mode": "tree,form"}
        )
        self.env.cr.execute("UPDATE ir_act_window SET res_model = %s WHERE id = %s", [model_name, action.id])
        action.invalidate_recordset(["res_model"])
        return action

    def _relation_counts(self):
        return {
            relation: self.migration._table_count(self.env.cr, relation)
            for relation in self.migration.SUMMARY_VIEWS + self.migration.FACT_TABLES
        }

    def _ensure_counted_relations(self):
        for relation in self.migration.SUMMARY_VIEWS + self.migration.FACT_TABLES:
            self.env.cr.execute("SELECT to_regclass(%s)", [relation])
            if not self.env.cr.fetchone()[0]:
                self.env.cr.execute('CREATE TABLE "{}" (id integer)'.format(relation))
                self.env.cr.execute('INSERT INTO "{}" (id) VALUES (1), (2)'.format(relation))

    def test_only_target_ui_is_removed_and_data_relations_are_unchanged(self):
        self._ensure_counted_relations()
        target_actions = self.env["ir.actions.act_window"]
        target_views = self.env["ir.ui.view"]
        target_menus = self.env["ir.ui.menu"]
        for index, model_name in enumerate(self.migration.ORPHAN_MODELS):
            action = self._action_with_runtime_missing_model("orphan-%s" % index, model_name)
            view = self.env["ir.ui.view"].create(
                {"name": "orphan-view-%s" % index, "model": "res.partner", "type": "tree", "arch_db": "<tree/>"}
            )
            self.env.cr.execute("UPDATE ir_ui_view SET model = %s WHERE id = %s", [model_name, view.id])
            view.invalidate_recordset(["model"])
            menu = self.env["ir.ui.menu"].create(
                {"name": "orphan-menu-%s" % index, "action": "ir.actions.act_window,%s" % action.id}
            )
            self._xmlid(action, "target_action_%s" % index)
            self._xmlid(view, "target_view_%s" % index)
            self._xmlid(menu, "target_menu_%s" % index)
            target_actions |= action
            target_views |= view
            target_menus |= menu

        survivor = self.env["ir.actions.act_window"].create(
            {"name": "handoff-survivor", "res_model": "res.partner", "view_mode": "tree,form"}
        )
        survivor_xmlid = self._xmlid(survivor, "survivor_action")
        before = self._relation_counts()

        self.migration.migrate(self.env.cr, "17.0.0.81")

        self.assertFalse(target_actions.exists())
        self.assertFalse(target_views.exists())
        self.assertFalse(target_menus.exists())
        self.assertTrue(survivor.exists())
        self.assertTrue(survivor_xmlid.exists())
        self.assertEqual(before, self._relation_counts())
        snapshot_text = self.env["ir.config_parameter"].sudo().get_param(self.migration.SNAPSHOT_KEY)
        snapshot = json.loads(snapshot_text)
        self.assertEqual(set(snapshot["orphan_models"]), set(self.migration.ORPHAN_MODELS))
        self.assertEqual(snapshot["summary_view_counts"], {name: before[name] for name in self.migration.SUMMARY_VIEWS})
        self.assertEqual(snapshot["fact_table_counts"], {name: before[name] for name in self.migration.FACT_TABLES})
        self.assertEqual(len(snapshot["menus"]), 3)
        self.assertEqual(len(snapshot["actions"]), 3)
        self.assertEqual(len(snapshot["views"]), 3)

        self.migration.migrate(self.env.cr, "17.0.0.82")
        self.assertEqual(snapshot_text, self.env["ir.config_parameter"].sudo().get_param(self.migration.SNAPSHOT_KEY))
        self.assertTrue(survivor.exists())
        self.assertTrue(survivor_xmlid.exists())
        self.assertEqual(before, self._relation_counts())

    def test_missing_relations_are_safe(self):
        self.assertIsNone(self.migration._table_count(self.env.cr, "sc_absent_handoff_fixture"))

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
