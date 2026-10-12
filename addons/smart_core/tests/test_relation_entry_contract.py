# -*- coding: utf-8 -*-
"""Host-runnable lock on the relation-entry contract boundary.

``PageAssembler._build_relation_entry_for_field`` publishes the create capability
of a declared relation field.  A field the contract already declares readonly
must not advertise a create entry, otherwise the same payload is self
contradictory (viewer sees a "new" entry on a field it cannot edit).  The Odoo
module ``page_assembler`` is loaded with stubbed ``odoo`` modules, matching
``test_page_assembler_view_orchestration_versions.py``, so this lock runs without
a live Odoo runtime.
"""
from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "addons/smart_core/app_config_engine/services/assemblers/page_assembler.py"


def _install_module(name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _load_page_assembler():
    for name in list(sys.modules):
        if name == "odoo" or name.startswith("odoo."):
            sys.modules.pop(name, None)
    odoo = _install_module("odoo", _=lambda value: value)
    _install_module("odoo.exceptions", AccessError=type("AccessError", (Exception,), {}))
    _install_module("odoo.http", request=types.SimpleNamespace(env=None))
    odoo.http = sys.modules["odoo.http"]
    _install_module("odoo.addons")
    smart_core = _install_module("odoo.addons.smart_core")
    app_config = _install_module("odoo.addons.smart_core.app_config_engine")
    services = _install_module("odoo.addons.smart_core.app_config_engine.services")
    assemblers = _install_module("odoo.addons.smart_core.app_config_engine.services.assemblers")
    utils = _install_module("odoo.addons.smart_core.utils")
    smart_core.__path__ = [str(ROOT / "addons/smart_core")]
    app_config.__path__ = [str(ROOT / "addons/smart_core/app_config_engine")]
    services.__path__ = [str(ROOT / "addons/smart_core/app_config_engine/services")]
    assemblers.__path__ = [str(ROOT / "addons/smart_core/app_config_engine/services/assemblers")]
    utils.__path__ = [str(ROOT / "addons/smart_core/utils")]
    _install_module(
        "odoo.addons.smart_core.utils.delete_policy",
        resolve_unlink_policy=lambda *_args, **_kwargs: {},
    )
    _install_module(
        "odoo.addons.smart_core.utils.extension_hooks",
        call_extension_hook_first=lambda *_args, **_kwargs: None,
    )
    _install_module(
        "odoo.addons.smart_core.app_config_engine.utils.misc",
        safe_eval=lambda value: value,
    )
    _install_module(
        "odoo.addons.smart_core.app_config_engine.utils.view_utils",
        extract_tree_columns_strict=lambda *_args, **_kwargs: ([], None),
        normalize_cols_safely=lambda value, *_args, **_kwargs: value,
    )
    module_name = "odoo.addons.smart_core.app_config_engine.services.assemblers.page_assembler"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module.PageAssembler


class TestRelationEntryContract(unittest.TestCase):
    def setUp(self):
        assembler_cls = _load_page_assembler()
        self.assembler = assembler_cls.__new__(assembler_cls)
        self.assembler.env = {}


    def test_extract_dictionary_type_from_domain_list(self):
        result = self.assembler._extract_dictionary_type_from_domain([("type", "=", "project_type")])
        self.assertEqual(result, "project_type")

    def test_extract_dictionary_type_from_domain_string(self):
        result = self.assembler._extract_dictionary_type_from_domain("[('type','=','project_category')]")
        self.assertEqual(result, "project_category")

    def test_build_relation_entry_page_mode(self):
        descriptor = {"relation": "res.users", "domain": []}
        base_entry = {"model": "res.users", "action_id": 88, "menu_id": 9, "can_read": True, "can_create": True}
        entry = self.assembler._build_relation_entry_for_field("manager_id", descriptor, base_entry)
        self.assertEqual(entry.get("create_mode"), "page")
        self.assertEqual(entry.get("default_vals"), {})
        self.assertTrue(entry.get("can_read"))
        self.assertEqual(entry.get("reason_code"), "PAGE_ENTRY_READY")

    def test_build_relation_entry_page_mode_for_dictionary_keeps_type_default(self):
        descriptor = {"relation": "sc.dictionary", "domain": "[('type','=','project_type')]"}
        base_entry = {"model": "sc.dictionary", "action_id": 101, "menu_id": 11, "can_read": True, "can_create": True}
        entry = self.assembler._build_relation_entry_for_field("project_type_id", descriptor, base_entry)
        self.assertEqual(entry.get("create_mode"), "page")
        self.assertEqual(entry.get("default_vals", {}).get("type"), "project_type")
        self.assertTrue(entry.get("can_read"))
        self.assertEqual(entry.get("reason_code"), "PAGE_ENTRY_READY")

    def test_build_relation_entry_page_mode_readonly_when_create_forbidden(self):
        descriptor = {"relation": "sc.dictionary", "domain": "[('type','=','project_type')]"}
        base_entry = {"model": "sc.dictionary", "action_id": 101, "menu_id": 11, "can_read": True, "can_create": False}
        entry = self.assembler._build_relation_entry_for_field("project_type_id", descriptor, base_entry)
        self.assertEqual(entry.get("create_mode"), "page")
        self.assertEqual(entry.get("default_vals", {}).get("type"), "project_type")
        self.assertTrue(entry.get("can_read"))
        self.assertEqual(entry.get("reason_code"), "PAGE_ENTRY_READONLY")

    def test_build_relation_entry_readonly_field_does_not_publish_create(self):
        # A readonly field is not editable, so it must not advertise a create
        # capability even when the relation target has a page entry authority.
        descriptor = {
            "relation": "project.funding.baseline",
            "domain": [],
            "readonly": True,
        }
        base_entry = {
            "model": "project.funding.baseline",
            "action_id": 645,
            "menu_id": 559,
            "can_read": True,
            "can_create": True,
        }
        entry = self.assembler._build_relation_entry_for_field(
            "funding_baseline_id", descriptor, base_entry
        )
        self.assertFalse(entry.get("can_create"))
        self.assertEqual(entry.get("create_mode"), "page")
        self.assertEqual(entry.get("reason_code"), "PAGE_ENTRY_READONLY")
        self.assertFalse((entry.get("inline_create") or {}).get("enabled"))

    def test_build_relation_entry_quick_mode_for_dictionary(self):
        descriptor = {"relation": "sc.dictionary", "domain": "[('type','=','project_type')]"}
        base_entry = {"model": "sc.dictionary", "action_id": None, "menu_id": None, "can_read": True, "can_create": True}
        entry = self.assembler._build_relation_entry_for_field("project_type_id", descriptor, base_entry)
        self.assertEqual(entry.get("create_mode"), "quick")
        self.assertEqual(entry.get("default_vals", {}).get("type"), "project_type")
        self.assertTrue(entry.get("can_read"))
        self.assertEqual(entry.get("reason_code"), "QUICK_CREATE_READY")

    def test_build_relation_entry_disabled_without_page_or_quick(self):
        descriptor = {"relation": "project.task", "domain": []}
        base_entry = {"model": "project.task", "action_id": None, "menu_id": None, "can_read": True, "can_create": True}
        entry = self.assembler._build_relation_entry_for_field("task_id", descriptor, base_entry)
        self.assertEqual(entry.get("create_mode"), "disabled")
        self.assertTrue(entry.get("can_read"))
        self.assertEqual(entry.get("reason_code"), "NO_CREATE_ENTRY")

    def test_self_relation_search_dialog_uses_minimal_contract(self):
        dialog = self.assembler._build_relation_search_dialog_contract(
            "construction.contract",
            model_name="construction.contract",
        )

        self.assertEqual(dialog.get("source"), "self_relation_minimal_view")
        self.assertEqual(dialog.get("read_fields"), ["id", "display_name", "name"])
        self.assertEqual(dialog.get("columns"), [])

    def test_build_relation_entry_dictionary_domain_hint_from_model_field(self):
        class _Field:
            domain = [("type", "=", "project_type")]

        class _Model:
            _fields = {"project_type_id": _Field()}

        self.assembler.env = {"project.project": _Model()}
        descriptor = {"relation": "sc.dictionary", "domain": []}
        base_entry = {"model": "sc.dictionary", "action_id": None, "menu_id": None, "can_read": True, "can_create": True}
        entry = self.assembler._build_relation_entry_for_field(
            "project_type_id",
            descriptor,
            base_entry,
            model_name="project.project",
        )
        self.assertEqual(entry.get("create_mode"), "quick")
        self.assertEqual(entry.get("default_vals", {}).get("type"), "project_type")

    def test_build_relation_entry_disabled_when_relation_read_forbidden(self):
        descriptor = {"relation": "sc.dictionary", "domain": "[('type','=','project_type')]"}
        base_entry = {"model": "sc.dictionary", "action_id": 101, "menu_id": 11, "can_read": False, "can_create": True}
        entry = self.assembler._build_relation_entry_for_field("project_type_id", descriptor, base_entry)
        self.assertEqual(entry.get("create_mode"), "disabled")
        self.assertFalse(entry.get("can_read"))
        self.assertEqual(entry.get("reason_code"), "RELATION_READ_FORBIDDEN")

    def test_apply_access_policy_blocks_when_core_relation_unreadable(self):
        data = {
            "fields": {
                "name": {"type": "char"},
                "project_type_id": {
                    "type": "many2one",
                    "relation": "sc.dictionary",
                    "relation_entry": {"can_read": False, "reason_code": "RELATION_READ_FORBIDDEN"},
                },
            },
            "field_groups": [
                {"name": "core", "fields": ["name", "project_type_id"]},
            ],
            "warnings": [],
            "degraded": False,
        }
        self.assembler._apply_access_policy(data, model_name="project.project")
        policy = data.get("access_policy") or {}
        self.assertEqual(policy.get("mode"), "block")
        self.assertEqual(policy.get("reason_code"), "RELATION_READ_FORBIDDEN_CORE")
        self.assertEqual(len(policy.get("blocked_fields") or []), 1)

    def test_apply_access_policy_degrades_when_non_core_relation_unreadable(self):
        data = {
            "fields": {
                "name": {"type": "char"},
                "project_type_id": {
                    "type": "many2one",
                    "relation": "sc.dictionary",
                    "relation_entry": {"can_read": False, "reason_code": "RELATION_READ_FORBIDDEN"},
                },
            },
            "field_groups": [
                {"name": "core", "fields": ["name"]},
            ],
            "warnings": [],
            "degraded": False,
        }
        self.assembler._apply_access_policy(data, model_name="project.project")
        policy = data.get("access_policy") or {}
        self.assertEqual(policy.get("mode"), "degrade")
        self.assertEqual(policy.get("reason_code"), "RELATION_READ_FORBIDDEN")
        self.assertEqual(len(policy.get("degraded_fields") or []), 1)

    def test_apply_access_policy_degrades_when_core_relation_targets_system_model(self):
        data = {
            "fields": {
                "name": {"type": "char"},
                "alias_model_id": {
                    "type": "many2one",
                    "relation": "ir.model",
                    "relation_entry": {"can_read": False, "reason_code": "RELATION_READ_FORBIDDEN"},
                },
            },
            "field_groups": [
                {"name": "core", "fields": ["name", "alias_model_id"]},
            ],
            "warnings": [],
            "degraded": False,
        }
        self.assembler._apply_access_policy(data, model_name="project.project")
        policy = data.get("access_policy") or {}
        self.assertEqual(policy.get("mode"), "degrade")
        self.assertEqual(policy.get("reason_code"), "RELATION_READ_FORBIDDEN")
        self.assertEqual(len(policy.get("blocked_fields") or []), 0)
        self.assertEqual(len(policy.get("degraded_fields") or []), 1)


if __name__ == "__main__":
    unittest.main()
