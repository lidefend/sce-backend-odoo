# -*- coding: utf-8 -*-
import importlib.util
import sys
import types
import unittest
from pathlib import Path


class _BaseIntentHandler:
    def __init__(self, env=None, params=None, context=None):
        self.env = env or {}
        self.params = params or {}
        self.context = context or {}


class _Record:
    id = 7

    def exists(self):
        return self

    def check_access_rule(self, mode):
        return True


class _Model:
    def browse(self, record_id):
        return _Record()

    def search(self, domain, limit=None):
        return _Record()

    def check_access_rights(self, mode):
        return True


class _EmptySearchModel:
    def search(self, *args, **kwargs):
        return []


class _Env(dict):
    pass


def _load_handler():
    root = Path(__file__).resolve().parents[1]
    odoo_mod = types.ModuleType("odoo")
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

    module_name = "odoo.addons.smart_core.handlers.chatter_timeline"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, root / "handlers" / "chatter_timeline.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class TestChatterTimelineBoundaries(unittest.TestCase):
    def setUp(self):
        self.module = _load_handler()

    def test_missing_target_returns_structured_error(self):
        handler = self.module.ChatterTimelineHandler(env={}, params={}, context={"trace_id": "trace"})

        result = handler.handle()

        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], 400)
        self.assertEqual(result["error"]["reason_code"], "MISSING_PARAMS")
        self.assertEqual(result["meta"]["trace_id"], "trace")

    def test_unknown_model_returns_not_found_without_env_lookup(self):
        handler = self.module.ChatterTimelineHandler(env={}, params={"model": "missing.model", "res_id": 1})

        result = handler.handle()

        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], 404)
        self.assertEqual(result["error"]["reason_code"], "NOT_FOUND")

    def test_invalid_res_id_returns_user_error(self):
        handler = self.module.ChatterTimelineHandler(env={"x.model": object()}, params={"model": "x.model", "res_id": "bad"})

        result = handler.handle()

        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], 400)
        self.assertEqual(result["error"]["reason_code"], "USER_ERROR")

    def test_non_positive_res_id_returns_user_error(self):
        handler = self.module.ChatterTimelineHandler(env={"x.model": object()}, params={"model": "x.model", "res_id": 0})

        result = handler.handle()

        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], 400)
        self.assertEqual(result["error"]["reason_code"], "USER_ERROR")
        self.assertEqual(result["error"]["message"], "res_id 无效")

    def test_invalid_limit_returns_user_error(self):
        handler = self.module.ChatterTimelineHandler(
            env={"x.model": object()},
            params={"model": "x.model", "res_id": 7, "limit": "bad"},
        )

        result = handler.handle()

        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], 400)
        self.assertEqual(result["error"]["reason_code"], "USER_ERROR")
        self.assertEqual(result["error"]["message"], "limit 无效")

    def test_invalid_offset_returns_user_error(self):
        handler = self.module.ChatterTimelineHandler(
            env={"x.model": object()},
            params={"model": "x.model", "res_id": 7, "offset": -1},
        )

        result = handler.handle()

        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], 400)
        self.assertEqual(result["error"]["message"], "offset 无效")

    def test_string_false_include_audit_skips_audit_authority(self):
        handler = self.module.ChatterTimelineHandler(
            env=_Env({"x.model": _Model(), "mail.message": _EmptySearchModel(), "ir.attachment": _EmptySearchModel()}),
            params={"model": "x.model", "res_id": 7, "include_audit": "false"},
        )

        result = handler.handle()

        self.assertIsInstance(result, tuple)
        data, meta = result
        self.assertEqual(data["counts"]["audit"], 0)
        self.assertEqual(data["paging"], {"offset": 0, "limit": 40, "next_offset": None, "has_more": False})
        self.assertEqual(data["auxiliary_authorities"], [])
        self.assertEqual(meta["auxiliary_authorities"], [])

    def test_offset_pages_the_merged_timeline_without_dropping_items(self):
        handler = self.module.ChatterTimelineHandler(
            env=_Env({"x.model": _Model()}),
            params={"model": "x.model", "res_id": 7, "limit": 2, "offset": 2, "include_audit": False},
        )
        handler._load_messages = lambda model, res_id, limit: [
            {"key": "m-1", "type": "message", "at": "2026-08-11T12:00:00"},
            {"key": "m-2", "type": "message", "at": "2026-08-11T10:00:00"},
        ]
        handler._load_attachments = lambda model, res_id, limit: [
            {"key": "a-1", "type": "attachment", "at": "2026-08-11T11:00:00"},
            {"key": "a-2", "type": "attachment", "at": "2026-08-11T09:00:00"},
            {"key": "a-3", "type": "attachment", "at": "2026-08-11T08:00:00"},
        ]
        handler._load_activities = lambda model, res_id, limit: []

        data, _meta = handler.handle()

        self.assertEqual([item["key"] for item in data["items"]], ["m-2", "a-2"])
        self.assertEqual(data["paging"], {"offset": 2, "limit": 2, "next_offset": 4, "has_more": True})
        self.assertEqual(data["counts"]["total"], 2)

    def test_technical_audit_identifiers_are_not_product_labels(self):
        self.assertEqual(
            self.module._audit_event_label("action_submit", "payment_submitted"),
            "业务操作",
        )
        self.assertEqual(
            self.module._audit_event_label("提交付款申请", "payment_submitted"),
            "提交付款申请",
        )


if __name__ == "__main__":
    unittest.main()
