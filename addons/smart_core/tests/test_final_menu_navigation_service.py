# -*- coding: utf-8 -*-
import importlib.util
import sys
import types
import unittest
from pathlib import Path


SMART_CORE_DIR = Path(__file__).resolve().parents[1]


def _install_module(name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _load_module():
    _install_module("odoo")
    _install_module("odoo.addons")
    smart_core_pkg = _install_module("odoo.addons.smart_core")
    smart_core_pkg.__path__ = [str(SMART_CORE_DIR)]
    delivery_pkg = _install_module("odoo.addons.smart_core.delivery")
    delivery_pkg.__path__ = [str(SMART_CORE_DIR / "delivery")]

    class _ConvergenceService:
        def __init__(self, env):
            self.env = env

    class _FactService:
        def __init__(self, env):
            self.env = env

    class _InterpreterService:
        def __init__(self, env):
            self.env = env

    _install_module(
        "odoo.addons.smart_core.delivery.menu_delivery_convergence_service",
        MenuDeliveryConvergenceService=_ConvergenceService,
    )
    _install_module(
        "odoo.addons.smart_core.delivery.menu_fact_service",
        MenuFactService=_FactService,
    )
    _install_module(
        "odoo.addons.smart_core.delivery.menu_target_interpreter_service",
        MenuTargetInterpreterService=_InterpreterService,
    )
    _install_module("odoo.addons.smart_core.security")
    _install_module(
        "odoo.addons.smart_core.security.platform_admin",
        can_discover_platform_capabilities=lambda user: False,
        user_is_platform_admin=lambda user: False,
    )
    _install_module("odoo.addons.smart_core.utils")
    _install_module(
        "odoo.addons.smart_core.utils.backend_contract_boundaries",
        MENU_CONFIG_NAV_ENABLED_PARAM="smart_core.menu_config.nav_enabled",
        MENU_CONFIG_POLICY_MODEL="ui.menu.config.policy",
    )
    _install_module(
        "odoo.addons.smart_core.utils.extension_hooks",
        call_extension_hook_first=lambda env, hook_name, *args, **kwargs: None,
    )

    sys.modules.pop("odoo.addons.smart_core.delivery.final_menu_navigation_service", None)
    spec = importlib.util.spec_from_file_location(
        "odoo.addons.smart_core.delivery.final_menu_navigation_service",
        SMART_CORE_DIR / "delivery" / "final_menu_navigation_service.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TestFinalMenuNavigationService(unittest.TestCase):
    def setUp(self):
        self.module = _load_module()

    def test_delivery_group_uses_config_ref_as_navigation_fact_menu_id(self):
        node = {
            "menu_id": 889777446,
            "label": "合同中心",
            "config_ref": {"model": "ir.ui.menu", "id": 293},
            "config_menu_id": 293,
            "children": [
                {
                    "menu_id": 361,
                    "label": "一般合同（公司）",
                    "meta": {"action_id": 1001, "model": "sc.general.contract"},
                }
            ],
        }

        fact = self.module._delivery_node_to_fact(node)

        self.assertEqual(fact["menu_id"], 293)
        self.assertEqual(fact["runtime_menu_id"], 889777446)
        self.assertEqual(fact["config_menu_id"], 293)
        self.assertEqual(fact["config_ref"], {"model": "ir.ui.menu", "id": 293})
        self.assertTrue(fact["configurable"])
        self.assertTrue(fact["synthetic"])
        self.assertEqual(fact["node_kind"], "group")

    def test_flatten_fact_tree_preserves_real_child_ids(self):
        tree = [
            {
                "menu_id": 293,
                "name": "合同中心",
                "children": [
                    {"menu_id": 361, "name": "一般合同（公司）", "children": []},
                    {"menu_id": 389, "name": "施工合同", "children": []},
                ],
            }
        ]

        flat = self.module._flatten_fact_tree(tree)

        self.assertEqual([row["menu_id"] for row in flat], [293, 361, 389])
        self.assertEqual(flat[0]["child_ids"], [361, 389])

    def test_runtime_navigation_preserves_declared_role_surface_restrictions(self):
        service = object.__new__(self.module.FinalMenuNavigationService)
        service._is_platform_admin_user = lambda: False
        service._can_discover_platform_capabilities = lambda: True
        service._is_business_config_user = lambda: False
        declared = {
            "role_code": "executive",
            "discover_installed_capabilities": True,
            "system_configuration_visible": False,
            "menu_blocklist_xmlids": ["example.menu_configuration"],
            "model_blocklist": ["example.configuration"],
        }

        surface = service._runtime_role_surface({"role_surface": declared})

        self.assertEqual(surface["role_code"], "executive")
        self.assertTrue(surface["discover_installed_capabilities"])
        self.assertFalse(surface["system_configuration_visible"])
        self.assertEqual(
            surface["menu_blocklist_xmlids"],
            ["example.menu_configuration"],
        )
        self.assertEqual(surface["model_blocklist"], ["example.configuration"])
        self.assertFalse(surface["is_platform_admin"])
        self.assertFalse(surface["is_business_config_admin"])

    def test_build_propagates_delivery_contract_failure_without_native_fallback(self):
        service = object.__new__(self.module.FinalMenuNavigationService)
        service._build_delivery_navigation_contract = lambda: (_ for _ in ()).throw(
            RuntimeError("delivery_failed")
        )

        with self.assertRaisesRegex(RuntimeError, "delivery_failed"):
            service.build()

        source = (SMART_CORE_DIR / "delivery" / "final_menu_navigation_service.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("MenuFactService", source)
        self.assertNotIn("MenuTargetInterpreterService", source)

    def test_system_init_reapplies_role_surface_after_delivery_overlays(self):
        source = (
            SMART_CORE_DIR / "handlers" / "system_init.py"
        ).read_text(encoding="utf-8")
        delivery_assignment = (
            'delivery_nav = delivery_payload.get("nav") '
            'if isinstance(delivery_payload.get("nav"), list) else []'
        )
        role_filter = (
            "delivery_nav = MenuService._filter_role_surface_nodes("
        )
        self.assertIn(delivery_assignment, source)
        self.assertIn(role_filter, source)
        self.assertLess(source.index(delivery_assignment), source.index(role_filter))
        filtered_snapshot = "_delivery_authoritative_nav = list(delivery_nav)"
        self.assertIn(filtered_snapshot, source)
        self.assertLess(source.index(role_filter), source.index(filtered_snapshot))


if __name__ == "__main__":
    unittest.main()
