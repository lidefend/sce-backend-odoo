from __future__ import annotations

import unittest
import json
from pathlib import Path

from scripts.verify.frontend_release_navigation_policy_guard import ROLE_MAP, validate, validate_formal_targets, validate_runtime_targets


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

    def test_finance_historical_payment_entry_is_released_exactly_once(self):
        manifest, policies = _fixture()
        historical_menu = "smart_construction_core.menu_sc_historical_payment_fact"
        manifest["roles"]["finance"] = {
            "expected_count": 2,
            "leaf_keys": [
                "x.menu_finance|x.action_finance|x.model",
                f"{historical_menu}|smart_construction_core.action_sc_historical_payment_fact|sc.historical.payment.fact",
            ],
            "browser_expected_count": 1,
            "browser_leaf_keys": ["x.menu_finance|x.action_finance|x.model"],
        }
        policies["finance"]["primary_menu_xmlids"].append(historical_menu)
        self.assertEqual(validate(manifest, policies), [])

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



class RuntimeTargetDeclarationTest(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[2]
        self.source = (root / 'scripts/verify/frontend_delivery_hardening_runtime_ids.py').read_text()
        policy = json.loads((root / 'addons/smart_construction_core/data/formal_business_product_menu_policy_v1.json').read_text())
        self.standard = next(p for p in policy['products'] if p['product_key'] == 'construction.standard')
        self.assertEqual(validate_runtime_targets(self.source, self.standard), [])

    def test_real_resolver_is_published(self):
        self.assertEqual(validate_runtime_targets(self.source, self.standard), [])

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
