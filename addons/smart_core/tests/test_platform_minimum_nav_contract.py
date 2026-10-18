# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path


SMART_CORE_DIR = Path(__file__).resolve().parents[1]


def _install_module(name: str, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _install_stubs():
    for name in list(sys.modules):
        if name.startswith("odoo"):
            sys.modules.pop(name, None)
    odoo = _install_module("odoo", SUPERUSER_ID=1, api=object())
    _install_module("odoo.addons")
    _install_module("odoo.addons.smart_core")
    _install_module("odoo.addons.smart_core.core")
    _install_module("odoo.addons.smart_core.delivery")
    _install_module("odoo.addons.smart_core.utils")
    _install_module("odoo.addons.smart_core.security")
    _install_module(
        "odoo.addons.smart_core.utils.extension_hooks",
        call_extension_hook_first=lambda *args, **kwargs: None,
    )
    _install_module(
        "odoo.addons.smart_core.security.platform_admin",
        user_is_platform_admin=lambda user: False,
    )
    _install_module(
        "odoo.addons.smart_core.utils.backend_contract_boundaries",
        MENU_CONFIG_POLICY_MODEL="ui.menu.config.policy",
    )
    _install_module(
        "odoo.addons.smart_core.core.source_authority",
        build_source_authority_contract=lambda *args, **kwargs: {},
    )
    _install_module(
        "odoo.addons.smart_core.core.delivery_menu_defaults",
        build_delivery_menu_child=lambda *args, **kwargs: {},
        build_delivery_menu_group=lambda *args, **kwargs: {},
        build_delivery_menu_root=lambda *args, **kwargs: {},
        synthetic_menu_id=lambda *args, **kwargs: 0,
    )
    _install_module(
        "odoo.addons.smart_core.core.navigation_entry_target",
        build_web_surface_entry_target=lambda *args, **kwargs: {},
    )
    _install_module(
        "odoo.addons.smart_core.delivery.menu_delivery_convergence_service",
        MenuDeliveryConvergenceService=type("MenuDeliveryConvergenceService", (), {}),
    )
    _install_module(
        "odoo.addons.smart_core.delivery.menu_fact_service",
        MenuFactService=type("MenuFactService", (), {}),
    )
    _install_module(
        "odoo.addons.smart_core.delivery.native_config_menu_projection",
        native_config_delivery_groups=lambda *args, **kwargs: [],
    )
    _install_module(
        "odoo.addons.smart_core.security.platform_admin",
        user_is_platform_admin=lambda user: False,
        can_discover_platform_capabilities=lambda user: False,
    )
    return odoo


def _load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class _RecordSet:
    def __init__(self, count: int = 0):
        self._count = count

    def sudo(self):
        return self

    def search_count(self, domain):
        return self._count

    def get_param(self, key, default=""):
        return default


class _Env:
    def __init__(self, installed_modules: int = 0):
        self._module_records = _RecordSet(installed_modules)
        self._params = _RecordSet()

    def __getitem__(self, name):
        if name == "ir.module.module":
            return self._module_records
        if name == "ir.config_parameter":
            return self._params
        raise KeyError(name)


class PlatformMinimumNavContractTests(unittest.TestCase):
    def _load(self):
        _install_stubs()
        contract = _load_module(
            "odoo.addons.smart_core.core.platform_minimum_nav_contract",
            SMART_CORE_DIR / "core" / "platform_minimum_nav_contract.py",
        )
        service_module = _load_module(
            "odoo.addons.smart_core.delivery.final_menu_navigation_service",
            SMART_CORE_DIR / "delivery" / "final_menu_navigation_service.py",
        )
        menu_service_module = _load_module(
            "odoo.addons.smart_core.delivery.menu_service",
            SMART_CORE_DIR / "delivery" / "menu_service.py",
        )
        return contract, service_module, menu_service_module

    def test_platform_mode_contract_is_non_empty_and_scene_isolated(self):
        contract, _service, _menu_service = self._load()

        payload = contract.build_platform_minimum_nav_contract()
        scene_keys = []

        def walk(nodes):
            for node in nodes or []:
                scene_key = str(node.get("scene_key") or (node.get("meta") or {}).get("scene_key") or "").strip()
                if scene_key:
                    scene_keys.append(scene_key)
                walk(node.get("children") or [])

        walk(payload["nav"])
        self.assertTrue(payload["nav"])
        self.assertEqual(scene_keys, ["workspace.home"])
        self.assertEqual(payload["default_route"]["scene_key"], "workspace.home")
        self.assertEqual(payload["default_route"]["reason"], "platform_minimum_surface")
        self.assertTrue(payload["meta"]["platform_minimum_surface"])
        leaf = payload["nav"][0]["children"][0]["children"][0]
        self.assertIsInstance(leaf["menu_id"], int)
        self.assertGreater(leaf["menu_id"], 0)
        self.assertEqual(leaf["entry_target"]["type"], "scene")
        self.assertEqual(leaf["entry_target"]["scene_key"], "workspace.home")
        self.assertEqual(payload["default_route"]["menu_id"], leaf["menu_id"])

    def test_declared_scene_leaf_survives_route_authority_projection(self):
        contract, _service, menu_service_module = self._load()
        payload = contract.build_platform_minimum_nav_contract()
        nav = payload["nav"]
        leaf = nav[0]["children"][0]["children"][0]
        specs = menu_service_module.MenuService._walk_nav_declared_entry_specs(nav)
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0]["menu_id"], leaf["menu_id"])
        self.assertEqual(specs[0]["entry_target"]["type"], "scene")
        authority = {
            "primary_actions": [],
            "role_home_actions": [
                {
                    **specs[0],
                    "route_kind": "ROLE_HOME_ACTION",
                    "action_id": 0,
                    "allowed_operation": "read",
                    "required_capability": "menu_container_visible",
                    "source": "nav.declared_entry",
                }
            ],
            "contextual_actions": [],
            "admin_actions": [],
            "denied_actions": [],
            "menu_containers": [],
        }
        filtered = menu_service_module.MenuService.filter_nav_by_route_authority(nav, authority)
        self.assertEqual(len(filtered), 1)
        filtered_leaf = filtered[0]["children"][0]["children"][0]
        self.assertEqual(filtered_leaf["menu_id"], leaf["menu_id"])
        projected = menu_service_module.MenuService.project_canonical_navigation(filtered, authority)
        projected_leaf = projected[0]["children"][0]["children"][0]
        self.assertEqual(projected_leaf["canonical_navigation"]["state"], "enabled")
        self.assertEqual(projected_leaf["canonical_navigation"]["route"], "/")
        self.assertEqual(projected_leaf["canonical_navigation"]["menu_id"], leaf["menu_id"])

    def test_platform_menu_service_returns_the_same_minimum_surface(self):
        contract, service_module, _menu_service = self._load()
        env = _Env(installed_modules=0)
        self.assertTrue(contract.is_platform_minimum_surface_mode(env, {}))

        navigation = service_module.FinalMenuNavigationService(env).build()
        flat = navigation["nav_fact"]["flat"]
        keys = [row["key"] for row in flat]

        self.assertEqual(keys, ["root:scene_contract", "group:role_primary", "scene:workspace.home"])
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(flat[-1]["scene_key"], "workspace.home")
        self.assertEqual(flat[-1]["action_type"], "scene.contract")
        self.assertTrue(navigation["meta"]["platform_minimum_surface"])
        self.assertEqual(navigation["meta"]["nav_source"], "platform_minimum_surface")

    def test_industry_install_leaves_platform_minimum_mode(self):
        contract, _service, _menu_service = self._load()
        env = _Env(installed_modules=1)
        # The hook is stubbed to None, so configure the fallback module list.
        env._params = _RecordSet()
        env._params.get_param = lambda key, default="": (
            "smart_construction_core" if key == "smart_core.industry_extension_modules" else default
        )

        self.assertFalse(contract.is_platform_minimum_surface_mode(env, {}))


if __name__ == "__main__":
    unittest.main()
