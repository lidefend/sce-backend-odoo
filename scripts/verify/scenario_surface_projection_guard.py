#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Static guard for the scenario product surface projection.

Pure Python (no Odoo). Loads the P1 scenario surface contract and the released
91 menu identities from product_menu_source, then proves the projection regroups
all 91 into domain -> scenario -> intent without re-authoring identity.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PMS = _load_module("product_menu_source", ROOT / "addons/smart_construction_core/services/product_menu_source.py")
PROJ = _load_module("scenario_surface_projection", ROOT / "addons/smart_construction_core/services/scenario_surface_projection.py")
SURFACE_PATH = ROOT / "addons/smart_construction_core/data/scenario_product_surface.json"


def released_menu_xmlids():
    src = PMS.load_source()
    _contract, pub = PMS.project(src)
    standard = next(p for p in pub["products"] if p.get("edition_key") == "standard")
    return [row["menu_xmlid"] for group in standard["menu_groups"] for row in group["menus"]]


def synthetic_leaves(menu_xmlids):
    leaves = []
    for index, xmlid in enumerate(menu_xmlids, start=1):
        leaves.append({
            "menu_xmlid": xmlid,
            "menu_id": index,
            "action_id": index,
            "action_xmlid": f"action.{index}",
            "model": "res.model",
            "view_modes": ["tree", "form"],
            "route": f"/a/{index}?menu_id={index}",
            "label": xmlid,
        })
    return leaves


def synthetic_nav(menu_xmlids):
    nodes = []
    for index, xmlid in enumerate(menu_xmlids, start=1):
        nodes.append({
            "xmlid": xmlid,
            "menu_xmlid": xmlid,
            "label": xmlid,
            "menu_id": index,
            "action_id": index,
            "model": "res.model",
            "view_modes": ["tree", "form"],
            "route": f"/a/{index}?menu_id={index}",
            "children": [],
            "canonical_navigation": {
                "schema_version": "1.0",
                "key": xmlid,
                "menu_id": index,
                "action_id": index,
                "label": xmlid,
                "route": f"/a/{index}?menu_id={index}",
                "state": "enabled",
            },
        })
    return nodes


def synthetic_route_authority(menu_xmlids):
    return {
        "principal_scope": {"user_id": 1},
        "primary_actions": [
            {
                "menu_id": index,
                "action_id": index,
                "menu_xmlid": xmlid,
                "action_xmlid": f"action.{index}",
                "model": "res.model",
                "view_modes": ["tree", "form"],
                "route": f"/a/{index}?menu_id={index}",
            }
            for index, xmlid in enumerate(menu_xmlids, start=1)
        ],
    }


class ScenarioSurfaceProjectionGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.surface = PROJ.load_surface(SURFACE_PATH)
        cls.released = released_menu_xmlids()
        cls.leaves = synthetic_leaves(cls.released)

    def test_released_universe_is_exactly_91(self):
        self.assertEqual(len(self.released), 91)

    def test_surface_maps_all_91_and_only_them(self):
        index = PROJ.build_menu_index(self.surface)
        self.assertEqual(set(index), set(self.released))

    def test_surface_declares_17_scenarios_under_6_domains(self):
        self.assertEqual(len(self.surface["scenarios"]), 17)
        self.assertEqual(len(self.surface["domains"]), 6)
        scenario_keys = {s["key"] for s in self.surface["scenarios"]}
        domain_keys = {k for d in self.surface["domains"] for k in d["scenarios"]}
        self.assertEqual(scenario_keys, domain_keys)

    def test_projection_groups_all_91_with_no_unmapped(self):
        result = PROJ.project_scenario_navigation(surface=self.surface, authorized_leaves=self.leaves)
        self.assertTrue(result["ok"])
        self.assertEqual(result["diagnostics"]["unmapped_count"], 0)
        self.assertEqual(result["diagnostics"]["grouped_menu_count"], 91)
        self.assertEqual(result["diagnostics"]["grouped_leaf_count"], 91)

    def test_projection_preserves_leaf_identity(self):
        result = PROJ.project_scenario_navigation(surface=self.surface, authorized_leaves=self.leaves, include_platform=True)
        domain_entries = [e for d in result["tree"]["domains"] for s in d["scenarios"] for i in s["intents"] for e in i["entries"]]
        horizontal = result["tree"]["horizontal"]
        platform = result["tree"]["platform"]
        self.assertEqual(len(domain_entries), 79)
        self.assertEqual(len(horizontal), 5)
        self.assertEqual(len(platform), 7)
        by_menu = {e["menu_xmlid"]: e for e in domain_entries + horizontal + platform}
        first = self.released[0]
        self.assertEqual(by_menu[first]["menu_xmlid"], first)
        self.assertEqual(by_menu[first]["route"], f"/a/1?menu_id=1")

    def test_empty_intents_are_omitted(self):
        result = PROJ.project_scenario_navigation(surface=self.surface, authorized_leaves=self.leaves)
        ledger = next(
            s for d in result["tree"]["domains"] for s in d["scenarios"] if s["key"] == "receipt.payment.ledger"
        )
        self.assertEqual([i["intent"] for i in ledger["intents"]], ["view"])

    def test_unmapped_leaf_reported_not_grouped(self):
        extra = dict(self.leaves[0], menu_xmlid="smart_construction_core.menu_not_in_surface")
        result = PROJ.project_scenario_navigation(surface=self.surface, authorized_leaves=self.leaves + [extra])
        self.assertEqual(result["diagnostics"]["unmapped_count"], 1)
        self.assertIn("smart_construction_core.menu_not_in_surface", result["diagnostics"]["unmapped_menu_xmlids"])
        self.assertEqual(result["diagnostics"]["grouped_menu_count"], 91)

    def test_invalid_surface_returns_fallback_contract(self):
        result = PROJ.project_scenario_navigation(surface={"schema": "wrong"}, authorized_leaves=self.leaves)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error_code"], "SURFACE_INVALID")
        self.assertIsNone(result["tree"])

    def test_flatten_authorized_nav_leaves_preserves_identity(self):
        subset = self.released[:4]
        nav = synthetic_nav(subset)
        authority = synthetic_route_authority(subset)
        leaves = PROJ.flatten_authorized_nav_leaves(nav, authority)
        self.assertEqual(len(leaves), 4)
        self.assertEqual(leaves[0]["menu_xmlid"], subset[0])
        self.assertEqual(leaves[0]["action_xmlid"], "action.1")
        self.assertEqual(leaves[0]["route"], "/a/1?menu_id=1")

    def test_project_authorized_nav_end_to_end(self):
        nav = synthetic_nav(self.released)
        authority = synthetic_route_authority(self.released)
        result = PROJ.project_authorized_nav(nav=nav, route_authority=authority, surface=self.surface)
        self.assertTrue(result["ok"])
        self.assertEqual(result["diagnostics"]["grouped_menu_count"], 91)
        self.assertEqual(result["diagnostics"]["unmapped_count"], 0)
        self.assertEqual(len(result["tree"]["platform"]), 7)
        self.assertEqual(len(result["tree"]["horizontal"]), 5)

    def test_zero_business_scenes_keep_only_authorized_management_entries(self):
        subset = self.surface["horizontal_work_center"]["menus"] + self.surface["platform_support"]["menus"]
        result = PROJ.project_authorized_nav(nav=synthetic_nav(subset),
            route_authority=synthetic_route_authority(subset), surface=self.surface)
        self.assertEqual(result["tree"]["domains"], [])
        self.assertEqual(len(result["tree"]["horizontal"]), 5)
        self.assertEqual(len(result["tree"]["platform"]), 7)
        self.assertEqual(result["tree"]["platform_label"], "产品配置")
        authority = synthetic_route_authority(subset)
        authority["primary_actions"] = authority["primary_actions"][:5]
        revoked = PROJ.project_authorized_nav(nav=synthetic_nav(subset[:5]), route_authority=authority, surface=self.surface)
        self.assertEqual(revoked["tree"]["platform"], [])

    def test_management_workspace_has_effective_scene_delivery_declaration(self):
        policy = json.loads((ROOT / "docs/product/delivery/v1/construction_pm_v1_scene_surface_policy.json").read_text())
        surface_policy = policy["surfaces"][policy["default_surface"]]
        published = set(surface_policy["nav_allowlist"] + surface_policy["deep_link_allowlist"])
        for entry in self.surface["platform_support"]["workspace_entries"]:
            self.assertIn(entry["scene_key"], published)

    def test_setup_workspace_uses_native_acl_and_delivered_scene(self):
        scene = {"key": "enterprise.setup", "name": "企业初始化工作空间", "target": {"route": "/s/enterprise.setup"}}
        seen = []
        def allowed(model, operation):
            seen.append((model, operation))
            return True
        rows = PROJ.project_management_workspaces(scenes=[scene], check_access=allowed, surface=self.surface)
        self.assertEqual(rows, [{"key": "enterprise.setup", "label": scene["name"], "route": scene["target"]["route"]}])
        self.assertEqual(seen, [("sc.scene.company.enablement", operation) for operation in ["read", "create", "write"]])
        for denied_operation in ["read", "create", "write"]:
            self.assertEqual(PROJ.project_management_workspaces(scenes=[scene], surface=self.surface,
                check_access=lambda model, operation: operation != denied_operation), [])
        self.assertEqual(PROJ.project_management_workspaces(scenes=[], check_access=allowed, surface=self.surface), [])
        self.assertEqual(PROJ.project_management_workspaces(scenes=[dict(scene, access={"allowed": False})],
            check_access=allowed, surface=self.surface), [])

    def test_role_difference_only_authorized_scenarios_present(self):
        finance_only = [
            "smart_construction_core.menu_sc_user_payment_apply",
            "smart_construction_core.menu_sc_payment_execution",
            "smart_construction_core.menu_sc_funding_plan_summary",
        ]
        nav = synthetic_nav(finance_only)
        authority = synthetic_route_authority(finance_only)
        result = PROJ.project_authorized_nav(nav=nav, route_authority=authority, surface=self.surface)
        self.assertTrue(result["ok"])
        domain_keys = {d["key"] for d in result["tree"]["domains"]}
        self.assertEqual(domain_keys, {"finance"})

    def test_scene_entry_leaf_without_action_is_collected(self):
        scene_entry_nav = [{
            "xmlid": "smart_construction_core.menu_sc_workspace_home",
            "menu_xmlid": "smart_construction_core.menu_sc_workspace_home",
            "label": "角色首页",
            "menu_id": 1,
            "action_id": 0,
            "route": "/m/1",
            "children": [],
            "canonical_navigation": {
                "schema_version": "1.0",
                "key": "smart_construction_core.menu_sc_workspace_home",
                "menu_id": 1,
                "action_id": 0,
                "label": "角色首页",
                "route": "/s/workspace.home",
                "state": "enabled",
            },
        }]
        leaves = PROJ.flatten_authorized_nav_leaves(scene_entry_nav, {})
        self.assertEqual(len(leaves), 1)
        self.assertEqual(leaves[0]["menu_xmlid"], "smart_construction_core.menu_sc_workspace_home")
        self.assertEqual(leaves[0]["action_id"], 0)
        self.assertEqual(leaves[0]["route"], "/s/workspace.home")


if __name__ == "__main__":
    sys.exit(0 if unittest.main(verbosity=2, exit=False).result.wasSuccessful() else 1)
