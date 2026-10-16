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

import copy
from unittest.mock import patch
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


    def test_preference_projection_keeps_relation_denial_and_core_block(self):
        self.assembler.include_relation_search_dialogs = False
        self.assembler._build_relation_entry_map = lambda models: {
            model: {"model": model, "can_read": False, "can_create": False}
            for model in models
        }
        data = {"fields": {"parent_id": {"type": "many2one", "relation": "x.parent", "required": True}},
                "context": {}, "views": {}, "warnings": [], "degraded": False}
        with patch.object(self.assembler, '_build_relation_search_dialog_contract', side_effect=AssertionError('unused dialog')):
            self.assembler._inject_relation_entry_contract(data, 'x.child')
        self.assertFalse(data['fields']['parent_id']['relation_entry']['can_read'])
        self.assembler._apply_access_policy(data)
        self.assertEqual(data['access_policy']['mode'], 'block')
        self.assertEqual(data['access_policy']['reason_code'], 'RELATION_READ_FORBIDDEN_CORE')

    def test_preference_projection_preserves_hierarchy_dialog_dependency(self):
        self.assembler.include_relation_search_dialogs = False
        self.assembler._build_relation_entry_map = lambda models: {model: {"model": model, "can_read": True} for model in models}
        data = {"fields": {name: {"type": "many2one", "relation": 'x.' + name} for name in ('parent_id', 'other_id')},
                "context": {"hierarchy_levels": [{"field": "parent_id"}]}, "views": {}}
        with patch.object(self.assembler, '_build_relation_search_dialog_contract', return_value={'read_fields': ['id', 'code'], 'order': 'code asc'}) as build:
            self.assembler._inject_relation_entry_contract(data, 'x.child')
        self.assertEqual(build.call_count, 1)
        self.assertEqual(data['fields']['parent_id']['relation_entry']['search_dialog']['read_fields'], ['id', 'code'])
        self.assertNotIn('search_dialog', data['fields']['other_id']['relation_entry'])

    def test_full_projection_still_builds_dialogs_and_preserves_other_entry_values(self):
        descriptor = {'type': 'many2one', 'relation': 'x.parent'}
        # A readable target is exactly the case where the full projection publishes
        # search_dialog; dropping only that key must reproduce the narrow projection,
        # proving no other entry value is derived from the dialog payload.
        base = {'model': 'x.parent', 'can_read': True, 'can_create': False}
        full = self.assembler._build_relation_entry_for_field('parent_id', descriptor, base)
        narrow = self.assembler._build_relation_entry_for_field('parent_id', descriptor, base, include_search_dialog=False)
        full.pop('search_dialog')
        self.assertEqual(full, narrow)

    def test_relation_demand_declaration_classifies_sources_and_stages(self):
        data = {
            "fields": {
                "project_id": {"type": "many2one", "relation": "project.project"},
                "audit_user_id": {"type": "many2one", "relation": "res.users"},
                "amount": {"type": "float"},
            },
            "views": {"tree": {"type": "field", "name": "project_id"}},
            "context": {},
        }
        declaration = self.assembler._relation_demand_declaration(data, model_name="payment.request")
        # Only the rendered relation field requires popup content; the expansion-only
        # audit field still carries its permission and navigation facts.
        self.assertEqual(declaration["dialog_required_fields"], {"project_id"})
        self.assertEqual(declaration["targets"]["project_id"]["stages"],
                         ["permission", "navigation", "search_dialog"])
        self.assertEqual(declaration["targets"]["audit_user_id"]["stages"],
                         ["permission", "navigation"])
        self.assertIn("resolved_view_field", declaration["targets"]["project_id"]["sources"])
        self.assertIn("model_field_expansion", declaration["targets"]["audit_user_id"]["sources"])
        self.assertNotIn("resolved_view_field", declaration["targets"]["audit_user_id"]["sources"])
        self.assertNotIn("amount", declaration["targets"])
        self.assertEqual(declaration["sources"]["view_fields"], ["project_id"])

    def test_relation_demand_declaration_keeps_off_view_override_and_hierarchy(self):
        data = {
            "fields": {
                "override_only_id": {"type": "many2one", "relation": "x.override"},
                "hierarchy_only_id": {"type": "many2one", "relation": "x.hierarchy"},
                "expansion_only_id": {"type": "many2one", "relation": "x.audit"},
            },
            "views": {},
            "context": {"hierarchy_levels": [{"field": "hierarchy_only_id"}]},
        }
        declaration = self.assembler._relation_demand_declaration(
            data,
            model_name="x.child",
            layout_relation_overrides={"override_only_id": {"action_id": 5, "menu_id": 6}},
        )
        self.assertEqual(declaration["dialog_required_fields"],
                         {"override_only_id", "hierarchy_only_id"})
        self.assertEqual(declaration["targets"]["hierarchy_only_id"]["stages"],
                         ["permission", "navigation", "hierarchy_fact", "search_dialog"])
        self.assertIn("explicit_view_override",
                      declaration["targets"]["override_only_id"]["sources"])
        self.assertEqual(declaration["targets"]["expansion_only_id"]["stages"],
                         ["permission", "navigation"])

    def test_view_relation_field_materializes_one_search_dialog(self):
        self.assembler.include_relation_search_dialogs = True
        self.assembler._build_relation_entry_map = lambda models: {
            model: {"model": model, "can_read": True, "can_create": False} for model in models
        }
        data = {
            "fields": {
                "project_id": {"type": "many2one", "relation": "project.project"},
                "create_uid": {"type": "many2one", "relation": "res.users"},
            },
            "views": {"tree": {"type": "field", "name": "project_id"}},
            "context": {},
        }
        with patch.object(self.assembler, "_build_relation_search_dialog_contract",
                          return_value={"read_fields": ["id", "name"], "order": "name asc"}) as build:
            self.assembler._inject_relation_entry_contract(data, "payment.request")
        # one dialog for the rendered field; the off-view audit relation keeps facts only.
        self.assertEqual(build.call_count, 1)
        self.assertIn("search_dialog", data["fields"]["project_id"]["relation_entry"])
        off_view = data["fields"]["create_uid"]["relation_entry"]
        self.assertNotIn("search_dialog", off_view)
        self.assertTrue(off_view["can_read"])

    def test_off_view_relation_field_never_builds_a_dialog(self):
        self.assembler.include_relation_search_dialogs = True
        self.assembler._build_relation_entry_map = lambda models: {
            model: {"model": model, "can_read": True, "can_create": True} for model in models
        }
        data = {
            "fields": {"create_uid": {"type": "many2one", "relation": "res.users"}},
            "views": {"tree": {"type": "field", "name": "project_id"}},
            "context": {},
        }
        with patch.object(self.assembler, "_build_relation_search_dialog_contract",
                          side_effect=AssertionError("off-view field must not build a dialog")):
            self.assembler._inject_relation_entry_contract(data, "payment.request")
        entry = data["fields"]["create_uid"]["relation_entry"]
        self.assertNotIn("search_dialog", entry)
        self.assertTrue(entry["can_read"])
        self.assertTrue(entry["can_create"])

    def test_unreadable_relation_target_never_publishes_a_dialog(self):
        self.assembler.include_relation_search_dialogs = True
        self.assembler._build_relation_entry_map = lambda models: {
            model: {"model": model, "can_read": False, "can_create": False} for model in models
        }
        data = {
            "fields": {"project_id": {"type": "many2one", "relation": "project.project"}},
            "views": {"tree": {"type": "field", "name": "project_id"}},
            "context": {},
        }
        with patch.object(self.assembler, "_build_relation_search_dialog_contract",
                          side_effect=AssertionError("unreadable target must not build a dialog")):
            self.assembler._inject_relation_entry_contract(data, "payment.request")
        entry = data["fields"]["project_id"]["relation_entry"]
        self.assertFalse(entry["can_read"])
        # No empty structure is substituted: the key is simply absent for the client.
        self.assertNotIn("search_dialog", entry)
        self.assertEqual(entry["reason_code"], "RELATION_READ_FORBIDDEN")

    def test_off_view_hierarchy_field_still_materializes_its_dialog(self):
        self.assembler.include_relation_search_dialogs = True
        self.assembler._build_relation_entry_map = lambda models: {
            model: {"model": model, "can_read": True, "can_create": False} for model in models
        }
        data = {
            "fields": {
                "project_id": {"type": "many2one", "relation": "project.project"},
                "parent_id": {"type": "many2one", "relation": "x.parent"},
            },
            "views": {"tree": {"type": "field", "name": "project_id"}},
            "context": {"hierarchy_levels": [{"field": "parent_id"}]},
        }
        with patch.object(self.assembler, "_build_relation_search_dialog_contract",
                          return_value={"read_fields": ["id", "code"], "order": "code asc"}) as build:
            self.assembler._inject_relation_entry_contract(data, "x.child")
        # The hierarchy level is not rendered in the tree, yet its dialog facts are
        # required by the level policy and must survive.
        self.assertEqual(build.call_count, 2)
        self.assertEqual(
            data["fields"]["parent_id"]["relation_entry"]["search_dialog"]["read_fields"],
            ["id", "code"],
        )

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
