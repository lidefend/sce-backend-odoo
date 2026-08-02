# -*- coding: utf-8 -*-
import importlib.util
import sys
import types
import unittest
from pathlib import Path


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
