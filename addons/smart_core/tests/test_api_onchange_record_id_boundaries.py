# -*- coding: utf-8 -*-
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class _BaseIntentHandler:
    def __init__(self, env=None, params=None, payload=None, context=None):
        self.env = env
        self.params = params or {}
        self.payload = payload or {}
        self.context = context or {}


class _Model:
    _fields = {}

    def with_context(self, context):
        return self

    def check_access_rights(self, mode):
        return True

    def check_field_access_rights(self, mode, names):
        return names

    def get_view(self, view_id=None, view_type="form"):
        return {"arch": "<form>" + "".join('<field name="%s"/>' % name for name in self._fields) + "</form>"}


class _Field:
    def __init__(self, field_type="", comodel_name=""):
        self.type = field_type
        self.comodel_name = comodel_name


class _OnchangeModel(_Model):
    _fields = {"line_ids": _Field("one2many", "x.line")}
    _onchange_methods = {"line_ids": True}

    def onchange(self, values, changed_fields, field_onchange):
        return {
            "line_patches": [
                {
                    "field": "line_ids",
                    "row_id": "bad",
                    "patch": {"name": "A"},
                }
            ]
        }


class _LineModel(_Model):
    _fields = {"name": _Field("char")}


def _manual_menu_onchange(record):
    return {"value": {"original_label": "基础设置", "preview_summary": "保存后刷新页面生效"}}


class _ManualOnchangeModel(_Model):
    _fields = {"menu_id": _Field("many2one", "ir.ui.menu"), "original_label": _Field("char"), "preview_summary": _Field("char")}
    _onchange_methods = {"menu_id": [_manual_menu_onchange]}

    def onchange(self, values, changed_fields, field_onchange):
        return {"value": {"original_label": "基础设置", "preview_summary": "保存后刷新页面生效"}}

    def new(self, values):
        return types.SimpleNamespace(**(values or {}))


class _Env(dict):
    pass


class _FakeOdooFieldType:
    @staticmethod
    def to_string(value):
        return str(value)


def _install_module(name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _load_handler():
    root = Path(__file__).resolve().parents[1]
    exc_mod = _install_module("odoo.exceptions", AccessError=type("AccessError", (Exception,), {}), UserError=type("UserError", (Exception,), {}))
    fields_mod = types.SimpleNamespace(Date=_FakeOdooFieldType, Datetime=_FakeOdooFieldType)
    _install_module("odoo", exceptions=exc_mod, fields=fields_mod)

    addons_mod = _install_module("odoo.addons")
    smart_core_mod = _install_module("odoo.addons.smart_core")
    handlers_mod = _install_module("odoo.addons.smart_core.handlers")
    core_mod = _install_module("odoo.addons.smart_core.core")
    utils_mod = _install_module("odoo.addons.smart_core.utils")
    smart_core_mod.__path__ = [str(root)]
    handlers_mod.__path__ = [str(root / "handlers")]
    core_mod.__path__ = [str(root / "core")]
    utils_mod.__path__ = [str(root / "utils")]

    _install_module("odoo.addons.smart_core.core.base_handler", BaseIntentHandler=_BaseIntentHandler)
    _install_module(
        "odoo.addons.smart_core.core.project_context",
        record_scope_denied_response=lambda meta, message="": {"ok": False, "meta": meta, "message": message},
        project_scope_denied_response=lambda meta: {"ok": False, "meta": meta},
        record_in_business_scope=lambda model, record_id, params=None, context=None: (True, {"applied": False}),
        record_in_project_scope=lambda model, record_id, project_id: (True, {"applied": False}),
        selected_record_context_id_from_context=lambda params, context: None,
        selected_project_id_from_context=lambda params, context: None,
    )
    _install_module(
        "odoo.addons.smart_core.core.unified_page_contract_v2_assembler",
        assemble_unified_page_patch_v2=lambda data, action_id, request_id: {"meta": {"contractVersion": "2.0"}},
    )
    _install_module(
        "odoo.addons.smart_core.core.unified_page_contract_lite_preview",
        with_lite_preview_if_requested=lambda response, params, key: response,
    )
    reason_name = "odoo.addons.smart_core.utils.reason_codes"
    sys.modules.pop(reason_name, None)
    reason_spec = importlib.util.spec_from_file_location(reason_name, root / "utils" / "reason_codes.py")
    reason_module = importlib.util.module_from_spec(reason_spec)
    sys.modules[reason_name] = reason_module
    reason_spec.loader.exec_module(reason_module)

    module_name = "odoo.addons.smart_core.handlers.api_onchange"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, root / "handlers" / "api_onchange.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class TestApiOnchangeRecordIdBoundaries(unittest.TestCase):
    def setUp(self):
        self.module = _load_handler()

    def test_invalid_record_id_returns_bad_request(self):
        handler = self.module.ApiOnchangeHandler(env=_Env({"x.model": _Model()}), params={"model": "x.model", "id": "bad"})

        result = handler.handle()

        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], 400)
        self.assertEqual(result["error"]["message"], "id invalid")

    def test_missing_record_id_still_allows_new_record_onchange(self):
        handler = self.module.ApiOnchangeHandler(env=_Env({"x.model": _Model()}), params={"model": "x.model"})

        result = handler.handle()

        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["applied_fields"], [])

    def test_string_false_include_v2_patch_does_not_generate_v2_patch(self):
        handler = self.module.ApiOnchangeHandler(
            env=_Env({"x.model": _Model()}),
            params={"model": "x.model", "include_v2_patch": "false"},
        )

        result = handler.handle()

        self.assertTrue(result["ok"])
        self.assertNotIn("unified_page_patch_v2", result)

    def test_invalid_backend_line_row_id_does_not_break_normalization(self):
        model = _OnchangeModel()
        line = _LineModel()
        model.env = _Env({"x.line": line})
        env = _Env({"x.model": model, "x.line": line})
        handler = self.module.ApiOnchangeHandler(
            env=env,
            params={"model": "x.model", "changed_fields": ["line_ids"], "values": {"line_ids": []}},
        )

        result = handler.handle()

        self.assertTrue(result["ok"])
        line_patch = result["data"]["line_patches"][0]
        self.assertEqual(line_patch["row_id"], 0)
        self.assertEqual(line_patch["row_state"], "create")
        self.assertEqual(line_patch["command_hint"], [0])

    def test_native_result_preserved_without_manual_reexecution(self):
        env = _Env({"x.manual": _ManualOnchangeModel()})
        handler = self.module.ApiOnchangeHandler(
            env=env,
            params={"model": "x.manual", "values": {"menu_id": 1}, "changed_fields": ["menu_id"]},
        )

        result = handler.handle()

        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["patch"]["original_label"], "基础设置")
        self.assertEqual(result["data"]["patch"]["preview_summary"], "保存后刷新页面生效")

    def test_native_failures_never_enter_manual_supplement(self):
        for failure, code, reason in (
            (self.module.AccessError("private access detail"), 403, "ONCHANGE_ACCESS_DENIED"),
            (self.module.UserError("Invalid business value"), 400, "ONCHANGE_VALIDATION_FAILED"),
            (RuntimeError("private internal detail"), 500, "ONCHANGE_EXECUTION_FAILED"),
        ):
            with self.subTest(reason=reason):
                model = _ManualOnchangeModel()
                handler = self.module.ApiOnchangeHandler(env=_Env({"x.manual": model}), params={
                    "model": "x.manual", "values": {"menu_id": 1}, "changed_fields": ["menu_id"],
                    "include_v2_patch": True,
                })
                with patch.object(model, "onchange", side_effect=failure), patch.object(model, "new") as manual:
                    result = handler.handle()
                manual.assert_not_called()
                self.assertFalse(result["ok"])
                self.assertEqual(result["code"], code)
                self.assertEqual(result["error"]["reason_code"], reason)
                self.assertNotIn("private", result["error"]["message"])
                self.assertNotIn("data", result)
                self.assertNotIn("unified_page_patch_v2", result)
                if code == 400:
                    self.assertEqual(result["error"]["message"], "Invalid business value")

    def test_invalid_native_response_is_not_empty_success(self):
        for raw in (None, [], "invalid", {"value": []}, {"domain": "bad"},
                    {"modifiers_patch": []}, {"line_patches": {}}, {"line_patches": [1]},
                    {"warning": "bad"}, {"warning": [1]}):
            model = _ManualOnchangeModel()
            handler = self.module.ApiOnchangeHandler(env=_Env({"x.manual": model}), params={
                "model": "x.manual", "values": {"menu_id": 1}, "changed_fields": ["menu_id"],
            })
            with patch.object(model, "onchange", return_value=raw), patch.object(model, "new") as manual:
                result = handler.handle()
            manual.assert_not_called()
            self.assertFalse(result["ok"])
            self.assertEqual(result["error"]["reason_code"], "ONCHANGE_RESPONSE_INVALID")

    def test_view_spec_keeps_hidden_fields_and_separates_child_scope(self):
        model = _ManualOnchangeModel()
        child = _LineModel()
        model._fields = {**model._fields, "line_ids": _Field("one2many", "x.line")}
        model.env = _Env({"x.line": child})
        child._fields = {"name": _Field("char"), "hidden": _Field("char")}
        arch = '<form><field name="menu_id"/><field name="original_label" invisible="1"/><field name="line_ids"><tree><field name="name"/></tree></field><field name="line_ids"><form><field name="hidden" invisible="1"/></form></field></form>'
        with patch.object(model, "get_view", return_value={"arch": arch}) as get_view:
            spec = self.module.build_native_onchange_spec(model, view_id=17)
        get_view.assert_called_once_with(view_id=17, view_type="form")
        self.assertEqual(spec, {"menu_id": {"fields": {"display_name": {}}}, "original_label": {},
                                "line_ids": {"fields": {"name": {}, "hidden": {}}}})
        with patch.object(model, "get_view", return_value={"arch": arch}), patch.object(child, "check_field_access_rights", side_effect=self.module.AccessError("denied")):
            with self.assertRaises(self.module.AccessError):
                self.module.build_native_onchange_spec(model)

    def test_implicit_relation_subview_resolves_comodel_default_form(self):
        model = _ManualOnchangeModel()
        child = _LineModel()
        child._fields = {"name": _Field("char"), "partner_id": _Field("many2one", "res.partner")}
        model._fields = {**model._fields, "line_ids": _Field("one2many", "x.line")}
        model.env = _Env({"x.line": child})

        with patch.object(child, "get_view", wraps=child.get_view) as get_view:
            spec = self.module.build_native_onchange_spec(model)

        get_view.assert_called_once_with(view_type="form")
        self.assertEqual(
            spec,
            {
                "menu_id": {"fields": {"display_name": {}}},
                "original_label": {},
                "preview_summary": {},
                "line_ids": {
                    "fields": {
                        "name": {},
                        "partner_id": {"fields": {"display_name": {}}},
                    },
                },
            },
        )

    def test_explicit_subview_skips_implicit_resolution(self):
        model = _ManualOnchangeModel()
        child = _LineModel()
        child._fields = {"name": _Field("char"), "hidden": _Field("char")}
        model._fields = {**model._fields, "line_ids": _Field("one2many", "x.line")}
        model.env = _Env({"x.line": child})
        arch = '<form><field name="menu_id"/><field name="line_ids"><tree><field name="name"/></tree></field></form>'

        with patch.object(model, "get_view", return_value={"arch": arch}), patch.object(
            child, "get_view", side_effect=AssertionError("implicit subview must not resolve")
        ) as implicit:
            spec = self.module.build_native_onchange_spec(model)

        implicit.assert_not_called()
        self.assertEqual(spec["line_ids"], {"fields": {"name": {}}})

    def test_implicit_self_referential_subview_does_not_recurse(self):
        model = _ManualOnchangeModel()
        child = _LineModel()
        child._fields = {"name": _Field("char"), "child_ids": _Field("one2many", "x.line")}
        model._fields = {**model._fields, "line_ids": _Field("one2many", "x.line")}
        model.env = _Env({"x.line": child})

        with patch.object(child, "get_view", wraps=child.get_view) as get_view:
            spec = self.module.build_native_onchange_spec(model)

        self.assertEqual(get_view.call_count, 1)
        self.assertEqual(spec["line_ids"], {"fields": {"name": {}, "child_ids": {}}})

    def test_implicit_subview_unknown_field_raises(self):
        model = _ManualOnchangeModel()
        child = _LineModel()
        child._fields = {"name": _Field("char")}
        model._fields = {**model._fields, "line_ids": _Field("one2many", "x.line")}
        model.env = _Env({"x.line": child})

        with patch.object(child, "get_view", return_value={"arch": '<form><field name="ghost"/></form>'}):
            with self.assertRaises(self.module.NativeOnchangeSpecError):
                self.module.build_native_onchange_spec(model)

    def test_implicit_subview_read_denied_raises(self):
        model = _ManualOnchangeModel()
        child = _LineModel()
        child._fields = {"name": _Field("char")}
        model._fields = {**model._fields, "line_ids": _Field("one2many", "x.line")}
        model.env = _Env({"x.line": child})

        with patch.object(child, "check_access_rights", side_effect=self.module.AccessError("denied")):
            with self.assertRaises(self.module.AccessError):
                self.module.build_native_onchange_spec(model)

    def test_changed_field_requires_view_declaration_and_value(self):
        model = _ManualOnchangeModel()
        for values, arch in (({}, '<form><field name="menu_id"/></form>'),
                             ({"menu_id": 1}, '<form><field name="original_label"/></form>')):
            handler = self.module.ApiOnchangeHandler(env=_Env({"x.manual": model}), params={
                "model": "x.manual", "values": values, "changed_fields": ["menu_id"],
            })
            with patch.object(model, "get_view", return_value={"arch": arch}), patch.object(model, "onchange") as native:
                result = handler.handle()
            native.assert_not_called()
            self.assertEqual(result["error"]["reason_code"], "ONCHANGE_SPEC_INVALID")

    def test_native_called_once_with_full_view_spec(self):
        model = _ManualOnchangeModel()
        handler = self.module.ApiOnchangeHandler(env=_Env({"x.manual": model}), params={
            "model": "x.manual", "values": {"menu_id": 1}, "changed_fields": ["menu_id"],
        })
        with patch.object(model, "onchange", return_value={"value": {}}) as native, patch.object(model, "new") as manual:
            result = handler.handle()
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["patch"], {})
        manual.assert_not_called()
        native.assert_called_once_with({"menu_id": 1}, ["menu_id"], {
            "menu_id": {"fields": {"display_name": {}}}, "original_label": {}, "preview_summary": {},
        })

    def test_native_relation_objects_adapt_without_losing_virtual_identity(self):
        model = _ManualOnchangeModel()
        child = _LineModel()
        model._fields = {**model._fields, "line_ids": _Field("one2many", "x.line")}
        child._fields = {"partner_id": _Field("many2one", "res.partner")}
        model.env = _Env({"x.line": child})
        raw = {"menu_id": {"id": 7, "display_name": "Native menu"},
               "line_ids": [[1, "virtual_a", {"partner_id": {"id": 9, "display_name": "Native partner"}}]]}
        result = self.module.normalize_native_onchange_values(model, raw)
        self.assertEqual(result, {"menu_id": [7, "Native menu"],
                                 "line_ids": [[1, "virtual_a", {"partner_id": [9, "Native partner"]}]]})
        self.assertIsInstance(raw["menu_id"], dict)
        handler = self.module.ApiOnchangeHandler(env=_Env({"x.manual": model}), params={
            "model": "x.manual", "values": {"menu_id": 1}, "changed_fields": ["menu_id"],
        })
        with patch.object(model, "onchange", return_value={"value": raw}):
            response = handler.handle()
        self.assertTrue(response["ok"], response)
        self.assertEqual(response["data"]["patch"], result)
        with patch.object(model, "onchange", return_value={"value": {"menu_id": {"id": True}}}):
            response = handler.handle()
        self.assertEqual(response["error"]["reason_code"], "ONCHANGE_RESPONSE_INVALID")

    def feedback_params(self, **overrides):
        params = {
            "model": "x.model",
            "values": {},
            "changed_fields": [],
            "feedback_evaluation": {
                "version": "1.0.0",
                "operation": "describe",
                "request_id": "r6_3_handler",
                "view_id": 1,
                "container_id": "feedback",
            },
        }
        params.update(overrides)
        return params

    def test_feedback_requires_draft_capability_before_transport(self):
        handler = self.module.ApiOnchangeHandler(
            env=_Env({"x.model": _Model()}),
            params=self.feedback_params(),
        )
        result = handler.handle()
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], 409)
        self.assertEqual(result["error"]["reason_code"], "COMPONENT_CAPABILITY_REQUIRED")
        self.assertEqual(
            result["error"]["details"]["feedback_evaluation"]["diagnostic"]["path"],
            "feedback_evaluation.capability",
        )

    def test_feedback_rejects_mixed_patch_inputs(self):
        for overrides in (
            {"values": {"note": "unsafe"}},
            {"changed_fields": ["note"]},
            {"include_v2_patch": True},
            {"client_contract_capabilities": ["form.feedback.message.v1", "form.feedback.draft.v1"], "contract_version": "2.2.0"},
        ):
            with self.subTest(overrides=overrides):
                handler = self.module.ApiOnchangeHandler(
                    env=_Env({"x.model": _Model()}),
                    params=self.feedback_params(**overrides),
                )
                result = handler.handle()
                self.assertFalse(result["ok"])
                self.assertEqual(result["code"], 400)
                self.assertEqual(result["error"]["reason_code"], "FEEDBACK_CONFIG_INVALID")

    def test_feedback_success_is_the_only_payload_and_contains_no_patch(self):
        params = self.feedback_params(client_contract_capabilities=[
            "form.feedback.message.v1",
            "form.feedback.draft.v1",
        ])
        handler = self.module.ApiOnchangeHandler(env=_Env({"x.model": _Model()}), params=params)
        payload = {
            "version": "1.0.0",
            "request_id": "r6_3_handler",
            "status": "described",
            "binding": {"etag": "a" * 64},
        }
        with patch.object(self.module, "evaluate_feedback", return_value=payload) as evaluate:
            result = handler.handle()
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["data"]["feedback_evaluation"], payload)
        self.assertEqual(result["data"]["patch"], {})
        self.assertEqual(result["data"]["modifiers_patch"], {})
        self.assertEqual(result["data"]["line_patches"], [])
        self.assertNotIn("unified_page_patch_v2", result)
        self.assertNotIn("lite_preview", result)
        evaluate.assert_called_once()


if __name__ == "__main__":
    unittest.main()
