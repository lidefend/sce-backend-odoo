# -*- coding: utf-8 -*-
import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _install(name, path=None):
    module = types.ModuleType(name)
    if path:
        module.__path__ = [path]
    sys.modules[name] = module
    return module


def _load_builder():
    _install("odoo")
    _install("odoo.addons")
    _install("odoo.addons.smart_core", str(ROOT))
    handlers = _install("odoo.addons.smart_core.handlers", str(ROOT / "handlers"))
    projection = _install("odoo.addons.smart_core.handlers.ui_contract_v2_projection")
    projection.form_structure_presentation_mode = lambda authority, mode: (
        "task" if mode == "task" else "workspace"
    )
    constants = _install("odoo.addons.smart_core.handlers.ui_contract_v2_constants")
    constants.BUSINESS_FORM_STRUCTURE_HISTORY_LABEL_TOKENS = ()
    constants.BUSINESS_FORM_STRUCTURE_HISTORY_NAME_PREFIXES = ()
    constants.BUSINESS_FORM_STRUCTURE_HISTORY_NAME_SUFFIXES = ()
    constants.BUSINESS_FORM_STRUCTURE_HISTORY_NAME_TOKENS = ()
    module_name = "odoo.addons.smart_core.handlers.ui_contract_v2_form_structure"
    spec = importlib.util.spec_from_file_location(
        module_name, ROOT / "handlers" / "ui_contract_v2_form_structure.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module, handlers


class _Handler:
    SOURCE_KIND = "test"

    def _form_layout_columns_from_governance(self, *args, **kwargs):
        return 0

    def _form_layout_group_visible_from_governance(self, *args, **kwargs):
        return True

    def _form_structure_surfaces(self, *args, **kwargs):
        return []


class FieldOwnershipDerivationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module, _ = _load_builder()

    def test_default_fallback_returns_minimal_structure_not_guessed_ownership(self):
        def field_type(name):
            return "many2one" if name == "owner_id" else "char"

        def field_label(name):
            return name

        contract = self.module.build_form_structure_contract(
            _Handler(),
            model="project.project",
            profile={
                "common_fields": ["name", "owner_id"],
                "detail_fields": [],
                "amount_fields": [],
                "date_fields": [],
                "status_field": "",
                "note_field": "",
                "attachment_field": "",
                "field_labels": {},
            },
            field_type=field_type,
            unique=lambda items: list(dict.fromkeys(items)),
            field_label=field_label,
            governance={"form_structure_authority": "business_view_orchestration", "field_groups": {}, "form_presentation_mode": "workspace"},
            navigation_title="项目概览",
        )
        self.assertEqual(contract["structureAuthority"], "container_tree")
        self.assertEqual(contract["structureSource"], "native_view")
        self.assertEqual(contract["slots"], [])
        self.assertEqual(contract["fieldRoles"], {})
        self.assertEqual(contract["fieldOwnership"], {})

    def test_native_authority_yields_empty_ownership(self):
        contract = self.module.build_form_structure_contract(
            _Handler(),
            model="project.project",
            profile={"common_fields": [], "detail_fields": [], "amount_fields": [], "date_fields": [], "status_field": "", "note_field": "", "attachment_field": "", "field_labels": {}},
            field_type=lambda name: "char",
            unique=lambda items: list(dict.fromkeys(items)),
            field_label=lambda name: name,
            governance={"form_structure_authority": "native_authority"},
            navigation_title="项目概览",
        )
        self.assertEqual(contract["fieldOwnership"], {})

    def test_no_field_name_guessing_without_explicit_config(self):
        def field_type(name):
            return "char"

        def field_label(name):
            return name

        contract = self.module.build_form_structure_contract(
            _Handler(),
            model="project.project",
            profile={
                "common_fields": ["project_code", "name"],
                "detail_fields": [],
                "amount_fields": [],
                "date_fields": [],
                "status_field": "",
                "note_field": "",
                "attachment_field": "",
                "field_labels": {},
            },
            field_type=field_type,
            unique=lambda items: list(dict.fromkeys(items)),
            field_label=field_label,
            governance={
                "form_structure_authority": "business_view_orchestration",
                "field_groups": {},
                "form_presentation_mode": "workspace",
                "identity_fields": ["project_code", "name"],
            },
            navigation_title="项目概览",
        )
        self.assertEqual(contract["structureAuthority"], "container_tree")
        self.assertEqual(contract["fieldOwnership"], {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
