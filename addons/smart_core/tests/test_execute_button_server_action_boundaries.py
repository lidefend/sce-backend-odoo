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


class RelationActionOriginTest(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / 'core/relation_action_authority.py'
        spec = importlib.util.spec_from_file_location('relation_action_authority_test_target', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.validate = module.validate_relation_action_origin
        self.calls = []
        calls = self.calls
        class Parent:
            _fields = {'lines': types.SimpleNamespace(type='one2many', comodel_name='x.child')}
            ids = [3]
            def browse(self, record_id):
                calls.append(('browse', record_id))
                return self
            def exists(self): return self
            def check_access_rights(self, mode): calls.append(('acl', mode))
            def check_access_rule(self, mode): calls.append(('rule', mode))
            def check_field_access_rights(self, mode, names): calls.append(('fields', mode, names))
            def __getitem__(self, name): return types.SimpleNamespace(ids=self.ids)
        self.parent = Parent()
        self.origin = dict(model='x.parent', record_id=2, field='lines', action_id=41, menu_id=51)
        self.entry = dict(model='x.child', can_read=True, can_open=True)
        self.contract = {'statusContract': {'globalStatus': {'effectiveRecordCapabilities': {'read': True}}},
                         'layoutContract': {'children': [{'type': 'field', 'name': 'lines', 'fieldInfo': {'relation_entry': self.entry}}]}}

    def run_origin(self, origin=None, entry_error=''):
        return self.validate({'x.parent': self.parent}, self.origin if origin is None else origin,
                             model='x.child', record_id=3, load_contract=lambda **kw: self.contract,
                             validate_entry=lambda action, menu, model: entry_error)

    def test_current_parent_and_field_access_checked(self):
        self.run_origin()
        self.assertEqual(self.calls, [('browse', 2), ('acl', 'read'), ('rule', 'read'), ('fields', 'read', ['lines'])])

    def test_incomplete_or_mismatched_origin_is_denied(self):
        for patch in ({'record_id': 0}, {'record_id': True}, {'menu_id': 0}, {'field': 'other'}):
            with self.subTest(patch=patch), self.assertRaises(ValueError): self.run_origin({**self.origin, **patch})
        with self.assertRaisesRegex(ValueError, 'ENTRY_DENIED'): self.run_origin(entry_error='DENIED')
        self.parent._fields = {'lines': types.SimpleNamespace(type='char', comodel_name='x.child')}
        with self.assertRaisesRegex(ValueError, 'FIELD_MISMATCH'): self.run_origin()

    def test_removed_link_is_not_an_execution_authority(self):
        self.parent.ids = [99]
        with self.assertRaisesRegex(ValueError, 'RECORD_MISMATCH'): self.run_origin()

    def test_revoked_acl_or_open_contract_is_denied(self):
        self.entry['can_open'] = False
        with self.assertRaisesRegex(ValueError, 'OPEN_NOT_AUTHORIZED'): self.run_origin()
        self.entry['can_open'] = True
        self.parent.check_access_rule = lambda _mode: (_ for _ in ()).throw(PermissionError('revoked'))
        with self.assertRaises(PermissionError): self.run_origin()

    def test_hidden_or_nested_occurrence_does_not_grant_access(self):
        node = self.contract['layoutContract']['children'][0]
        node['modifiers'] = {'invisible': True}
        with self.assertRaisesRegex(ValueError, 'OPEN_NOT_AUTHORIZED'): self.run_origin()
        node.pop('modifiers')
        self.contract['layoutContract'] = {'type': 'field', 'name': 'other', 'children': [node]}
        with self.assertRaisesRegex(ValueError, 'OPEN_NOT_AUTHORIZED'): self.run_origin()


    def test_handler_uses_delivered_entry_and_retains_child_action_verdict(self):
        from unittest.mock import patch
        module = _load_handler()
        child_contract = _authorized_contract()
        handler = _authority_handler(module, child_contract)
        handler.env = {'x.parent': self.parent}
        handler.payload['meta'] = {'relation_origin': self.origin}
        handler._load_current_action_contract = lambda **kw: self.contract if kw['model'] == 'x.parent' else child_contract
        result = {'ok': True, 'data': {'allowed': True, 'action_id': 41, 'menu_id': 51, 'model': 'x.parent'}}
        route_module = types.ModuleType('odoo.addons.smart_core.handlers.route_authority_validate')
        route_module.RouteAuthorityValidateHandler = lambda *args, **kwargs: types.SimpleNamespace(handle=lambda: result)
        def authorize():
            return handler._authorize_contract_action(_authority_button(), model='x.child', record_id=3,
                                                      method_name='action_confirm', button_type='object')
        with patch.dict(sys.modules, {route_module.__name__: route_module}):
            authorize()
            for key, value in (('allowed', False), ('menu_id', 99), ('model', 'x.other'), ('action_id', 99)):
                original = result['data'][key]
                result['data'][key] = value
                with self.subTest(key=key), self.assertRaisesRegex(module.AccessError, 'ENTRY_DENIED'): authorize()
                result['data'][key] = original
            child_contract['actionContract']['actionRuleList'][0]['entitlementEvaluated'] = False
            with self.assertRaises(module.AccessError): authorize()


class WorkItemActionOriginTest(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / 'core/work_item_action_authority.py'
        spec = importlib.util.spec_from_file_location('work_item_authority_test_target', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.validate = module.validate_work_item_action_origin

    def run_origin(self, origin, authorize):
        return self.validate(origin, model='x.record', record_id=7, method_name='validate_tier', authorize=authorize)

    def test_valid_origin_rechecks_exact_target_each_time(self):
        calls = []
        def authorize(origin, **target):
            calls.append((origin, target))
            return len(calls) == 1
        self.run_origin({'source': 'review', 'id': 3}, authorize)
        with self.assertRaisesRegex(ValueError, 'NOT_AUTHORIZED'):
            self.run_origin({'source': 'review', 'id': 3}, authorize)
        self.assertEqual(calls[0][1], {'model': 'x.record', 'record_id': 7, 'method_name': 'validate_tier'})

    def test_malformed_origin_never_reaches_provider(self):
        for origin in (None, {}, {'source': 'review', 'id': True}, {'source': 'review', 'id': '3'},
                       {'source': '', 'id': 3}, {'source': 'review', 'id': -1}, {'source': 'review', 'id': 3, 'allowed': True}):
            with self.subTest(origin=origin), self.assertRaisesRegex(ValueError, 'ORIGIN_INVALID'):
                self.run_origin(origin, lambda *a, **kw: self.fail('must not call provider'))

    def test_only_explicit_provider_authority_is_accepted(self):
        for response in (None, False, 1, 'true', {'allowed': True}):
            with self.subTest(response=response), self.assertRaisesRegex(ValueError, 'NOT_AUTHORIZED'):
                self.run_origin({'source': 'review', 'id': 3}, lambda *a, **kw: response)

    def test_missing_target_cannot_be_authorized_by_provider(self):
        for model, record_id in (('', 7), ('x.record', 0), ('x.record', True)):
            with self.assertRaisesRegex(ValueError, 'TARGET_INVALID'):
                self.validate({'source': 'review', 'id': 3}, model=model, record_id=record_id,
                              method_name=None, authorize=lambda *a, **kw: True)

    def test_contract_cannot_forge_validated_access_level(self):
        module = _load_handler()
        model = _ButtonModel()
        handler = module.ExecuteButtonHandler(env=_Env({'x.model': model}), payload={
            'params': {'model': 'x.model', 'record_id': 3, 'button': _authority_button()},
            'meta': {'action_id': 41, 'menu_id': 51, 'record_access_mode': 'read'},
        })
        contract = _authorized_contract()
        contract['actionContract']['actionRuleList'][0]['_validated_work_item_access_mode'] = 'read'
        handler._load_current_action_contract = lambda **kw: contract
        result = handler.handle()
        self.assertTrue(result['ok'])
        self.assertEqual(model.access_modes, ['write'])

    def test_record_access_level_must_come_from_exact_backend_grant(self):
        for mode in ('read', 'write'):
            self.assertEqual(self.run_origin({'source': 'review', 'id': 3},
                lambda *a, **kw: {'allowed': True, 'record_access_mode': mode}), mode)
        self.assertEqual(self.run_origin({'source': 'review', 'id': 3}, lambda *a, **kw: True), 'write')
        for grant in ({'allowed': True, 'record_access_mode': 'sudo'},
                      {'allowed': 1, 'record_access_mode': 'read'},
                      {'allowed': True, 'record_access_mode': 'read', 'skip_acl': True}):
            with self.assertRaisesRegex(ValueError, 'NOT_AUTHORIZED'):
                self.run_origin({'source': 'review', 'id': 3}, lambda *a, **kw: grant)


class ReviewWorkItemOriginTest(unittest.TestCase):
    def setUp(self):
        import ast
        path = Path(__file__).resolve().parents[2] / 'smart_construction_core/services/review_work_item_service.py'
        function = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == 'authorize_review_origin')
        self.scope_allowed = True
        namespace = {'record_in_business_scope': lambda *a: (self.scope_allowed, {})}
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec'), namespace)
        self.authorize = namespace['authorize_review_origin']
        self.review = types.SimpleNamespace(id=3, model='x.record', res_id=7, status='pending', reviewer_ids=types.SimpleNamespace(ids=[34]))
        self.review.exists = lambda: self.review
        company = object()
        self.access = []
        self.record = types.SimpleNamespace(_fields={'company_id': True, 'review_ids': True}, company_id=company,
            review_ids=types.SimpleNamespace(ids=[3]), can_review=True,
            check_access_rights=lambda mode: self.access.append(('acl', mode)),
            check_access_rule=lambda mode: self.access.append(('rule', mode)))
        self.record.exists = lambda: self.record
        review, record = self.review, self.record
        class Env:
            uid = 34
            context = {}
            def __contains__(self, name): return name == 'x.record'
            def __getitem__(self, name):
                target = review if name == 'tier.review' else record
                model = types.SimpleNamespace(browse=lambda _id: target)
                model.sudo = lambda: model
                return model
        self.env = Env()
        self.env.company = company

    def check_origin(self, **kwargs):
        return self.authorize(self.env, {'source': 'tier.review', 'id': 3}, model='x.record', record_id=7, **kwargs)

    def test_assigned_review_requires_record_acl_rules_and_current_scope(self):
        self.assertIs(self.check_origin(method_name='validate_tier'), True)
        self.assertEqual(self.access, [('acl', 'read'), ('rule', 'read')])
        self.scope_allowed = False
        self.assertIs(self.check_origin(method_name='validate_tier'), False)

    def test_wrong_actor_or_expired_review_is_denied(self):
        self.env.uid = 35
        self.assertIs(self.check_origin(), False)
        self.env.uid = 34
        self.review.status = 'approved'
        self.assertIs(self.check_origin(), False)

    def test_wrong_target_or_company_is_denied(self):
        self.review.res_id = 8
        self.assertIs(self.check_origin(), False)
        self.review.res_id = 7
        self.record.company_id = object()
        self.assertIs(self.check_origin(), False)

    def test_review_origin_cannot_authorize_other_business_actions(self):
        self.assertIs(self.check_origin(method_name='action_done'), False)
        self.assertIs(self.check_origin(method_name='reject_tier'), True)

    def test_current_review_membership_and_can_review_are_required(self):
        self.record.can_review = False
        self.assertIs(self.check_origin(), False)
        self.record.can_review = True
        self.record.review_ids.ids = [4]
        self.assertIs(self.check_origin(), False)


if __name__ == "__main__":
    unittest.main()
