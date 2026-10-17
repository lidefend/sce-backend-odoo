# -*- coding: utf-8 -*-
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


def _load_handler():
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
    contract_service_mod.ContractService = type("ContractService", (), {})
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

    governance_mod = _install_module("odoo.addons.smart_core.utils.contract_governance")
    governance_mod.apply_contract_governance = lambda data, mode, inject_contract_mode=False: data
    governance_mod.resolve_contract_mode = lambda params: "user"
    governance_mod.resolve_contract_surface = lambda params, contract_mode=None: "scene"

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


class TestUiContractIdBoundaries(unittest.TestCase):
    def setUp(self):
        module = _load_handler()
        env = types.SimpleNamespace(context={}, user=types.SimpleNamespace(lang=""))
        self.handler = module.UiContractHandler(env=env, context={})

    def test_internal_preference_projection_returns_only_profile_and_restores_purpose(self):
        result_module = sys.modules['odoo.addons.smart_core.core.intent_execution_result']
        result_module.adapt_handler_result = lambda value: value
        def handle(payload):
            self.assertTrue(self.handler._list_preference_projection)
            return {'ok': True, 'data': {'list_profile': {'columns': ['name']}, 'partial_page': True}}
        self.handler.handle = handle
        self.assertEqual(self.handler.read_list_preference_profile({}), {'columns': ['name']})
        self.assertFalse(self.handler._list_preference_projection)
        def fail(payload):
            raise ValueError('failed projection')
        self.handler.handle = fail
        with self.assertRaises(ValueError):
            self.handler.read_list_preference_profile({})
        self.assertFalse(self.handler._list_preference_projection)

    def test_external_payload_or_context_cannot_select_narrow_projection(self):
        module = sys.modules['odoo.addons.smart_core.handlers.ui_contract']
        self.handler.env.cr = object()
        self.handler.env.user.id = 7
        module.ActionDispatcher = lambda env, su, **kwargs: kwargs
        self.handler.payload = {'include_relation_search_dialogs': False, '_list_preference_projection': True}
        self.assertEqual(self.handler._build_dispatcher({'include_relation_search_dialogs': False, '_list_preference_projection': True}), {})
        self.handler._list_preference_projection = True
        self.assertEqual(self.handler._build_dispatcher({}), {'include_relation_search_dialogs': False})

    def test_action_open_rejects_invalid_action_id(self):
        result = self.handler._op_action_open({"action_id": "bad"}, {})

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], 400)
        self.assertIn("action_id", result["error"]["message"])

    def test_action_open_rejects_invalid_record_id(self):
        result = self.handler._op_action_open({"action_id": "7", "record_id": "bad"}, {})

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], 400)
        self.assertIn("record_id", result["error"]["message"])

    def test_action_open_rejects_invalid_view_id(self):
        result = self.handler._op_action_open({"action_id": "7", "view_id": "bad"}, {})

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], 400)
        self.assertIn("view_id", result["error"]["message"])

    def test_action_open_forwards_explicit_list_view_to_first_dispatch(self):
        from unittest.mock import Mock
        dispatcher = Mock()
        dispatcher.dispatch.return_value = ({"head": {}, "views": {"tree": {"columns": ["name"]}}}, {})
        self.handler._build_dispatcher = lambda ctx: dispatcher
        self.handler._finalize_projected_contract = lambda **kwargs: kwargs["data"]
        for requested, expected in (("1700", 1700), (None, None)):
            params = {"action_id": "7", "view_type": "tree", "menu_id": 71,
                      "sceneKey": "declared_scene", "menuXmlid": "example.menu", "arbitrary": "not forwarded"}
            if requested:
                params["view_id"] = requested
            data = self.handler._op_action_open(params, {})
            self.assertEqual(data["scene_key"], "declared_scene")
            self.assertEqual(data["head"]["scene_key"], "declared_scene")
            self.assertEqual(data["menu_xmlid"], "example.menu")
            self.assertEqual(data["head"]["menu_xmlid"], "example.menu")
            self.assertNotIn("arbitrary", data)
            forwarded = dispatcher.dispatch.call_args.args[0]
            self.assertEqual(forwarded.get("view_id"), expected)
            self.assertEqual(forwarded["subject"], "action")
            self.assertEqual(forwarded["action_id"], 7)
            self.assertEqual(forwarded["view_type"], "tree")
            self.assertEqual(forwarded["menu_id"], 71)
        self.assertEqual(dispatcher.dispatch.call_count, 2)

    def test_action_open_forwards_explicit_form_view_id(self):
        action = types.SimpleNamespace(
            id=7,
            res_model="x.model",
            context="{}",
            exists=lambda: True,
        )

        class _ActionModel:
            def sudo(self):
                return self

            def with_context(self, _context):
                return self

            def browse(self, _action_id):
                return action

        class _Env(dict):
            context = {}
            user = types.SimpleNamespace(lang="")

        self.handler.env = _Env({"ir.actions.act_window": _ActionModel()})
        captured = {}

        def _dispatch_model_contract(**kwargs):
            captured.update(kwargs)
            return {}, {}

        self.handler._dispatch_model_contract = _dispatch_model_contract
        self.handler._finalize_projected_contract = lambda **kwargs: kwargs["data"]

        self.handler._op_action_open(
            {
                "action_id": "7",
                "record_id": "11",
                "view_type": "form",
                "view_id": "1700",
                "render_profile": "readonly",
            },
            {},
        )

        self.assertEqual(captured["model"], "x.model")
        self.assertEqual(captured["view_type"], "form")
        self.assertEqual(captured["view_id"], 1700)
        self.assertEqual(captured["action_id"], 7)
        self.assertEqual(captured["record_id"], 11)
        self.assertEqual(captured["render_profile"], "readonly")

    def test_model_rejects_invalid_optional_ids(self):
        self.handler.env = {"x.model": object()}

        for field in ("action_id", "menu_id", "record_id"):
            with self.subTest(field=field):
                result = self.handler._op_model({"model": "x.model", field: "bad"}, {})
                self.assertFalse(result["ok"])
                self.assertEqual(result["error"]["code"], 400)
                self.assertIn(field, result["error"]["message"])

    def test_handle_rejects_invalid_company_id(self):
        result = self.handler.handle({"params": {"op": "model", "model": "x.model", "company_id": "bad"}})

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], 400)
        self.assertEqual(result["error"]["message"], "company_id 无效")


if __name__ == "__main__":
    unittest.main()
