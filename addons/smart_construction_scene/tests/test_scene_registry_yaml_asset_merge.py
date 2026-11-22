# -*- coding: utf-8 -*-
import importlib.util
import json
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scene_registry.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("scene_registry_yaml_asset_merge_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class TestSceneRegistryYamlAssetMerge(unittest.TestCase):
    def test_request_scope_loads_declarations_once_for_all_consumers(self):
        registry = _load_module()
        calls = []

        class RequestContext:
            def __init__(self):
                self.values = {}

            def resolve(self, key, loader):
                if key in self.values:
                    return self.values[key], False
                value = loader()
                self.values[key] = value
                return value, True

        context = RequestContext()

        def load(env, drift=None):
            del env, drift
            calls.append(1)
            return [
                {
                    "code": "projects.list",
                    "name": "项目台账",
                    "target": {"route": "/s/projects.list"},
                }
            ], {"load_from_db": 1}

        with patch.object(registry, "_load_scene_declarations_with_timings", side_effect=load):
            first = registry.load_effective_scene_declarations_for_request(
                None,
                request_context=context,
            )
            second, second_timings = (
                registry.load_effective_scene_declarations_with_timings_for_request(
                    None,
                    request_context=context,
                )
            )
            configured, configure_timings = (
                registry.load_scene_configs_with_timings_for_request(
                    None,
                    request_context=context,
                )
            )

        self.assertEqual(calls, [1])
        self.assertEqual(first, second)
        self.assertEqual(first, configured)
        self.assertIsNot(first, configured)
        self.assertEqual(second_timings, {})
        self.assertEqual(configure_timings, {})
        snapshot = context.values[registry.EFFECTIVE_SCENE_DECLARATIONS_FACT]
        self.assertEqual(
            snapshot.content_fingerprint,
            registry.scene_declaration_fingerprint(first),
        )

    def test_request_scoped_declarations_do_not_cross_contexts(self):
        registry = _load_module()
        calls = []

        class RequestContext:
            def __init__(self):
                self.values = {}

            def resolve(self, key, loader):
                if key in self.values:
                    return self.values[key], False
                self.values[key] = loader()
                return self.values[key], True

        def load(env, drift=None):
            del env, drift
            calls.append(1)
            return [{"code": f"scene.{len(calls)}", "target": {}}], {}

        with patch.object(registry, "_load_scene_declarations_with_timings", side_effect=load):
            first = registry.load_effective_scene_declarations_for_request(
                None,
                request_context=RequestContext(),
            )
            second = registry.load_effective_scene_declarations_for_request(
                None,
                request_context=RequestContext(),
            )

        self.assertEqual(calls, [1, 1])
        self.assertNotEqual(first, second)

    def test_request_snapshot_is_deeply_read_only_and_runtime_projection_is_isolated(self):
        registry = _load_module()

        class RequestContext:
            def __init__(self):
                self.values = {}

            def resolve(self, key, loader):
                if key in self.values:
                    return self.values[key], False
                value = loader()
                self.values[key] = value
                return value, True

        declaration = {
            "code": "projects.list",
            "target": {"route": "/s/projects.list", "model": "project.project"},
            "tiles": [{"key": "project.read", "status": "ga"}],
            "handling_entry_catalog": {
                "groups": [{"key": "operations", "items": [{"key": "open"}]}],
            },
        }
        context = RequestContext()
        with patch.object(
            registry,
            "_load_scene_declarations_with_timings",
            return_value=([deepcopy(declaration)], {"load_from_db": 1}),
        ):
            effective = registry.load_effective_scene_declarations_for_request(
                None,
                request_context=context,
            )
            snapshot = context.values[registry.EFFECTIVE_SCENE_DECLARATIONS_FACT]
            initial_fingerprint = snapshot.content_fingerprint
            with self.assertRaisesRegex(TypeError, "read-only"):
                effective[0]["target"]["route"] = "/s/changed"
            with self.assertRaisesRegex(TypeError, "read-only"):
                effective[0]["tiles"].append({"key": "changed"})
            with self.assertRaisesRegex(TypeError, "read-only"):
                effective[0]["handling_entry_catalog"]["groups"][0]["items"][0]["key"] = "changed"

            projected = registry.load_scene_configs_for_request(
                None,
                request_context=context,
            )
            projected[0]["target"]["route"] = "/s/runtime"
            projected[0]["tiles"].append({"key": "runtime"})
            projected[0]["access"] = {"allowed": False}

        self.assertEqual(
            registry.scene_declaration_fingerprint(snapshot.declarations),
            initial_fingerprint,
        )
        self.assertEqual(effective[0]["target"]["route"], "/s/projects.list")
        self.assertEqual(len(effective[0]["tiles"]), 1)
        self.assertEqual(
            effective[0]["handling_entry_catalog"]["groups"][0]["items"][0]["key"],
            "open",
        )

    def test_scene_fingerprint_detects_content_mutation(self):
        registry = _load_module()
        declarations = [{"code": "projects.list", "target": {"route": "/s/projects.list"}}]
        fingerprint = registry.scene_declaration_fingerprint(declarations)
        declarations[0]["target"]["route"] = "/s/changed"
        self.assertNotEqual(
            fingerprint,
            registry.scene_declaration_fingerprint(declarations),
        )

    def test_imported_handling_target_is_shared_with_data_only_declarations(self):
        registry = _load_module()
        original = {"code": "effective.imported", "name": "Imported handling", "target": {"route": "/s/effective.imported"},
                    "handling_entry_catalog": {"groups": [{"key": "operations", "label": "Operations", "items": [
                        {"key": "open", "label": "Open", "action_xmlid": "test.old_action"}]}]}}
        imported = deepcopy(original)
        imported["handling_entry_catalog"]["groups"][0]["items"][0]["action_xmlid"] = "test.new_action"
        config = SimpleNamespace(get_param=lambda key, *args: json.dumps({imported["code"]: imported})
                                 if key == registry.IMPORTED_SCENES_PARAM else "false")
        config.sudo = lambda: config
        class Env:
            def __getitem__(self, key):
                if key == "ir.config_parameter":
                    return config
                raise KeyError(key)
        with patch.object(registry, "_load_scene_registry_content_entries_with_timings", side_effect=lambda: ([deepcopy(original)], {})), \
                patch.object(registry, "_load_scene_asset_entries_with_timings", return_value=([], {})):
            declarations = registry.load_effective_scene_declarations(Env())
            page = registry.load_scene_configs(Env())
        declared = next(row for row in declarations if row["code"] == imported["code"])
        rendered = next(row for row in page if row["code"] == imported["code"])
        self.assertEqual(declared["handling_entry_catalog"], rendered["handling_entry_catalog"])
        self.assertEqual(declared["handling_entry_catalog"]["groups"][0]["items"][0]["action_xmlid"], "test.new_action")

    def test_db_declaration_read_never_calls_capability_projection(self):
        registry = _load_module()
        definition = {"code": "effective.frozen", "name": "Frozen", "tiles": [{"key": "cap", "payload": {"action_id": 101}}]}
        record = SimpleNamespace(code=definition["code"], to_effective_definition_dict=lambda: deepcopy(definition))
        projections = []
        def project(tiles, user, **kwargs):
            projections.append(user)
            return [{**row, "allowed": False} for row in tiles]
        record._filter_payload_tiles = project
        env = SimpleNamespace(user="reader")
        with patch.object(registry, "_published_db_scenes", return_value=[record]), \
                patch.object(registry, "_load_imported_scenes", return_value=[]), \
                patch.object(registry, "_load_scene_registry_content_entries_with_timings", return_value=([], {})), \
                patch.object(registry, "_load_scene_asset_entries_with_timings", return_value=([], {})):
            declarations = registry.load_effective_scene_declarations(env)
            self.assertEqual(projections, [])
            page = registry.load_scene_configs(env)
        self.assertNotIn("allowed", declarations[0]["tiles"][0])
        self.assertFalse(page[0]["tiles"][0]["allowed"])
        self.assertEqual(projections, ["reader"])

    def test_load_scene_configs_prefers_registry_target_xmlids_over_stale_db_numeric_ids(self):
        target = _load_module()
        original_load_from_db = target._load_from_db
        original_load_imported = target._load_imported_scenes
        original_load_content = target._load_scene_registry_content_entries_with_timings
        try:
            target._load_from_db = lambda env, drift=None: [
                {
                    "code": "projects.list",
                    "name": "项目台账",
                    "target": {
                        "route": "/s/projects.list",
                        "action_id": 519,
                        "menu_id": 329,
                    },
                }
            ]
            target._load_imported_scenes = lambda env, drift=None: []
            target._load_scene_registry_content_entries_with_timings = lambda: (
                [
                    {
                        "code": "projects.list",
                        "name": "项目列表",
                        "target": {
                            "route": "/s/projects.list",
                        "menu_xmlid": "smart_construction_core.menu_sc_project_project",
                            "action_xmlid": "smart_construction_core.action_sc_project_list",
                        },
                    }
                ],
                {},
            )
            rows, _timings = target.load_scene_configs_with_timings(None)
        finally:
            target._load_from_db = original_load_from_db
            target._load_imported_scenes = original_load_imported
            target._load_scene_registry_content_entries_with_timings = original_load_content

        projects_list = next((row for row in rows if row.get("code") == "projects.list"), {})
        scene_target = (projects_list.get("target") or {})
        self.assertEqual(scene_target.get("route"), "/s/projects.list")
        self.assertEqual(scene_target.get("action_xmlid"), "smart_construction_core.action_sc_project_list")
        self.assertEqual(scene_target.get("menu_xmlid"), "smart_construction_core.menu_sc_project_project")
        self.assertNotIn("action_id", scene_target)
        self.assertNotIn("menu_id", scene_target)

    def test_load_scene_configs_merges_yaml_asset_fields_into_registry_row(self):
        target = _load_module()
        original_load_from_db = target._load_from_db
        original_load_imported = target._load_imported_scenes
        original_load_content = target._load_scene_registry_content_entries_with_timings
        try:
            target._load_from_db = lambda env, drift=None: []
            target._load_imported_scenes = lambda env, drift=None: []
            target._load_scene_registry_content_entries_with_timings = lambda: (
                [
                    {
                        "code": "projects.ledger",
                        "name": "项目台账",
                        "target": {
                            "route": "/s/projects.ledger",
                            "menu_xmlid": "smart_construction_core.menu_sc_project_project",
                            "action_xmlid": "smart_construction_core.action_sc_project_list",
                        },
                    }
                ],
                {},
            )
            rows, _timings = target.load_scene_configs_with_timings(None)
        finally:
            target._load_from_db = original_load_from_db
            target._load_imported_scenes = original_load_imported
            target._load_scene_registry_content_entries_with_timings = original_load_content

        ledger = next((row for row in rows if row.get("code") == "projects.ledger"), {})
        self.assertEqual(((ledger.get("target") or {}).get("route")), "/s/projects.ledger")
        self.assertEqual(((ledger.get("page") or {}).get("route")), "/s/projects.ledger")
        self.assertEqual([zone.get("name") for zone in (ledger.get("zones") or [])], ["header", "search", "main"])
        self.assertEqual(((ledger.get("blocks") or [])[0] or {}).get("source"), "ui_base_contract.views.tree")
        self.assertEqual(((ledger.get("search_surface") or {}).get("source")), "ui_base_contract.search")
        self.assertEqual(((ledger.get("permission_surface") or {}).get("source")), "ui_base_contract.permissions")

    def test_load_scene_configs_merges_cost_project_budget_yaml_asset_fields(self):
        target = _load_module()
        original_load_from_db = target._load_from_db
        original_load_imported = target._load_imported_scenes
        original_load_content = target._load_scene_registry_content_entries_with_timings
        try:
            target._load_from_db = lambda env, drift=None: []
            target._load_imported_scenes = lambda env, drift=None: []
            target._load_scene_registry_content_entries_with_timings = lambda: (
                [
                    {
                        "code": "cost.project_budget",
                        "name": "预算管理",
                        "target": {
                            "route": "/s/cost.project_budget",
                        },
                    }
                ],
                {},
            )
            rows, _timings = target.load_scene_configs_with_timings(None)
        finally:
            target._load_from_db = original_load_from_db
            target._load_imported_scenes = original_load_imported
            target._load_scene_registry_content_entries_with_timings = original_load_content

        budget = next((row for row in rows if row.get("code") == "cost.project_budget"), {})
        self.assertEqual(((budget.get("target") or {}).get("route")), "/s/cost.project_budget")
        self.assertEqual(((budget.get("page") or {}).get("route")), "/s/cost.project_budget")
        self.assertEqual([zone.get("name") for zone in (budget.get("zones") or [])], ["header", "search", "main"])
        self.assertEqual(((budget.get("blocks") or [])[0] or {}).get("source"), "ui_base_contract.views.tree")
        self.assertEqual(((budget.get("search_surface") or {}).get("source")), "ui_base_contract.search")
        self.assertEqual(((budget.get("permission_surface") or {}).get("source")), "ui_base_contract.permissions")


if __name__ == "__main__":
    unittest.main()
