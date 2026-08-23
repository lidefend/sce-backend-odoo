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


class _WindowAction:
    _name = "ir.actions.act_window"
    id = 338

    def __init__(self):
        self.read_calls = 0
        self.execution_context = {}

    def exists(self):
        return self

    def check_access_rights(self, mode):
        if mode != "read":
            raise AssertionError("window actions must use current-user read authority")

    def check_access_rule(self, mode):
        if mode != "read":
            raise AssertionError("window actions must use current-user read authority")

    def with_context(self, context):
        self.execution_context = dict(context)
        return self

    def read(self):
        self.read_calls += 1
        return [{
            "id": self.id,
            "type": "ir.actions.act_window",
            "name": "Share",
            "res_model": "x.share.wizard",
            "view_mode": "form",
            "target": "new",
        }]


class _WindowActionModel:
    def __init__(self, action):
        self.action = action

    def sudo(self):
        raise AssertionError("window action must not be escalated with sudo")

    def browse(self, action_id):
        return self.action if action_id == self.action.id else None


class _Env(dict):
    user = types.SimpleNamespace(groups_id=set())


def _authorized_contract(*, disabled=False, duplicate=False, method="action_confirm", button_type="object"):
    is_server = button_type in {"server", "server_action"}
    is_window = button_type == "action"
    backend_identity = (
        "server_action:7"
        if is_server
        else "window_action:338"
        if is_window
        else f"button:{button_type}:{method}"
    )
    rule = {
        "actionId": "action.confirm",
        "actionKey": "confirm",
        "backendIdentity": backend_identity,
        "sourceWidgetId": "page.header",
        "button": {
            "name": method,
            "type": button_type,
            **({"server_action_id": 7} if is_server else {}),
        },
        **({
            "target": {
                "action_id": 338,
                "xml_id": "project.share_action",
                "context_raw": "{'dialog_size': 'medium'}",
            },
        } if is_window else {}),
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
    is_server = button_type in {"server", "server_action"}
    backend_identity = (
        "server_action:7"
        if is_server
        else "window_action:338"
        if button_type == "action"
        else f"button:{button_type}:{method}"
    )
    return {
        "name": method,
        "type": button_type,
        "action_id": "action.confirm",
        "backend_identity": backend_identity,
        "source_widget_id": "page.header",
        **({"server_action_id": 7} if is_server else {}),
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

    def __init__(self):
        self.method_calls = 0

    def exists(self):
        return self

    def __iter__(self):
        return iter([types.SimpleNamespace(id=3)])

    def check_access_rule(self, mode):
        return True

    def with_context(self, context):
        return self

    def shared_action(self):
        self.method_calls += 1
        return None


class _ButtonModel:
    def __init__(self, recordset=None, readonly_methods=()):
        self.recordset = recordset or _Recordset()
        self._sc_readonly_navigation_button_methods = readonly_methods
        self.access_modes = []

    def check_access_rights(self, mode):
        self.access_modes.append(mode)
        return True

    def browse(self, ids):
        return self.recordset


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
    tools_mod = types.ModuleType("odoo.tools")
    safe_eval_mod = types.ModuleType("odoo.tools.safe_eval")
    safe_eval_mod.safe_eval = lambda expression, _globals: (
        {"dialog_size": "medium"}
        if expression == "{'dialog_size': 'medium'}"
        else {}
    )
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
            "odoo.tools": tools_mod,
            "odoo.tools.safe_eval": safe_eval_mod,
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

    def test_handle_server_action_name_collision_runs_only_server_action(self):
        module = _load_handler()
        for button_type in ("server", "server_action"):
            with self.subTest(button_type=button_type):
                action = _Action("x.model")
                recordset = _Recordset()
                button_model = _ButtonModel(recordset, readonly_methods=("shared_action",))
                env = _Env({
                    "x.model": button_model,
                    "ir.actions.server": _ActionModel(action),
                })
                handler = module.ExecuteButtonHandler(
                    env=env,
                    payload={
                        "params": {
                            "model": "x.model",
                            "record_id": 3,
                            "button": _authority_button(method="shared_action", button_type=button_type),
                        },
                        "meta": {"action_id": 41, "menu_id": 51},
                    },
                    context={"trace_id": "trace"},
                )
                handler._load_current_action_contract = lambda **_kwargs: _authorized_contract(
                    method="shared_action",
                    button_type=button_type,
                )

                result = handler.handle()

                self.assertTrue(result["ok"])
                self.assertEqual(recordset.method_calls, 0)
                self.assertEqual(action.run_calls, 1)
                self.assertEqual(button_model.access_modes, ["write"])

    def test_handle_server_action_dry_run_executes_neither_collision_target(self):
        module = _load_handler()
        action = _Action("x.model")
        recordset = _Recordset()
        env = _Env({
            "x.model": _ButtonModel(recordset),
            "ir.actions.server": _ActionModel(action),
        })
        handler = module.ExecuteButtonHandler(
            env=env,
            payload={
                "params": {
                    "model": "x.model",
                    "record_id": 3,
                    "dry_run": True,
                    "button": _authority_button(method="shared_action", button_type="server"),
                },
                "meta": {"action_id": 41, "menu_id": 51},
            },
            context={"trace_id": "trace"},
        )
        handler._load_current_action_contract = lambda **_kwargs: _authorized_contract(
            method="shared_action",
            button_type="server",
        )

        result = handler.handle()

        self.assertTrue(result["ok"])
        self.assertEqual(recordset.method_calls, 0)
        self.assertEqual(action.run_calls, 0)
        self.assertEqual(result["data"]["result"]["reason_code"], "DRY_RUN")

    def test_handle_object_action_name_collision_runs_only_model_method(self):
        module = _load_handler()
        action = _Action("x.model")
        recordset = _Recordset()
        env = _Env({
            "x.model": _ButtonModel(recordset),
            "ir.actions.server": _ActionModel(action),
        })
        handler = module.ExecuteButtonHandler(
            env=env,
            payload={
                "params": {
                    "model": "x.model",
                    "record_id": 3,
                    "button": _authority_button(method="shared_action", button_type="object"),
                },
                "meta": {"action_id": 41, "menu_id": 51},
            },
            context={"trace_id": "trace"},
        )
        handler._load_current_action_contract = lambda **_kwargs: _authorized_contract(
            method="shared_action",
            button_type="object",
        )

        result = handler.handle()

        self.assertTrue(result["ok"])
        self.assertEqual(recordset.method_calls, 1)
        self.assertEqual(action.run_calls, 0)

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

    def test_contract_window_action_authority_rejects_target_mismatch(self):
        module = _load_handler()
        contract = _authorized_contract(method="338", button_type="action")
        contract["actionContract"]["actionRuleList"][0]["target"]["action_id"] = 339
        handler = _authority_handler(module, contract)

        with self.assertRaisesRegex(module.AccessError, "ACTION_CONTRACT_WINDOW_ACTION_MISMATCH"):
            handler._authorize_contract_action(
                _authority_button(method="338", button_type="action"),
                model="x.model",
                record_id=3,
                method_name="338",
                button_type="action",
            )

    def test_handle_contract_window_action_loads_wizard_without_model_method_or_sudo(self):
        module = _load_handler()
        window_action = _WindowAction()
        recordset = _Recordset()
        button_model = _ButtonModel(recordset)
        env = _Env({
            "x.model": button_model,
            "ir.actions.act_window": _WindowActionModel(window_action),
        })
        handler = module.ExecuteButtonHandler(
            env=env,
            payload={
                "params": {
                    "model": "x.model",
                    "record_id": 3,
                    "button": _authority_button(method="338", button_type="action"),
                },
                "meta": {"action_id": 41, "menu_id": 51},
            },
            context={"trace_id": "trace"},
        )
        handler._load_current_action_contract = lambda **_kwargs: _authorized_contract(
            method="338",
            button_type="action",
        )

        result = handler.handle()

        self.assertTrue(result["ok"])
        self.assertEqual(recordset.method_calls, 0)
        self.assertEqual(button_model.access_modes, ["read"])
        self.assertEqual(window_action.read_calls, 1)
        self.assertEqual(window_action.execution_context["active_model"], "x.model")
        self.assertEqual(window_action.execution_context["active_id"], 3)
        self.assertEqual(window_action.execution_context["active_ids"], [3])
        self.assertEqual(window_action.execution_context["dialog_size"], "medium")
        raw_action = result["data"]["result"]["raw_action"]
        self.assertEqual(raw_action["entry_target"]["route"], "/f/x.share.wizard/new")
        self.assertEqual(result["data"]["effect"]["target"]["kind"], "entry_target")

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

    def test_multiple_record_ids_are_denied_before_contract_authority_is_reused(self):
        module = _load_handler()
        handler = module.ExecuteButtonHandler(
            env=_Env({"x.model": _ButtonModel()}),
            payload={
                "params": {
                    "model": "x.model",
                    "record_id": [3, 4],
                    "button": _authority_button(),
                },
                "meta": {"action_id": 41, "menu_id": 51},
            },
            context={"trace_id": "trace"},
        )
        handler._load_current_action_contract = lambda **_kwargs: self.fail(
            "multi-record requests must be rejected before one record is used as authority"
        )

        result = handler.handle()

        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], 403)
        self.assertEqual(result["error"]["message"], "ACTION_CONTRACT_SINGLE_RECORD_REQUIRED")

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
