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

    module_name = "odoo.addons.smart_core.handlers.chatter_followers"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, root / "handlers" / "chatter_followers.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class TestChatterFollowerBoundaries(unittest.TestCase):
    def test_invalid_update_action_fails_before_environment_access(self):
        module = _load_handler()
        result = module.ChatterFollowersUpdateHandler(env={}, params={"action": "replace"}).handle()
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], 400)
        self.assertEqual(result["error"]["message"], "action 无效")

    def test_invalid_record_id_fails_closed(self):
        module = _load_handler()
        result = module.ChatterFollowersListHandler(
            env={"x.model": object()}, params={"model": "x.model", "res_id": "bad"}
        ).handle()
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], 400)
        self.assertEqual(result["error"]["message"], "res_id 无效")

    def test_missing_model_and_record_fail_closed(self):
        module = _load_handler()
        result = module.ChatterFollowersListHandler(env={}, params={}).handle()
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], 400)
        self.assertEqual(result["error"]["message"], "缺少参数 model/res_id")

    def test_source_authority_declares_projection_and_current_user_write_proxy(self):
        module = _load_handler()
        read_contract = module.ChatterFollowersListHandler.source_authority_contract()
        write_contract = module.ChatterFollowersUpdateHandler.source_authority_contract()
        self.assertTrue(read_contract["projection_only"])
        self.assertFalse(read_contract["write_proxy"])
        self.assertFalse(write_contract["projection_only"])
        self.assertTrue(write_contract["write_proxy"])
        self.assertIn("mail.followers", write_contract["authorities"])

    def test_normalized_contract_carrier_preserves_follower_capability(self):
        root = Path(__file__).resolve().parents[1]
        assembler = (root / "core" / "unified_page_contract_v2_assembler.py").read_text(encoding="utf-8")
        self.assertIn('(\"chatter\", \"attachments\", \"followers\", \"timeline\", \"sourceAuthority\")', assembler)


if __name__ == "__main__":
    unittest.main()
