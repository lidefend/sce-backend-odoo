# -*- coding: utf-8 -*-
import ast
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock


CORE_DIR = Path(__file__).resolve().parents[1] / "core"


def _load_module():
    sys.modules.setdefault("odoo", types.ModuleType("odoo"))
    sys.modules.setdefault("odoo.addons", types.ModuleType("odoo.addons"))
    smart_core_pkg = sys.modules.setdefault("odoo.addons.smart_core", types.ModuleType("odoo.addons.smart_core"))
    smart_core_pkg.__path__ = [str(CORE_DIR.parent)]
    core_pkg = sys.modules.setdefault("odoo.addons.smart_core.core", types.ModuleType("odoo.addons.smart_core.core"))
    core_pkg.__path__ = [str(CORE_DIR)]
    utils_pkg = sys.modules.setdefault("odoo.addons.smart_core.utils", types.ModuleType("odoo.addons.smart_core.utils"))
    utils_pkg.__path__ = [str(CORE_DIR.parent / "utils")]

    source_authority = types.ModuleType("odoo.addons.smart_core.core.source_authority")
    source_authority.build_source_authority_contract = lambda **kwargs: dict(kwargs)
    sys.modules["odoo.addons.smart_core.core.source_authority"] = source_authority

    extension_hooks = types.ModuleType("odoo.addons.smart_core.utils.extension_hooks")
    extension_hooks.iter_extension_modules = lambda env: []
    sys.modules["odoo.addons.smart_core.utils.extension_hooks"] = extension_hooks

    module_name = "odoo.addons.smart_core.core.system_init_extension_fact_merger"
    spec = importlib.util.spec_from_file_location(module_name, CORE_DIR / "system_init_extension_fact_merger.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class TestConstructionFactConsumption(unittest.TestCase):
    def test_collection_pruning_preserves_noncollection_facts_and_legacy_calls(self):
        path = CORE_DIR.parents[1] / "smart_construction_core/core_extension.py"
        tree = ast.parse(path.read_text())
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_system_init_fact_contributions")
        collection_builders = ["_build_task_action_rows", "_build_payment_action_rows", "_build_risk_action_rows",
                               "_build_project_action_rows", "_build_home_object_rows"]
        retained_builders = ["_build_role_entry_contract_rows", "_build_home_block_contract_rows",
                             "_build_enterprise_enablement_contract"]
        for context, expected in [(None, 1), ({}, 1), ({"include_workspace_collections": True}, 1),
                                  ({"include_workspace_collections": False}, 0),
                                  ({"include_workspace_collections": 0}, 1), ({"include_workspace_collections": ""}, 1)]:
            with self.subTest(context=context):
                ns = {name: Mock(return_value=[{"id": 1}]) for name in collection_builders + retained_builders}
                ns.update(_hook_facts=types.SimpleNamespace(role_surface_override_provider=lambda value: value),
                          _contract_role_surface_overrides=lambda: {"role": "retained"}, _logger=Mock())
                exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), "exec"), ns)
                env, user = object(), object()
                result = ns[function.name](env, user, context=context)
                self.assertIsNotNone(result)
                ns["_logger"].warning.assert_not_called()
                for name in collection_builders:
                    self.assertEqual(ns[name].call_count, expected, name)
                for name in retained_builders:
                    self.assertEqual(ns[name].call_count, 1, name)
                self.assertEqual(set(result["facts"]) - {"workspace_collections", "workspace_collection_export_keys", "workspace_business_source"},
                                 {"role_surface_override_provider", "role_entries", "home_blocks", "enterprise_enablement"})
                self.assertEqual(len(result["collections"]), 5 if expected else 0)
                self.assertEqual(ns["_build_enterprise_enablement_contract"].call_args.args, (env, user))


class TestSystemInitExtensionFactMerger(unittest.TestCase):
    def test_default_workspace_collection_export_keys_are_platform_generic(self):
        module = _load_module()
        data = {
            "ext_facts": {
                "x": {
                    "workspace_collections": {
                        "task_items": [{"id": 1}],
                        "risk_actions": [{"id": 2}],
                        "payment_requests": [{"id": 3}],
                        "project_actions": [{"id": 4}],
                    }
                }
            }
        }

        module.merge_extension_facts(data)

        self.assertEqual(data.get("task_items"), [{"id": 1}])
        self.assertEqual(data.get("risk_actions"), [{"id": 2}])
        self.assertNotIn("payment_requests", data)
        self.assertNotIn("project_actions", data)

    def test_extension_can_declare_workspace_collection_export_keys(self):
        module = _load_module()
        data = {
            "ext_facts": {
                "x": {
                    "workspace_collection_export_keys": ["payment_requests", "project_actions"],
                    "workspace_collections": {
                        "payment_requests": [{"id": 3}],
                        "project_actions": [{"id": 4}],
                    },
                }
            }
        }

        module.merge_extension_facts(data)

        self.assertEqual(data.get("payment_requests"), [{"id": 3}])
        self.assertEqual(data.get("project_actions"), [{"id": 4}])

    def test_extension_role_surface_provider_is_promoted_for_selection(self):
        module = _load_module()
        provider = {
            "key": "smart_construction_core",
            "priority": 100,
            "domain_key": "construction",
            "role_surface_overrides": {"business_config_admin": {"label": "业务配置管理员"}},
        }
        data = {
            "ext_facts": {
                "smart_construction_core": {
                    "role_surface_override_provider": provider,
                }
            }
        }

        module.merge_extension_facts(data)

        promoted = data["role_surface_override_providers"]["smart_construction_core"]
        self.assertNotIn("key", promoted)
        self.assertEqual(promoted["priority"], 100)
        self.assertEqual(promoted["domain_key"], "construction")
        self.assertIn("business_config_admin", promoted["role_surface_overrides"])


if __name__ == "__main__":
    unittest.main()
