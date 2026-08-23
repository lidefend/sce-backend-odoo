# -*- coding: utf-8 -*-
import importlib.util
import sys
import types
import unittest
from pathlib import Path


class _BaseIntentHandler:
    def __init__(self, env=None, su_env=None, request=None, params=None, context=None, payload=None):
        self.env = env
        self.su_env = su_env or env
        self.request = request
        self.payload = payload or ({"params": params or {}} if params is not None else {})
        self.params = self.payload.get("params", self.payload) if isinstance(self.payload, dict) else {}
        self.context = context or {}


class _Action:
    _name = "ir.actions.server"
    id = 7

    def __init__(self, model, result=None):
        self.model_id = types.SimpleNamespace(model=model)
        self.run_calls = 0
        self.result = result if result is not None else {}

    def exists(self):
        return self

    def sudo(self):
        raise AssertionError("server action must not be escalated with sudo")

    def check_access_rights(self, mode):
        return True

    def check_access_rule(self, mode):
        return True

    def with_context(self, context):
        return self

    def run(self):
        self.run_calls += 1
        return self.result


class _ActionModel:
    def __init__(self, action):
        self.action = action

    def sudo(self):
        raise AssertionError("server action model must not be escalated with sudo")

    def browse(self, action_id):
        return self.action


class _Env(dict):
    user = types.SimpleNamespace(groups_id=set())


def _authorized_contract(*, disabled=False, duplicate=False, method="action_confirm", button_type="object"):
    backend_identity = "server_action:7" if button_type == "server" else f"button:{button_type}:{method}"
    rule = {
        "actionId": "action.confirm",
        "actionKey": "confirm",
        "backendIdentity": backend_identity,
        "sourceWidgetId": "page.header",
        "button": {
            "name": method,
            "type": button_type,
            **({"server_action_id": 7} if button_type == "server" else {}),
        },
        "allowed": True,
        "enabled": not disabled,
        "disabled": disabled,
        "entitlementEvaluated": True,
    }
    rules = [rule, dict(rule)] if duplicate else [rule]
    return {
        "actionContract": {"actionRuleList": rules},
        "statusContract": {"buttonStatus": [{
            "btnId": "btn.confirm",
            "backendIdentity": rule["backendIdentity"],
            "visible": True,
            "disabled": disabled,
            **({"reasonCode": "ACTION_BLOCKED"} if disabled else {}),
        }]},
    }


def _authority_button(method="action_confirm", button_type="object"):
    backend_identity = "server_action:7" if button_type == "server" else f"button:{button_type}:{method}"
    return {
        "name": method,
        "type": button_type,
        "action_id": "action.confirm",
        "backend_identity": backend_identity,
        "source_widget_id": "page.header",
        **({"server_action_id": 7} if button_type == "server" else {}),
    }


def _authority_handler(module, contract):
    handler = module.ExecuteButtonHandler(
        env=_Env({}),
        payload={"params": {}, "meta": {"action_id": 41, "menu_id": 51}},
        context={},
    )
    handler._load_current_action_contract = lambda **_kwargs: contract
    return handler


class _Recordset:
    id = 3

    def exists(self):
        return self

    def __iter__(self):
        return iter([types.SimpleNamespace(id=3)])

    def check_access_rule(self, mode):
        return True

    def with_context(self, context):
        return self


class _ButtonModel:
    def check_access_rights(self, mode):
        return True

    def browse(self, ids):
        return _Recordset()


def _load_handler():
    root = Path(__file__).resolve().parents[1]
    odoo_mod = types.ModuleType("odoo")
    odoo_mod.fields = types.SimpleNamespace(Date=types.SimpleNamespace(context_today=lambda user: "2026-05-07"))
    exc_mod = types.ModuleType("odoo.exceptions")
    exc_mod.AccessError = type("AccessError", (Exception,), {})
    exc_mod.UserError = type("UserError", (Exception,), {})
    odoo_mod.exceptions = exc_mod

    addons_mod = types.ModuleType("odoo.addons")
    smart_core_mod = types.ModuleType("odoo.addons.smart_core")
    handlers_mod = types.ModuleType("odoo.addons.smart_core.handlers")
    core_mod = types.ModuleType("odoo.addons.smart_core.core")
    utils_mod = types.ModuleType("odoo.addons.smart_core.utils")
    smart_core_mod.__path__ = [str(root)]
    handlers_mod.__path__ = [str(root / "handlers")]
    core_mod.__path__ = [str(root / "core")]
    utils_mod.__path__ = [str(root / "utils")]
    base_mod = types.ModuleType("odoo.addons.smart_core.core.base_handler")
    base_mod.BaseIntentHandler = _BaseIntentHandler
    project_mod = types.ModuleType("odoo.addons.smart_core.core.project_context")
    project_mod.record_scope_denied_response = lambda meta, message="": {"ok": False, "meta": meta, "message": message}
    project_mod.project_scope_denied_response = lambda meta: {"ok": False, "meta": meta}
    project_mod.record_in_business_scope = lambda model, record_id, params=None, context=None: (True, {"applied": False})
    project_mod.record_in_project_scope = lambda model, record_id, project_id: (True, {"applied": False})
    project_mod.selected_record_context_id_from_context = lambda params, context: None
    project_mod.selected_project_id_from_context = lambda params, context: None

    sys.modules.update(
        {
            "odoo": odoo_mod,
            "odoo.exceptions": exc_mod,
            "odoo.addons": addons_mod,
            "odoo.addons.smart_core": smart_core_mod,
            "odoo.addons.smart_core.handlers": handlers_mod,
            "odoo.addons.smart_core.core": core_mod,
            "odoo.addons.smart_core.utils": utils_mod,
            "odoo.addons.smart_core.core.base_handler": base_mod,
            "odoo.addons.smart_core.core.project_context": project_mod,
        }
    )

    reason_name = "odoo.addons.smart_core.utils.reason_codes"
    sys.modules.pop(reason_name, None)
    reason_spec = importlib.util.spec_from_file_location(reason_name, root / "utils" / "reason_codes.py")
    reason_module = importlib.util.module_from_spec(reason_spec)
    sys.modules[reason_name] = reason_module
    reason_spec.loader.exec_module(reason_module)

    module_name = "odoo.addons.smart_core.handlers.execute_button"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, root / "handlers" / "execute_button.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class TestExecuteButtonServerActionBoundaries(unittest.TestCase):
    def test_server_action_model_must_match_active_model(self):
        module = _load_handler()
        action = _Action("other.model")
        env = _Env({"ir.actions.server": _ActionModel(action)})
        handler = module.ExecuteButtonHandler(env=env, context={})

        result = handler._run_server_action({"server_action_id": 7}, model="x.model", res_ids=[1])

        self.assertIsNone(result)
        self.assertEqual(action.run_calls, 0)

    def test_matching_server_action_can_run(self):
        module = _load_handler()
        action = _Action("x.model")
        env = _Env({"ir.actions.server": _ActionModel(action)})
        handler = module.ExecuteButtonHandler(env=env, context={})

        result = handler._run_server_action({"server_action_id": 7}, model="x.model", res_ids=[1])

        self.assertTrue(result["ok"])
        self.assertEqual(action.run_calls, 1)

    def test_contract_action_authority_requires_exact_identity_and_status(self):
        module = _load_handler()
        handler = _authority_handler(module, _authorized_contract())

        handler._authorize_contract_action(
            _authority_button(),
            model="x.model",
            record_id=3,
            method_name="action_confirm",
            button_type="object",
        )

    def test_contract_action_authority_rejects_missing_identity(self):
        module = _load_handler()
        handler = _authority_handler(module, _authorized_contract())
        button = _authority_button()
        button.pop("backend_identity")

        with self.assertRaisesRegex(module.AccessError, "ACTION_CONTRACT_AUTHORITY_MISSING"):
            handler._authorize_contract_action(
                button,
                model="x.model",
                record_id=3,
                method_name="action_confirm",
                button_type="object",
            )

    def test_contract_action_authority_rejects_forged_method(self):
        module = _load_handler()
        handler = _authority_handler(module, _authorized_contract())

        with self.assertRaisesRegex(module.AccessError, "ACTION_CONTRACT_BUTTON_MISMATCH"):
            handler._authorize_contract_action(
                _authority_button(),
                model="x.model",
                record_id=3,
                method_name="unlink",
                button_type="object",
            )

    def test_contract_action_authority_rejects_ambiguous_identity(self):
        module = _load_handler()
        handler = _authority_handler(module, _authorized_contract(duplicate=True))

        with self.assertRaisesRegex(module.AccessError, "ACTION_CONTRACT_AUTHORITY_AMBIGUOUS"):
            handler._authorize_contract_action(
                _authority_button(),
                model="x.model",
                record_id=3,
                method_name="action_confirm",
                button_type="object",
            )

    def test_contract_action_authority_rejects_disabled_action_with_reason(self):
        module = _load_handler()
        handler = _authority_handler(module, _authorized_contract(disabled=True))

        with self.assertRaisesRegex(module.AccessError, "ACTION_CONTRACT_NOT_AUTHORIZED"):
            handler._authorize_contract_action(
                _authority_button(),
                model="x.model",
                record_id=3,
                method_name="action_confirm",
                button_type="object",
            )

    def test_contract_action_authority_rejects_forged_server_action_id(self):
        module = _load_handler()
        handler = _authority_handler(module, _authorized_contract(button_type="server"))
        button = _authority_button(button_type="server")
        button["server_action_id"] = 8

        with self.assertRaisesRegex(module.AccessError, "ACTION_CONTRACT_SERVER_ACTION_MISMATCH"):
            handler._authorize_contract_action(
                button,
                model="x.model",
                record_id=3,
                method_name="action_confirm",
                button_type="server",
            )

    def test_server_action_navigation_result_has_entry_target(self):
        module = _load_handler()
        action = _Action(
            "x.model",
            result={
                "type": "ir.actions.act_window",
                "id": 44,
                "menu_id": 389,
                "res_model": "x.model",
                "view_mode": "tree,form",
            },
        )
        env = _Env({"ir.actions.server": _ActionModel(action)})
        handler = module.ExecuteButtonHandler(env=env, context={})

        result = handler._run_server_action({"server_action_id": 7}, model="x.model", res_ids=[1])

        self.assertTrue(result["ok"])
        raw_action = result["data"]["result"]["raw_action"]
        self.assertEqual(raw_action["entry_target"]["type"], "compatibility")
        self.assertEqual(raw_action["entry_target"]["route"], "/a/44")
        self.assertEqual(raw_action["entry_target"]["compatibility_refs"]["menu_id"], 389)
        self.assertEqual(result["data"]["result"]["entry_target"], raw_action["entry_target"])
        self.assertEqual(result["data"]["effect"]["target"]["kind"], "entry_target")

    def test_invalid_record_id_returns_bad_request(self):
        module = _load_handler()
        handler = module.ExecuteButtonHandler(
            env=_Env({}),
            params={"model": "x.model", "record_id": ["bad"], "button": {"name": "action_confirm"}},
            context={"trace_id": "trace"},
        )

        result = handler.handle()

        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], 400)
        self.assertEqual(result["error"]["message"], "record_id 无效")
        self.assertEqual(result["meta"]["trace_id"], "trace")

    def test_legacy_server_action_request_without_contract_authority_is_denied(self):
        module = _load_handler()
        handler = module.ExecuteButtonHandler(
            env=_Env({"x.model": _ButtonModel()}),
            params={
                "model": "x.model",
                "record_id": 3,
                "button": {"name": "missing_method", "server_action_id": "bad"},
            },
            context={"trace_id": "trace"},
        )

        result = handler.handle()

        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], 403)
        self.assertEqual(result["error"]["message"], "ACTION_CONTRACT_AUTHORITY_MISSING")


if __name__ == "__main__":
    unittest.main()
