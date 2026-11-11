"""PR810 maintenance regressions on real ORM and the system.init handler.

Run only in the governed acceptance fixture lane. Every edit rolls back with
TransactionCase; no cache/mock replaces the navigation delivery or projection.
"""
import runpy
import json
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
        # The test establishes the maintained policy for the current source.
        # An earlier release snapshot is a historical immutable artifact and
        # must not silently replace that candidate inside this rollback-only
        # runtime contract test.
        self.env["sc.edition.release.snapshot"].sudo().search([
            ("product_key", "in", ["construction.standard", "construction.preview"]),
            ("is_active", "=", True),
        ]).write({"is_active": False})

    def _upgrade_seed(self):
        convert_file(self.env, "smart_construction_core", "data/product_scenario_seed.xml", {},
                     mode="update", noupdate=False)

    def _binding(self, menu):
        row = self.Entry.search([("menu_id", "=", menu.id)])
        self.assertEqual(len(row), 1)
        return row

    def _navigation(self):
        return self._system_init(self.actor)

    def _system_init(self, actor):
        actor_env = self.env(user=actor.id, context=dict(
            self.env.context, lang="zh_CN", allowed_company_ids=[actor.company_id.id]))
        result = SystemInitHandler(env=actor_env).handle({"params": {
            "scene": "web", "with_preload": False, "scene_ready_mode": "registry",
        }})
        self.assertTrue(result.ok)
        self.role_surface = result.data.get("role_surface") or {}
        from odoo.addons.smart_construction_core.services.scenario_surface_projection import flatten_authorized_nav_leaves
        navigation = result.data["navigation"]
        self.product_policy_projection = navigation["product_policy"]
        leaves = flatten_authorized_nav_leaves(navigation["nav"], navigation["route_authority"])
        self.authorized_ids = {row["menu_id"] for row in leaves}
        self.account_leaves = [row for row in leaves if str(row.get("menu_xmlid", "")).startswith("account.")]
        surface = navigation["scenario_surface"]
        self.assertTrue(surface["ok"])
        return navigation, surface["tree"]["centers"]

    def _navigation_surface(self):
        return self._navigation()[1]

    def _route_state(self, navigation, menu):
        pair = (menu.id, menu.action.id)
        from odoo.addons.smart_construction_core.services.scenario_surface_projection import flatten_authorized_nav_leaves
        leaves = flatten_authorized_nav_leaves(navigation["nav"], navigation["route_authority"])
        nav_pairs = {(row["menu_id"], row["action_id"]) for row in leaves}
        authority = navigation["route_authority"]
        buckets = {}
        for bucket in ("primary_actions", "role_home_actions", "contextual_actions", "admin_actions"):
            rows = [
                row for row in authority.get(bucket) or []
                if (row.get("menu_id"), row.get("action_id")) == pair
            ]
            if rows:
                buckets[bucket] = rows
        denied = [
            row for row in authority.get("denied_actions") or []
            if (row.get("menu_id"), row.get("action_id")) == pair
        ]
        return pair, nav_pairs, buckets, denied

    def _product_policy_entries(self):
        return {
            (row.get("menu_id"), row.get("action_id")): row
            for row in self.product_policy_projection.get("entries") or []
        }

    def _entry_diagnostic(self, actor, menu, pair, nav_pairs, buckets, denied):
        policy_rows = []
        for policy in self.env["sc.product.policy"].sudo().search(
            [("product_key", "in", ["construction.standard", "construction.preview"])]
        ):
            for group in policy.menu_groups or []:
                for row in group.get("menus") or []:
                    if row.get("menu_xmlid") == menu.get_external_id().get(menu.id):
                        policy_rows.append({
                            "product_key": policy.product_key,
                            "group": group.get("group_key"),
                            "menu_id": row.get("menu_id"),
                            "action_id": row.get("action_id"),
                            "action_xmlid": row.get("action_xmlid"),
                            "route": row.get("route"),
                        })
        snapshots = []
        for snapshot in self.env["sc.edition.release.snapshot"].sudo().search(
            [("is_active", "=", True)], order="released_at desc, id desc"
        ):
            payload = snapshot.snapshot_json if isinstance(snapshot.snapshot_json, dict) else {}
            policy = payload.get("policy") if isinstance(payload.get("policy"), dict) else {}
            snapshot_pairs = {
                (row.get("menu_id"), row.get("action_id"))
                for group in policy.get("menu_groups") or []
                for row in group.get("menus") or []
            }
            snapshots.append({
                "id": snapshot.id,
                "product_key": snapshot.product_key,
                "state": snapshot.state,
                "has_pair": pair in snapshot_pairs,
                "schema": payload.get("policy_snapshot_schema"),
            })
        return json.dumps({
            "pair": pair,
            "nav_pairs": sorted(nav_pairs),
            "buckets": buckets,
            "denied": denied,
            "policy_rows": policy_rows,
            "release_snapshots": snapshots,
            "role_surface": {
                "role_code": self.role_surface.get("role_code"),
                "role_codes": self.role_surface.get("role_codes"),
                "discover_installed_capabilities": self.role_surface.get("discover_installed_capabilities"),
                "exposure_policy_declared": self.role_surface.get("exposure_policy_declared"),
                "role_home_menu_xmlids": self.role_surface.get("role_home_menu_xmlids"),
            },
            "menu": {
                "id": menu.id,
                "action_id": menu.action.id,
                "groups": [group.get_external_id().get(group.id) for group in menu.groups_id],
            },
        }, ensure_ascii=False, sort_keys=True)

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
        before = self._locations(self._navigation_surface())
        self.assertIn(self.project_menu.id, set(before))
        self.project_menu.parent_id = self.contract_center
        after = self._locations(self._navigation_surface())
        self.assertEqual(set(after), set(before), "placement must not change authorization")
        center = after[self.project_menu.id][0]
        self.assertEqual(center["key"], "smart_construction_core.menu_sc_contract_center")

    def test_system_init_external_center_rename_and_binding_deletion(self):
        self.actor = self.env.ref("smart_construction_acceptance_fixture.fe_user_activity_accounting")
        self.assertEqual(self.account_menu.sc_product_center_id, self.account_center)
        before = self._locations(self._navigation_surface())
        self.assertIn(self.account_menu.id, self.authorized_ids, str(self.account_leaves))
        self.assertIn(self.account_menu.id, set(before))
        self.assertEqual(self.account_menu.sc_product_center_id, self.account_center)
        self.account_center.with_context(lang="zh_CN").name = "Maintained accounting center"
        self._binding(self.account_menu).unlink()
        self._upgrade_seed()
        after = self._locations(self._navigation_surface())
        self.assertIn(self.account_menu.id, after)
        self.assertIn(self.account_menu.id, self.authorized_ids)
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
        locations = self._locations(self._navigation_surface())
        entries = locations[self.account_menu.id][1]["entries"]
        ids = [entry["menu_id"] for entry in entries]
        self.assertLess(ids.index(menu2.id), ids.index(self.account_menu.id))
        self.assertEqual(locations[menu2.id][2]["sequence"], 0)
        (first | second).unlink()
        (self.account_menu | menu2).write({"sc_scenario_exempt": True})
        self.account_menu.sequence, menu2.sequence = 90, 0
        entries = self._locations(self._navigation_surface())[self.account_menu.id][0]["entries"]
        ids = [entry["menu_id"] for entry in entries]
        self.assertLess(ids.index(menu2.id), ids.index(self.account_menu.id))

    def test_external_association_edits_survive_seed_reload(self):
        self.account_menu.sc_product_center_id = self.contract_center
        self._upgrade_seed()
        self.assertEqual(self.account_menu.sc_product_center_id, self.contract_center)
        self.account_menu.sc_product_center_id = False
        self._upgrade_seed()
        self.assertFalse(self.account_menu.sc_product_center_id)

    def test_system_init_config_admin_receives_independent_entries(self):
        navigation, _centers = self._navigation()
        actor_env = self.env(
            user=self.actor.id,
            context=dict(
                self.env.context,
                allowed_company_ids=[self.actor.company_id.id],
            ),
        )
        for xmlid, expected_route in (
            ("smart_construction_core.menu_sc_my_work", "/s/my_work.workspace"),
            (
                "smart_construction_core.menu_sc_enterprise_initialization",
                "/s/enterprise.setup",
            ),
        ):
            menu = self.env.ref(xmlid)
            pair, nav_pairs, buckets, denied = self._route_state(navigation, menu)
            diagnostic = self._entry_diagnostic(
                actor_env, menu, pair, nav_pairs, buckets, denied
            )
            with self.subTest(xmlid=xmlid):
                self.assertIn(menu.id, actor_env["ir.ui.menu"]._visible_menu_ids())
                self.assertIn(pair, nav_pairs, diagnostic)
                self.assertTrue(buckets, "%s missing from allowed route buckets: %s" % (xmlid, diagnostic))
                self.assertFalse(denied, "%s unexpectedly denied: %s" % (xmlid, denied))
                self.assertTrue(all(
                    row.get("route_kind") != "DENIED"
                    and row.get("reason_code") != "BUSINESS_SCENARIO_CONFIGURATION_MISSING"
                    and row.get("route") == expected_route
                    and (row.get("entry_target") or {}).get("route") == expected_route
                    for rows in buckets.values()
                    for row in rows
                ))
        my_work = self.env.ref("smart_construction_core.menu_sc_my_work")
        enterprise = self.env.ref(
            "smart_construction_core.menu_sc_enterprise_initialization"
        )
        _pair, _nav_pairs, buckets, _denied = self._route_state(navigation, enterprise)
        self.assertTrue(buckets, diagnostic)
        policy_entries = self._product_policy_entries()
        self.assertEqual(
            policy_entries[(my_work.id, my_work.action.id)]["route"],
            "/s/my_work.workspace",
        )
        self.assertEqual(
            policy_entries[(enterprise.id, enterprise.action.id)]["route"],
            "/s/enterprise.setup",
        )

    def test_system_init_business_full_gets_my_work_but_not_configuration_entry(self):
        full_group = self.env.ref("smart_construction_core.group_sc_business_full")
        user = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Business full runtime principal",
            "login": "business.full.runtime.principal",
            "company_id": self.actor.company_id.id,
            "company_ids": [(6, 0, [self.actor.company_id.id])],
            "groups_id": [(6, 0, [
                self.env.ref("base.group_user").id,
                full_group.id,
            ])],
        })
        self.assertFalse(
            user.has_group("smart_construction_core.group_sc_cap_business_config_admin")
        )
        navigation, _centers = self._system_init(user)
        my_work = self.env.ref("smart_construction_core.menu_sc_my_work")
        pair, nav_pairs, buckets, denied = self._route_state(navigation, my_work)
        diagnostic = self._entry_diagnostic(
            user.env, my_work, pair, nav_pairs, buckets, denied
        )
        self.assertIn(pair, nav_pairs, diagnostic)
        self.assertTrue(buckets, diagnostic)
        self.assertTrue(all(
            row.get("route") == "/s/my_work.workspace"
            for rows in buckets.values()
            for row in rows
        ))
        self.assertFalse(denied)
        policy_entries = self._product_policy_entries()
        self.assertEqual(
            policy_entries[(my_work.id, my_work.action.id)]["route"],
            "/s/my_work.workspace",
        )
        enterprise = self.env.ref(
            "smart_construction_core.menu_sc_enterprise_initialization"
        )
        _pair, nav_pairs, buckets, _denied = self._route_state(navigation, enterprise)
        self.assertNotIn(enterprise.id, self.authorized_ids)
        self.assertNotIn(
            enterprise.id,
            user.with_user(user).env["ir.ui.menu"]._visible_menu_ids(),
        )
        self.assertFalse(buckets)
        self.assertNotIn(
            (enterprise.id, enterprise.action.id),
            self._product_policy_entries(),
        )
