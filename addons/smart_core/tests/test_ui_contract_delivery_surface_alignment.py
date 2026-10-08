# -*- coding: utf-8 -*-
"""Unit guard for the ui.contract delivery-surface declaration.

The handler resolves the requested contract surface for its meta envelope. The
delivery data must be shaped with that same declared surface; a fallback that
dropped it normalized every payload to ``user`` and mislabelled hud/native
delivery data while the meta envelope stayed correct.

This test locks the declared-consumption behaviour at the P0 producer boundary.
End-to-end alignment is proven by the runtime guard
``verify.contract.surface_mapping_guard``; this unit only proves that the
resolved surface is actually forwarded, and that a hardcoded ``user`` would be
detected (the control case below is the negative baseline).
"""
from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path


class _BaseIntentHandler:
    def __init__(self, env=None, request=None, context=None, payload=None):
        self.env = env
        self.request = request
        self.context = context or {}
        self.payload = payload or {}
        self.params = self.payload.get("params") if isinstance(self.payload, dict) else {}
        if not isinstance(self.params, dict):
            self.params = {}


def _install_module(name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _load_handler(calls):
    root = Path(__file__).resolve().parents[1]

    api_mod = types.SimpleNamespace(Environment=lambda cr, uid, ctx: None)
    _install_module("odoo", api=api_mod, SUPERUSER_ID=1)
    _install_module("odoo.tools")
    _install_module("odoo.tools.safe_eval", safe_eval=lambda value: value)

    addons_mod = _install_module("odoo.addons")
    smart_core_mod = _install_module("odoo.addons.smart_core")
    handlers_mod = _install_module("odoo.addons.smart_core.handlers")
    core_mod = _install_module("odoo.addons.smart_core.core")
    app_config_mod = _install_module("odoo.addons.smart_core.app_config_engine")
    services_mod = _install_module("odoo.addons.smart_core.app_config_engine.services")
    dispatchers_mod = _install_module("odoo.addons.smart_core.app_config_engine.services.dispatchers")
    utils_mod = _install_module("odoo.addons.smart_core.utils")

    addons_mod.__path__ = []
    smart_core_mod.__path__ = [str(root)]
    handlers_mod.__path__ = [str(root / "handlers")]
    core_mod.__path__ = [str(root / "core")]
    app_config_mod.__path__ = [str(root / "app_config_engine")]
    services_mod.__path__ = [str(root / "app_config_engine" / "services")]
    dispatchers_mod.__path__ = [str(root / "app_config_engine" / "services" / "dispatchers")]
    utils_mod.__path__ = [str(root / "utils")]

    base_mod = _install_module("odoo.addons.smart_core.core.base_handler")
    base_mod.BaseIntentHandler = _BaseIntentHandler

    result_mod = _install_module("odoo.addons.smart_core.core.intent_execution_result")
    result_mod.IntentExecutionResult = type("IntentExecutionResult", (), {})

    projection_mod = _install_module("odoo.addons.smart_core.core.native_view_contract_projection")
    projection_mod.inject_primary_view_projection = lambda data, requested_view_type=None: data

    contract_service_mod = _install_module(
        "odoo.addons.smart_core.app_config_engine.services.contract_service"
    )
    class _ContractService:
        def __init__(self, env):
            self.env = env

    contract_service_mod.ContractService = _ContractService
    nav_mod = _install_module(
        "odoo.addons.smart_core.app_config_engine.services.dispatchers.nav_dispatcher"
    )
    nav_mod.NavDispatcher = type("NavDispatcher", (), {})
    menu_mod = _install_module(
        "odoo.addons.smart_core.app_config_engine.services.dispatchers.menu_dispatcher"
    )
    menu_mod.MenuDispatcher = type("MenuDispatcher", (), {})
    action_mod = _install_module(
        "odoo.addons.smart_core.app_config_engine.services.dispatchers.action_dispatcher"
    )
    action_mod.ActionDispatcher = type("ActionDispatcher", (), {})

    def _recording_governance(data, mode, **kwargs):
        calls.append({"contract_mode": mode, **kwargs})
        return dict(data)

    governance_mod = _install_module("odoo.addons.smart_core.utils.contract_governance")
    governance_mod.apply_contract_governance = _recording_governance
    governance_mod.resolve_contract_mode = lambda params: "user"
    governance_mod.resolve_contract_surface = lambda params, contract_mode=None: "user"

    request_params_name = "odoo.addons.smart_core.core.request_params"
    sys.modules.pop(request_params_name, None)
    request_params_spec = importlib.util.spec_from_file_location(
        request_params_name, root / "core" / "request_params.py"
    )
    request_params_module = importlib.util.module_from_spec(request_params_spec)
    sys.modules[request_params_name] = request_params_module
    request_params_spec.loader.exec_module(request_params_module)

    module_name = "odoo.addons.smart_core.handlers.ui_contract"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, root / "handlers" / "ui_contract.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class TestUiContractDeliverySurfaceAlignment(unittest.TestCase):
    def setUp(self):
        self.calls: list[dict] = []
        module = _load_handler(self.calls)
        env = types.SimpleNamespace(context={}, user=types.SimpleNamespace(lang=""))
        self.handler = module.UiContractHandler(env=env, context={})

    def _shape(self, contract_surface: str) -> dict:
        self.calls.clear()
        self.handler._shape_delivery_data(
            {"subject": "model"},
            payload={},
            contract_mode="user",
            contract_surface=contract_surface,
            source_mode="",
        )
        self.assertEqual(len(self.calls), 1, "delivery shaping must call the governance producer once")
        return self.calls[0]

    def test_declared_surface_is_forwarded_to_the_producer(self):
        for surface in ("user", "hud", "native"):
            with self.subTest(surface=surface):
                call = self._shape(surface)
                self.assertEqual(call.get("contract_surface"), surface)
                self.assertFalse(call.get("inject_contract_mode"))

    def test_control_user_surface_still_resolves_to_user(self):
        # Negative baseline: a hardcoded "user" would pass this control and fail
        # the hud/native cases above, so the pair detects the mislabelling.
        call = self._shape("user")
        self.assertEqual(call.get("contract_surface"), "user")


if __name__ == "__main__":
    unittest.main()
