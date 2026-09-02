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


def _load_handler():
    root = Path(__file__).resolve().parents[1]
    odoo_mod = types.ModuleType("odoo")
    exc_mod = types.ModuleType("odoo.exceptions")
    exc_mod.AccessError = type("AccessError", (Exception,), {})
    exc_mod.UserError = type("UserError", (Exception,), {})
    odoo_mod.exceptions = exc_mod
    modules = {
        "odoo": odoo_mod,
        "odoo.exceptions": exc_mod,
        "odoo.addons": types.ModuleType("odoo.addons"),
        "odoo.addons.smart_core": types.ModuleType("odoo.addons.smart_core"),
        "odoo.addons.smart_core.handlers": types.ModuleType("odoo.addons.smart_core.handlers"),
        "odoo.addons.smart_core.core": types.ModuleType("odoo.addons.smart_core.core"),
    }
    for name, module in modules.items():
        sys.modules[name] = module
    modules["odoo.addons.smart_core"].__path__ = [str(root)]
    modules["odoo.addons.smart_core.handlers"].__path__ = [str(root / "handlers")]
    modules["odoo.addons.smart_core.core"].__path__ = [str(root / "core")]
    base_mod = types.ModuleType("odoo.addons.smart_core.core.base_handler")
    base_mod.BaseIntentHandler = _BaseIntentHandler
    params_mod = types.ModuleType("odoo.addons.smart_core.core.request_params")
    params_mod.parse_positive_int = lambda value: (int(value), None) if str(value).isdigit() and int(value) > 0 else (None, "invalid")
    context_mod = types.ModuleType("odoo.addons.smart_core.core.project_context")
    context_mod.record_scope_denied_response = lambda meta: {"ok": False, "code": 403, "meta": meta}
    context_mod.record_in_business_scope = lambda model, record_id, params=None, context=None: (True, {"applied": False})
    sys.modules[base_mod.__name__] = base_mod
    sys.modules[params_mod.__name__] = params_mod
    sys.modules[context_mod.__name__] = context_mod
    module_name = "odoo.addons.smart_core.handlers.chatter_message_delete"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, root / "handlers" / "chatter_message_delete.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class TestChatterMessageDeleteBoundaries(unittest.TestCase):
    def test_missing_target_fails_before_environment_access(self):
        module = _load_handler()
        result = module.ChatterMessageDeleteHandler(env={}, params={}).handle()
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], 400)

    def test_invalid_identifiers_fail_closed(self):
        module = _load_handler()
        result = module.ChatterMessageDeleteHandler(
            env={"x.model": object()},
            params={"model": "x.model", "res_id": "bad", "message_id": "also-bad"},
        ).handle()
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], 400)

    def test_source_authority_is_an_explicit_write_proxy(self):
        module = _load_handler()
        contract = module.ChatterMessageDeleteHandler.source_authority_contract()
        self.assertFalse(contract["projection_only"])
        self.assertTrue(contract["write_proxy"])
        self.assertIn("mail.message", contract["authorities"])

    def test_timeline_projects_delete_only_with_exact_intent(self):
        root = Path(__file__).resolve().parents[1]
        timeline = (root / "handlers" / "chatter_timeline.py").read_text(encoding="utf-8")
        self.assertIn('"delete_intent": "chatter.message.delete" if can_delete else ""', timeline)
        self.assertIn('Message.check_access_rights("unlink")', timeline)
        self.assertIn('row.check_access_rule("unlink")', timeline)


if __name__ == "__main__":
    unittest.main()
