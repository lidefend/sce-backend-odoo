"""PR810 maintenance regressions on real ORM and the system.init handler.

Run only in the governed acceptance fixture lane. Every edit rolls back with
TransactionCase; no cache/mock replaces the navigation delivery or projection.
"""
import runpy
from pathlib import Path

from odoo.tests.common import TransactionCase, tagged
from odoo.tools.convert import convert_file
from odoo.addons.smart_construction_core.models.support import product_scenario
from odoo.addons.smart_core.handlers.system_init import SystemInitHandler


@tagged("post_install", "-at_install", "acceptance_business_scene_lifecycle",
        "acceptance_scenario_navigation_maintenance")
class TestScenarioNavigationMaintenance(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Scenario = self.env["sc.product.scenario"].sudo().with_context(active_test=False)
        self.Entry = self.env["sc.product.scenario.entry"].sudo()
        self.Param = self.env["ir.config_parameter"].sudo()
        self.actor = self.env.ref("smart_construction_acceptance_fixture.fe_user_config_admin")
        self.project_menu = self.env.ref("smart_construction_core.menu_sc_project_project")
        self.contract_center = self.env.ref("smart_construction_core.menu_sc_contract_center")
        self.account_menu = self.env.ref("account.menu_action_move_journal_line_form")
        self.account_center = self.env.ref("smart_construction_core.menu_sc_accounting_center")
        # Establish the released policy fixture inside this rollback-only test.
        # The candidate currently carries empty maintained policy records.
        policy = self.env["sc.product.policy"].sudo()
        policy.search([("product_key", "in", ["construction.standard", "construction.preview"])]).unlink()
        policy.sync_construction_menu_product_policies()

    def _upgrade_seed(self):
        convert_file(self.env, "smart_construction_core", "data/product_scenario_seed.xml", {},
                     mode="update", noupdate=False)

    def _binding(self, menu):
        row = self.Entry.search([("menu_id", "=", menu.id)])
        self.assertEqual(len(row), 1)
        return row

    def _navigation(self):
        actor_env = self.env(user=self.actor.id, context=dict(
            self.env.context, lang="zh_CN", allowed_company_ids=[self.actor.company_id.id]))
        result = SystemInitHandler(env=actor_env).handle({"params": {
            "scene": "web", "with_preload": False, "scene_ready_mode": "registry",
        }})
        self.assertTrue(result.ok)
        from odoo.addons.smart_construction_core.services.scenario_surface_projection import flatten_authorized_nav_leaves
        navigation = result.data["navigation"]
        leaves = flatten_authorized_nav_leaves(navigation["nav"], navigation["route_authority"])
        self.authorized_ids = {row["menu_id"] for row in leaves}
        self.account_leaves = [row for row in leaves if str(row.get("menu_xmlid", "")).startswith("account.")]
        surface = navigation["scenario_surface"]
        self.assertTrue(surface["ok"])
        return surface["tree"]["centers"]

    def _locations(self, centers):
        return {entry["menu_id"]: (center, scenario, entry)
                for center in centers
                for scenario in [*center["scenarios"], {"key": "", "entries": center["entries"]}]
                for entry in scenario["entries"]}

    def test_deleted_binding_stays_deleted_on_upgrade(self):
        self._binding(self.project_menu).unlink()
        self._upgrade_seed()
        self.assertFalse(self.Entry.search([("menu_id", "=", self.project_menu.id)]))

    def test_rebound_entry_keeps_scenario_and_sequence_on_upgrade(self):
        entry = self._binding(self.project_menu)
        replacement = self.Scenario.create({"code": "test.review810", "name": "Maintained scenario"})
        entry.write({"scenario_id": replacement.id, "sequence": 0})
        self._upgrade_seed()
        self.assertEqual(self._binding(self.project_menu), entry)
        self.assertEqual(entry.scenario_id, replacement)
        self.assertEqual(entry.sequence, 0)

    def test_archived_scenario_and_empty_configuration_survive_upgrade(self):
        scenario = self._binding(self.project_menu).scenario_id
        scenario.active = False
        self._upgrade_seed()
        self.assertFalse(scenario.active)
        self.assertEqual(self.Scenario.search_count([("code", "=", scenario.code)]), 1)
        self.Scenario.search([]).unlink()
        self._upgrade_seed()
        self.assertFalse(self.Scenario.search([]))

    def test_legacy_migration_adopts_deletions_before_seed_reload(self):
        self._binding(self.project_menu).unlink()
        self.Param.set_param(product_scenario.SCENARIO_SEED_KEY, False)
        migration = Path(product_scenario.__file__).parents[2] / "migrations/17.0.0.174/pre-migrate.py"
        runpy.run_path(str(migration))["migrate"](self.cr, "17.0.0.173")
        self.env.registry.clear_cache()
        self._upgrade_seed()
        self.assertFalse(self.Entry.search([("menu_id", "=", self.project_menu.id)]))

    def test_first_initialization_and_missing_marker_keep_archived_rebound_rows(self):
        self.Scenario.search([]).unlink()
        self.Param.set_param(product_scenario.SCENARIO_SEED_KEY, False)
        self._upgrade_seed()
        self.assertTrue(self.Param.get_param(product_scenario.SCENARIO_SEED_KEY))
        entry = self._binding(self.project_menu)
        archived = entry.scenario_id
        archived.active = False
        replacement = self.Scenario.create({"code": "test.rebound", "name": "Rebound"})
        entry.scenario_id = replacement
        self.Param.set_param(product_scenario.SCENARIO_SEED_KEY, False)
        self._upgrade_seed()
        self.assertEqual(self._binding(self.project_menu).scenario_id, replacement)
        self.assertFalse(archived.active)

    def test_system_init_uses_moved_native_parent_despite_old_policy(self):
        before = self._locations(self._navigation())
        self.assertIn(self.project_menu.id, set(before))
        self.project_menu.parent_id = self.contract_center
        after = self._locations(self._navigation())
        self.assertEqual(set(after), set(before), "placement must not change authorization")
        center = after[self.project_menu.id][0]
        self.assertEqual(center["key"], "smart_construction_core.menu_sc_contract_center")

    def test_system_init_external_center_rename_and_binding_deletion(self):
        self.actor = self.env.ref("smart_construction_acceptance_fixture.fe_user_activity_accounting")
        self.assertEqual(self.account_menu.sc_product_center_id, self.account_center)
        before = self._locations(self._navigation())
        self.assertIn(self.account_menu.id, self.authorized_ids, str(self.account_leaves))
        self.assertIn(self.account_menu.id, set(before))
        self.assertEqual(self.account_menu.sc_product_center_id, self.account_center)
        self.account_center.with_context(lang="zh_CN").name = "Maintained accounting center"
        self._binding(self.account_menu).unlink()
        self._upgrade_seed()
        after = self._locations(self._navigation())
        self.assertNotIn(self.account_menu.id, after)
        self.assertNotIn(self.account_menu.id, self.authorized_ids)
        self.account_menu.sc_scenario_exempt = True
        after = self._locations(self._navigation())
        self.assertEqual(set(after), set(before))
        center, scenario, entry = after[self.account_menu.id]
        self.assertEqual(center["key"], "smart_construction_core.menu_sc_accounting_center")
        self.assertEqual(center["name"], "Maintained accounting center")
        self.assertFalse(scenario["key"])
        self.assertFalse(entry["configured"])

    def test_system_init_consumes_entry_and_direct_sequence(self):
        self.actor = self.env.ref("smart_construction_acceptance_fixture.fe_user_activity_accounting")
        self.assertEqual(self.account_menu.sc_product_center_id, self.account_center)
        menu2 = self.env.ref("account.menu_action_account_moves_all")
        first, second = self._binding(self.account_menu), self._binding(menu2)
        second.scenario_id = first.scenario_id
        first.sequence, second.sequence = 90, 0
        locations = self._locations(self._navigation())
        entries = locations[self.account_menu.id][1]["entries"]
        ids = [entry["menu_id"] for entry in entries]
        self.assertLess(ids.index(menu2.id), ids.index(self.account_menu.id))
        self.assertEqual(locations[menu2.id][2]["sequence"], 0)
        (first | second).unlink()
        (self.account_menu | menu2).write({"sc_scenario_exempt": True})
        self.account_menu.sequence, menu2.sequence = 90, 0
        entries = self._locations(self._navigation())[self.account_menu.id][0]["entries"]
        ids = [entry["menu_id"] for entry in entries]
        self.assertLess(ids.index(menu2.id), ids.index(self.account_menu.id))

    def test_external_association_edits_survive_seed_reload(self):
        self.account_menu.sc_product_center_id = self.contract_center
        self._upgrade_seed()
        self.assertEqual(self.account_menu.sc_product_center_id, self.contract_center)
        self.account_menu.sc_product_center_id = False
        self._upgrade_seed()
        self.assertFalse(self.account_menu.sc_product_center_id)
