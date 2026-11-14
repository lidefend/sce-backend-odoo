#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Static guard for the scenario product surface projection.

Pure Python (no Odoo). Loads the P1 scenario surface contract and the released
92 menu identities from product_menu_source, then proves the projection regroups
all 92 into scenario/horizontal/direct-platform surfaces without re-authoring
identity.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import unittest
import types
from unittest.mock import Mock, patch
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


class SceneDeclarationConsumptionTest(unittest.TestCase):
    def test_declarations_empty_compatibility_and_ambiguity(self):
        scene = {"code": "scene.a", "target": {"menu_id": 10, "action_id": 20}}
        for declared, fallback_calls, expected in [
            ([scene], 0, {(10, 20): "scene.a"}), ([], 0, {}),
            (None, 1, {(10, 20): "scene.a"}), ({}, 1, {(10, 20): "scene.a"}),
        ]:
            with self.subTest(declared=declared):
                hook = Mock(return_value=declared)
                provider = Mock(return_value={"scenes": [scene]})
                with patch.dict(sys.modules, {
                    "odoo.addons.smart_core.utils.extension_hooks": types.SimpleNamespace(call_extension_hook_first=hook),
                    "odoo.addons.smart_core.core.scene_provider": types.SimpleNamespace(load_scenes_from_db_or_fallback=provider),
                }):
                    env = object()
                    self.assertEqual(PROJ._scene_targets_by_pair(env), (expected, []))
                    hook.assert_called_once_with(env, "smart_core_delivery_scene_declarations", env)
                    self.assertEqual(provider.call_count, fallback_calls)

    def test_declaration_xmlid_default_action_and_conflicts(self):
        scenes = [
            {"code": "scene.a", "target": {"menu_xmlid": "menu"}},
            {"key": "scene.b", "target": {"menu_id": "11", "action_xmlid": "action"}},
            {"code": "scene.c", "target": {"menu_id": 10, "action_id": 20}},
            {"code": "scene.a", "target": {"menu_id": 10, "action_id": 20}},
        ]
        action = types.SimpleNamespace(id=20)
        env = types.SimpleNamespace(ref=lambda key, **kw: {"menu": types.SimpleNamespace(id=10, action=action), "action": action}.get(key))
        with patch.dict(sys.modules, {
            "odoo.addons.smart_core.utils.extension_hooks": types.SimpleNamespace(call_extension_hook_first=lambda *args: scenes),
            "odoo.addons.smart_core.core.scene_provider": types.SimpleNamespace(load_scenes_from_db_or_fallback=Mock(side_effect=AssertionError("unused full projection"))),
        }):
            self.assertEqual(PROJ._scene_targets_by_pair(env), ({(11, 20): "scene.b"}, ["10/20"]))


def released_menu_xmlids():
    src = PMS.load_source()
    _contract, pub = PMS.project(src)
    standard = next(p for p in pub["products"] if p.get("edition_key") == "standard")
    return [row["menu_xmlid"] for group in standard["menu_groups"] for row in group["menus"]]


HORIZONTAL_MENUS = [
    "smart_construction_core.menu_sc_workspace_home",
    "smart_construction_core.menu_sc_my_work",
    "smart_construction_core.menu_sc_operating_metrics_project",
    "smart_construction_core.menu_sc_project_kanban",
    "smart_construction_core.menu_sc_workbench_my_todo_fact",
    "smart_construction_core.menu_sc_product_message_notification_v1",
]
PLATFORM_MENUS = [
    "smart_construction_core.menu_sc_business_config_workbench",
    "smart_construction_core.menu_sc_approval_policy",
    "smart_construction_core.menu_ui_form_field_policy_business_config",
    "smart_construction_core.menu_ui_menu_config_policy_business_config",
    "smart_construction_core.menu_sc_product_data_permission_v1",
    "smart_construction_core.menu_sc_product_system_parameter_v1",
    "smart_construction_core.menu_sc_product_numbering_rule_v1",
    "smart_construction_core.menu_sc_runtime_user_management",
]
HORIZONTAL_ROOT = "smart_construction_core.menu_sc_workspace_center"
PLATFORM_ROOT = "smart_construction_core.menu_sc_business_config_center"


def native_parent_by_menu():
    mapping = {}
    for menu in HORIZONTAL_MENUS:
        mapping[menu] = HORIZONTAL_ROOT
    for menu in PLATFORM_MENUS:
        mapping[menu] = PLATFORM_ROOT
    return mapping


def synthetic_leaves(menu_xmlids, parent_by_menu=None):
    parent_by_menu = parent_by_menu or {}
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
            "parent_menu_xmlid": parent_by_menu.get(xmlid, ""),
        })
    return leaves


def synthetic_nav(menu_xmlids, parent_by_menu=None):
    parent_by_menu = parent_by_menu or {}
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
            "parent_menu_xmlid": parent_by_menu.get(xmlid, ""),
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
    def test_native_config_surface_is_independent_of_released_business_catalog(self):
        leaf = {'menu_xmlid': 'test.native_workspace', 'menu_id': 901, 'action_id': 902,
                'label': 'Native workspace', 'route': '/s/test.workspace',
                'delivery_bucket': 'delivery_business_config',
                'entry_target': {'type': 'admin_surface', 'surface': 'test', 'route': '/s/test.workspace', 'delivery_scope': 'configuration'}}
        result = PROJ.project_scenario_navigation(surface=self.surface, authorized_leaves=[leaf], include_platform=True)
        self.assertEqual(result['tree']['platform'], [leaf])
        self.assertEqual(result['tree']['domains'], [])
        self.assertEqual(result['diagnostics']['unmapped_count'], 0)
        self.assertEqual(PROJ.project_scenario_navigation(surface=self.surface, authorized_leaves=[leaf])['tree']['platform'], [])
        for delta in ({'delivery_bucket': 'released_product_policy'}, {'entry_target': {}}):
            denied = PROJ.project_scenario_navigation(surface=self.surface, authorized_leaves=[dict(leaf, **delta)], include_platform=True)
            self.assertEqual(denied['tree']['platform'], [])
            self.assertEqual(denied['diagnostics']['unmapped_count'], 1)

    @classmethod
    def setUpClass(cls):
        cls.surface = PROJ.load_surface(SURFACE_PATH)
        cls.released = released_menu_xmlids()
        cls.parent_by_menu = native_parent_by_menu()
        cls.leaves = synthetic_leaves(cls.released, cls.parent_by_menu)

    def test_released_universe_is_exactly_92(self):
        self.assertEqual(len(self.released), 92)

    def test_surface_maps_all_92_and_only_them(self):
        index = PROJ.build_menu_index(self.surface, parent_by_menu=self.parent_by_menu)
        self.assertEqual(set(index), set(self.released))

    def test_runtime_user_management_is_direct_platform_not_scenario(self):
        assignments = PROJ.build_menu_assignments(
            self.surface,
            parent_by_menu=self.parent_by_menu,
        )
        rows = assignments["smart_construction_core.menu_sc_runtime_user_management"]
        self.assertEqual([row["location"] for row in rows], ["platform"])
        self.assertFalse(any(row["location"] == "scenario" for row in rows))

    def test_surface_declares_17_scenarios_under_6_domains(self):
        self.assertEqual(len(self.surface["scenarios"]), 17)
        self.assertEqual(len(self.surface["domains"]), 6)
        scenario_keys = {s["key"] for s in self.surface["scenarios"]}
        domain_keys = {k for d in self.surface["domains"] for k in d["scenarios"]}
        self.assertEqual(scenario_keys, domain_keys)

    def test_projection_groups_all_92_with_no_unmapped(self):
        result = PROJ.project_scenario_navigation(surface=self.surface, authorized_leaves=self.leaves)
        self.assertTrue(result["ok"])
        self.assertEqual(result["diagnostics"]["unmapped_count"], 0)
        self.assertEqual(result["diagnostics"]["grouped_menu_count"], 92)
        self.assertEqual(result["diagnostics"]["grouped_leaf_count"], 92)

    def test_projection_preserves_leaf_identity(self):
        result = PROJ.project_scenario_navigation(surface=self.surface, authorized_leaves=self.leaves, include_platform=True)
        domain_entries = [e for d in result["tree"]["domains"] for s in d["scenarios"] for i in s["intents"] for e in i["entries"]]
        horizontal = result["tree"]["horizontal"]
        platform = result["tree"]["platform"]
        self.assertEqual(len(domain_entries), 78)
        self.assertEqual(len(horizontal), 6)
        self.assertEqual(len(platform), 8)
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
        extra = dict(self.leaves[0], menu_xmlid="smart_construction_core.menu_not_in_surface", parent_menu_xmlid="")
        result = PROJ.project_scenario_navigation(surface=self.surface, authorized_leaves=self.leaves + [extra])
        self.assertEqual(result["diagnostics"]["unmapped_count"], 1)
        self.assertIn("smart_construction_core.menu_not_in_surface", result["diagnostics"]["unmapped_menu_xmlids"])
        self.assertEqual(result["diagnostics"]["grouped_menu_count"], 92)

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

    def test_flatten_actionless_parent_preserves_native_parent(self):
        nav = [{"menu_id": 1, "xmlid": "core.root", "children": [
            {"menu_id": 2, "xmlid": "core.group", "children": [
                {"menu_id": 3, "action_id": 30, "xmlid": "core.leaf"},
            ]},
        ]}]
        leaves = PROJ.flatten_authorized_nav_leaves(nav, {})
        self.assertEqual(len(leaves), 1)
        self.assertEqual(leaves[0]["menu_xmlid"], "core.leaf")
        self.assertEqual(leaves[0]["parent_menu_xmlid"], "core.group")

    def test_flatten_actionless_sibling_does_not_inherit_previous_identity(self):
        nav = [
            {"menu_id": 1, "action_id": 10, "xmlid": "core.previous"},
            {"menu_id": 2, "meta": {"menu_xmlid": "core.group"}, "children": [
                {"menu_id": 3, "action_id": 30, "xmlid": "core.leaf"},
            ]},
        ]
        leaves = PROJ.flatten_authorized_nav_leaves(nav, {})
        self.assertEqual(leaves[1]["parent_menu_xmlid"], "core.group")

    def test_project_authorized_nav_end_to_end(self):
        nav = synthetic_nav(self.released, native_parent_by_menu())
        authority = synthetic_route_authority(self.released)
        result = PROJ.project_authorized_nav(nav=nav, route_authority=authority, surface=self.surface)
        self.assertTrue(result["ok"])
        self.assertEqual(result["diagnostics"]["grouped_menu_count"], 92)
        self.assertEqual(result["diagnostics"]["unmapped_count"], 0)
        self.assertEqual(len(result["tree"]["platform"]), 8)
        self.assertEqual(len(result["tree"]["horizontal"]), 6)

    def test_zero_business_scenes_keep_only_authorized_management_entries(self):
        subset = HORIZONTAL_MENUS + PLATFORM_MENUS
        result = PROJ.project_authorized_nav(nav=synthetic_nav(subset, native_parent_by_menu()),
            route_authority=synthetic_route_authority(subset), surface=self.surface)
        self.assertEqual(result["tree"]["domains"], [])
        self.assertEqual(len(result["tree"]["horizontal"]), 6)
        self.assertEqual(len(result["tree"]["platform"]), 8)
        self.assertEqual(result["tree"]["platform_label"], "产品配置")
        authority = synthetic_route_authority(subset)
        authority["primary_actions"] = authority["primary_actions"][:5]
        revoked = PROJ.project_authorized_nav(nav=synthetic_nav(subset[:5], native_parent_by_menu()), route_authority=authority, surface=self.surface)
        self.assertEqual(revoked["tree"]["platform"], [])

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



class RuntimeMenuMetadataBatchTest(unittest.TestCase):
    def fixture(self, fail_batch=False):
        calls = []
        menus = []
        for mid, choices in [(9, ['native.first', 'alias.second']), (4, []), (7, ['native.seven'])]:
            menu = types.SimpleNamespace(id=mid, action=types.SimpleNamespace(id=80),
                                         sc_scenario_exempt=False, child_id=[])
            menu.get_external_id = Mock(return_value={mid: choices[0] if choices else ''})
            menus.append(menu)
        class Menus(list):
            def get_external_id(self):
                calls.append([m.id for m in self])
                if fail_batch: raise RuntimeError('batch unavailable')
                # Native selector owns multi-XMLID choice; no alternate selection.
                return {m.id: {9: 'native.first', 4: '', 7: 'native.seven'}[m.id] for m in self}
        class Scenarios(list):
            def mapped(self, path):
                assert path == 'entry_ids.menu_id'
                return Menus(menus[:2])
        entries = [types.SimpleNamespace(id=i+1, menu_id=menus[i], intent='view', sequence=20-i)
                   for i in [0, 1]]
        scenarios = Scenarios([types.SimpleNamespace(code='archived', name='Archived', active=False,
                                                     sequence=7, entry_ids=entries)])
        scenario_model, menu_model = Mock(), Mock()
        for model, records in [(scenario_model, scenarios), (menu_model, Menus(menus))]:
            model.sudo.return_value = model
            model.with_context.return_value = model
            model.search.return_value = records
        env = {'sc.product.scenario': scenario_model, 'ir.ui.menu': menu_model}
        return env, menus, calls

    def test_native_choice_empty_ids_archived_binding_and_order_match_singletons(self):
        env, menus, calls = self.fixture()
        surface = PROJ.load_runtime_surface(env)
        scope = PROJ.runtime_menu_scope(env, surface)
        self.assertEqual(calls, [[9, 4], [9, 4, 7]])
        for menu in menus: menu.get_external_id.assert_not_called()
        with patch.object(PROJ, '_menu_external_ids', return_value={}):
            original_surface = PROJ.load_runtime_surface(env)
            original_scope = PROJ.runtime_menu_scope(env, original_surface)
        self.assertEqual(surface, original_surface)
        self.assertEqual(scope, original_scope)
        self.assertFalse(surface['scenarios'][0]['active'])
        self.assertEqual(surface['scenarios'][0]['intents']['view'], ['native.first', 'menu:4'])
        self.assertEqual(scope[2][80], ['native.first', 'menu:4', 'native.seven'])
        env['sc.product.scenario'].with_context.assert_called_with(active_test=False)
        env['ir.ui.menu'].with_context.assert_called_with(**{'ir.ui.menu.full_list': True})

    def test_failed_batch_preserves_original_singleton_fallback(self):
        good_env, _, _ = self.fixture()
        expected = PROJ.load_runtime_surface(good_env)
        env, menus, calls = self.fixture(fail_batch=True)
        self.assertEqual(PROJ.load_runtime_surface(env), expected)
        self.assertEqual(calls, [[9, 4]])
        self.assertEqual(menus[0].get_external_id.call_count, 1)
        self.assertEqual(menus[1].get_external_id.call_count, 1)
        with patch.object(PROJ, '_menu_external_ids', return_value={}):
            expected_scope = PROJ.runtime_menu_scope(good_env, expected)
        self.assertEqual(PROJ.runtime_menu_scope(env, expected), expected_scope)

    def test_singleton_failure_keeps_native_id_fallback_without_cross_call_cache(self):
        env, menus, _ = self.fixture(fail_batch=True)
        menus[0].get_external_id.side_effect = RuntimeError('singleton unavailable')
        surface = PROJ.load_runtime_surface(env)
        self.assertEqual(surface['scenarios'][0]['intents']['view'], ['menu:9', 'menu:4'])
        menus[0].get_external_id.side_effect = None
        self.assertEqual(PROJ.load_runtime_surface(env)['scenarios'][0]['intents']['view'],
                         ['native.first', 'menu:4'])

if __name__ == "__main__":
    sys.exit(0 if unittest.main(verbosity=2, exit=False).result.wasSuccessful() else 1)
