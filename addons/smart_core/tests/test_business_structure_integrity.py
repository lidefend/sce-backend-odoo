# -*- coding: utf-8 -*-
import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load():
    module_name = "odoo.addons.smart_core.core.business_structure_integrity"
    spec = importlib.util.spec_from_file_location(
        module_name, ROOT / "core" / "business_structure_integrity.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _payload(form_spec):
    return {"view_orchestration": {"views": {"form": form_spec}}}


class BusinessStructureIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load()

    def codes(self, diagnostics):
        return [row["code"] for row in diagnostics]

    def test_empty_form_spec_is_error(self):
        diag = self.module.validate_business_structure(_payload({}), model_fields={"name": {}})
        self.assertIn("FORM_STRUCTURE_EMPTY", self.codes(diag))

    def test_entry_surface_without_sections_is_error(self):
        diag = self.module.validate_business_structure(
            _payload({"composition_mode": "entry_semantic_surface", "identity_fields": ["name"]}),
            model_fields={"name": {}},
        )
        self.assertIn("SECTION_MISSING", self.codes(diag))

    def test_title_only_section_is_error(self):
        diag = self.module.validate_business_structure(
            _payload({
                "composition_mode": "entry_semantic_surface",
                "identity_fields": ["name"],
                "sections": [{"title": "项目信息"}],
            }),
            model_fields={"name": {}},
        )
        self.assertIn("SECTION_FIELDS_EMPTY", self.codes(diag))

    def test_unknown_section_field_is_error(self):
        diag = self.module.validate_business_structure(
            _payload({
                "composition_mode": "entry_semantic_surface",
                "identity_fields": ["name"],
                "sections": [{"key": "identity", "title": "项目身份", "fields": ["missing_field"]}],
            }),
            model_fields={"name": {}},
        )
        self.assertIn("SECTION_FIELD_INVALID", self.codes(diag))

    def test_missing_identity_is_error(self):
        diag = self.module.validate_business_structure(
            _payload({
                "composition_mode": "entry_semantic_surface",
                "sections": [{"key": "identity", "title": "项目身份", "fields": ["name"]}],
            }),
            model_fields={"name": {}},
        )
        self.assertIn("IDENTITY_MISSING", self.codes(diag))

    def test_identity_not_in_section_is_error(self):
        diag = self.module.validate_business_structure(
            _payload({
                "composition_mode": "entry_semantic_surface",
                "identity_fields": ["orphan"],
                "sections": [{"key": "identity", "title": "项目身份", "fields": ["name"]}],
            }),
            model_fields={"name": {}, "orphan": {}},
        )
        self.assertIn("IDENTITY_NOT_IN_SECTION", self.codes(diag))

    def test_complete_structure_has_no_error(self):
        diag = self.module.validate_business_structure(
            _payload({
                "composition_mode": "entry_semantic_surface",
                "identity_fields": ["name"],
                "sections": [{"key": "identity", "title": "项目身份", "fields": ["name", "code"]}],
            }),
            model_fields={"name": {}, "code": {}},
        )
        self.assertEqual(diag, [])

    def test_field_in_multiple_sections_is_warning(self):
        diag = self.module.validate_business_structure(
            _payload({
                "composition_mode": "entry_semantic_surface",
                "identity_fields": ["name"],
                "sections": [
                    {"key": "identity", "title": "项目身份", "fields": ["name"]},
                    {"key": "summary", "title": "项目摘要", "fields": ["name"]},
                ],
            }),
            model_fields={"name": {}},
        )
        codes = self.codes(diag)
        self.assertIn("FIELD_MULTIPLE_SECTION", codes)
        self.assertNotIn("SECTION_FIELDS_EMPTY", codes)

    def test_native_group_unresolved_is_error_when_model_supplied(self):
        diag = self.module.validate_business_structure(
            _payload({
                "composition_mode": "entry_semantic_surface",
                "identity_fields": ["name"],
                "sections": [{
                    "key": "identity", "title": "项目身份", "fields": ["name"],
                    "native_group": "not_a_real_group",
                }],
            }),
            model_fields={"name": {}},
            native_groups={"real_group"},
        )
        self.assertIn("NATIVE_GROUP_UNRESOLVED", self.codes(diag))

    def test_native_group_unverified_without_model(self):
        diag = self.module.validate_business_structure(
            _payload({
                "composition_mode": "entry_semantic_surface",
                "identity_fields": ["name"],
                "sections": [{
                    "key": "identity", "title": "项目身份", "fields": ["name"],
                    "native_group": "real_group",
                }],
            }),
            model_fields={"name": {}},
        )
        self.assertIn("NATIVE_GROUP_UNVERIFIED", self.codes(diag))

    def test_native_semantic_surface_sections_are_native_not_config(self):
        diag = self.module.validate_business_structure(
            _payload({
                "composition_mode": "native_semantic_surface",
                "identity_fields": ["name"],
            }),
            model_fields={"name": {}},
        )
        codes = self.codes(diag)
        self.assertNotIn("SECTION_MISSING", codes)
        self.assertNotIn("IDENTITY_NOT_IN_SECTION", codes)
        self.assertNotIn("IDENTITY_MISSING", codes)
        self.assertEqual(diag, [])


if __name__ == "__main__":
    unittest.main()
