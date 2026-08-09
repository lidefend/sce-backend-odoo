# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "addons" / "smart_core" / "delivery" / "native_config_menu_projection.py"


def _install_module(name: str, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module


def _load_module():
    for name in list(sys.modules):
        if name.startswith("odoo"):
            sys.modules.pop(name, None)
    for name in (
        "odoo",
        "odoo.addons",
        "odoo.addons.smart_core",
        "odoo.addons.smart_core.core",
        "odoo.addons.smart_core.security",
        "odoo.addons.smart_core.utils",
    ):
        _install_module(name)
    _install_module(
        "odoo.addons.smart_core.core.source_authority",
        build_source_authority_contract=lambda **kwargs: dict(kwargs),
    )
    _install_module(
        "odoo.addons.smart_core.security.platform_admin",
        can_manage_system_configuration=lambda user: False,
    )
    _install_module(
        "odoo.addons.smart_core.utils.backend_contract_boundaries",
        MENU_CONFIG_POLICY_MODEL="ui.menu.config.policy",
    )
    _install_module(
        "odoo.addons.smart_core.utils.extension_hooks",
        call_extension_hook_first=lambda *args, **kwargs: None,
    )
    spec = importlib.util.spec_from_file_location("native_config_menu_projection_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class _RestrictedAction:
    id = 91

    def __init__(self):
        self.sudo_called = False

    def sudo(self):
        self.sudo_called = True
        return _ProjectedAction()


class _ProjectedAction:
    id = 91
    view_mode = ""
    res_model = ""

    def get_external_id(self):
        return {self.id: "smart_core.action_config_client"}


class _Menu:
    id = 17

    def __init__(self, action):
        self.action = action

    def get_external_id(self):
        return {self.id: "smart_core.menu_config_client"}


class NativeConfigMenuProjectionTests(unittest.TestCase):
    def test_action_metadata_uses_sudo_after_menu_visibility_projection(self):
        module = _load_module()
        restricted_action = _RestrictedAction()

        payload = module._action_payload(_Menu(restricted_action))

        self.assertTrue(restricted_action.sudo_called)
        self.assertEqual(payload["action_id"], 91)
        self.assertEqual(payload["action_xmlid"], "smart_core.action_config_client")


if __name__ == "__main__":
    unittest.main()
