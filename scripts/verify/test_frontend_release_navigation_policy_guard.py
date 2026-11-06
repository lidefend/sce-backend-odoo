from __future__ import annotations

import unittest
import json
from pathlib import Path

from scripts.verify.frontend_release_navigation_policy_guard import (
    ROLE_MAP,
    _load_role_policy,
    compare_role_projection,
    validate,
    validate_formal_targets,
    validate_runtime_targets,
)


def _fixture():
    roles = {}
    policies = {}
    for manifest_role, policy_role in ROLE_MAP.items():
        key = f"x.menu_{policy_role}|x.action_{policy_role}|x.model"
        roles[manifest_role] = {
            "expected_count": 1,
            "leaf_keys": [key],
            "browser_expected_count": 1,
            "browser_leaf_keys": [key],
        }
        policies[policy_role] = {
            "primary_menu_xmlids": [f"x.menu_{policy_role}"],
            "role_home_menu_xmlids": [],
            "contextual_menu_xmlids": [],
            "denied_menu_xmlids": [],
        }
    return {"roles": roles}, policies


class ReleaseNavigationPolicyGuardTest(unittest.TestCase):
    def test_exact_release_projection_passes(self):
        manifest, policies = _fixture()
        self.assertEqual(validate(manifest, policies), [])

    def test_missing_release_leaf_fails_closed(self):
        manifest, policies = _fixture()
        policies["finance"]["primary_menu_xmlids"] = []
        self.assertTrue(any("finance: release projection differs" in row for row in validate(manifest, policies)))

    def test_repository_projection_matches_current_role_authority(self):
        root = Path(__file__).resolve().parents[2]
        manifest = json.loads((root / "config/frontend/authoritative_navigation.json").read_text())
        policies = _load_role_policy()
        self.assertEqual(validate(manifest, policies), [])

        # A capability-discover role must not reintroduce a static primary whitelist.
        policies["finance"]["primary_menu_xmlids"] = [
            "smart_construction_core.menu_sc_historical_payment_fact"
        ]
        self.assertTrue(any("finance: capability-discover role declares stale" in row
                            for row in validate(manifest, policies)))

    def test_capability_discover_role_rejects_stale_primary_whitelist(self):
        manifest, policies = _fixture()
        policies["finance"]["discover_installed_capabilities"] = True
        policies["finance"]["role_home_menu_xmlids"] = ["x.menu_finance"]
        policies["finance"]["primary_menu_xmlids"] = ["x.stale_leaf"]
        errors = validate(manifest, policies)
        self.assertTrue(any("finance: capability-discover role declares stale" in row
                            for row in errors))

    def test_contextual_or_denied_overlap_fails_closed(self):
        manifest, policies = _fixture()
        policies["owner"]["contextual_menu_xmlids"] = ["x.menu_owner"]
        policies["pm"]["denied_menu_xmlids"] = ["x.menu_pm"]
        errors = validate(manifest, policies)
        self.assertTrue(any("owner: released/contextual overlap" in row for row in errors))
        self.assertTrue(any("pm: released/denied overlap" in row for row in errors))

    def test_formal_daily_contract_identity_replaces_legacy_construction_contract(self):
        manifest, policies = _fixture()
        formal_menu = "smart_construction_core.menu_sc_p1_daily_contract"
        legacy_menu = "smart_construction_core.menu_sc_construction_contract"
        manifest["roles"]["pm"] = {
            "expected_count": 1,
            "leaf_keys": [
                f"{formal_menu}|smart_construction_core.action_sc_general_contract|sc.general.contract"
            ],
            "browser_expected_count": 1,
            "browser_leaf_keys": [
                f"{formal_menu}|smart_construction_core.action_sc_general_contract|sc.general.contract"
            ],
        }
        policies["pm"]["primary_menu_xmlids"] = [formal_menu]
        self.assertEqual(validate(manifest, policies), [])

        policies["pm"]["primary_menu_xmlids"] = [legacy_menu]
        errors = validate(manifest, policies)
        self.assertTrue(any(formal_menu in row and legacy_menu in row for row in errors))

    def test_formal_targets_reject_retired_identity_even_when_role_and_manifest_agree(self):
        manifest, _ = _fixture()
        self.assertTrue(validate_formal_targets(manifest, {"menu_groups": []}, {}))

    def test_scene_route_must_match_product_and_backend_scene_map(self):
        menu = "x.home"
        target = {"menu_xmlid": menu, "action_xmlid": "", "model": "", "enabled": True,
                  "release_state": "released", "entry_target_policy": "scene_entry",
                  "scene_key": "workspace.home", "route": "/s/workspace.home"}
        product = {"menu_groups": [{"menus": [target]}]}
        manifest = {"roles": {"owner": {"browser_leaf_keys": [menu + "||"]}},
                    "scene_targets": {menu: {"scene_key": "workspace.home", "route": "/s/workspace.home"}}}
        self.assertEqual(validate_formal_targets(manifest, product, {menu: "workspace.home"}), [])
        self.assertTrue(validate_formal_targets(manifest, product, {menu: "other"}))
        manifest["scene_targets"][menu]["route"] = "/s/other"
        self.assertTrue(validate_formal_targets(manifest, product, {menu: "workspace.home"}))


class RoleProjectionComparatorTest(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[2]
        self.manifest = json.loads((root / "config/frontend/authoritative_navigation.json").read_text())

    def test_pm_equal_count_swap_is_visible_as_missing_and_unexpected(self):
        boq_identity = "smart_construction_core.menu_sc_boq_analysis|smart_construction_core.action_project_boq_analysis|project.boq.analysis"
        tender_identity = "smart_construction_core.menu_sc_project_tender|smart_construction_core.action_sc_project_tender|tender.bid"

        pm = self.manifest["roles"]["pm"]
        actual = list(pm["leaf_keys"])
        expected = [tender_identity if key == boq_identity else key for key in actual]
        self.assertEqual(len(expected), pm["expected_count"])
        self.assertEqual(len(pm["browser_leaf_keys"]), pm["browser_expected_count"])

        # Old guard: an equal-count swap of a non-browser leaf passes, because the
        # pm role is capability-discover and the offline guard never compares the
        # full leaf identities against an independent published set.
        swapped_manifest = json.loads(json.dumps(self.manifest))
        swapped_manifest["roles"]["pm"]["leaf_keys"] = expected
        self.assertEqual(validate(swapped_manifest, _load_role_policy()), [])

        result = compare_role_projection(expected, actual)
        self.assertTrue(any("menu_sc_project_tender" in key for key in result["missing"]))
        self.assertTrue(any("menu_sc_boq_analysis" in key for key in result["unexpected"]))
        self.assertFalse(result["consistent"])

    def test_finance_synchronized_shrink_still_fails(self):
        finance = self.manifest["roles"]["finance"]
        actual = list(finance["leaf_keys"])
        home = "smart_construction_core.menu_sc_workspace_home||"
        shrunk_manifest = json.loads(json.dumps(self.manifest))
        shrunk_manifest["roles"]["finance"] = {
            "expected_count": 1,
            "leaf_keys": [home],
            "browser_expected_count": 1,
            "browser_leaf_keys": [home],
        }
        self.assertEqual(validate(shrunk_manifest, _load_role_policy()), [])

        result = compare_role_projection([home], actual)
        self.assertTrue(result["unexpected"])
        self.assertFalse(result["consistent"])
        self.assertGreater(result["actual_count"], result["expected_count"])


class RuntimeTargetDeclarationTest(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[2]
        self.source = (root / 'scripts/verify/frontend_delivery_hardening_runtime_ids.py').read_text()
        policy = json.loads((root / 'addons/smart_construction_core/data/formal_business_product_menu_policy_v1.json').read_text())
        self.standard = next(p for p in policy['products'] if p['product_key'] == 'construction.standard')
        self.assertEqual(validate_runtime_targets(self.source, self.standard), [])

    def test_real_resolver_is_published(self):
        self.assertEqual(validate_runtime_targets(self.source, self.standard), [])

    def test_professional_wrapper_target_must_be_published(self):
        source = self.source.replace('menu_sc_p1_income_contract', 'menu_sc_project_contract_overview')
        self.assertTrue(any('not formally released' in error
                            for error in validate_runtime_targets(source, self.standard)))

    def test_professional_wrapper_action_must_match(self):
        source = self.source.replace('action_construction_contract_income', 'action_construction_contract_expense')
        self.assertTrue(any('runtime action differs' in error
                            for error in validate_runtime_targets(source, self.standard)))

    def test_retired_settlement_entry_fails(self):
        source = self.source.replace('menu_sc_p1_expense_settlement', 'menu_sc_expense_contract_settlement')
        self.assertTrue(validate_runtime_targets(source, self.standard))

    def test_mismatched_action_fails(self):
        source = self.source.replace('action_sc_settlement_order_expense', 'action_sc_settlement_order_income')
        self.assertTrue(validate_runtime_targets(source, self.standard))

    def test_missing_action_argument_fails(self):
        source = self.source.replace('declared_action_xmlid=SETTLEMENT_ACTION_XMLID,', '')
        self.assertTrue(validate_runtime_targets(source, self.standard))

    def test_disabled_formal_entry_fails(self):
        for group in self.standard['menu_groups']:
            for row in group.get('menus', []):
                if row.get('menu_xmlid', '').endswith('.menu_sc_p1_expense_settlement'):
                    row['enabled'] = False
        self.assertTrue(validate_runtime_targets(self.source, self.standard))

    def test_empty_or_dynamic_target_fails(self):
        self.assertTrue(validate_runtime_targets('', self.standard))
        self.assertTrue(validate_runtime_targets('target(resolve_menu(), x)', self.standard))


if __name__ == "__main__":
    unittest.main()
