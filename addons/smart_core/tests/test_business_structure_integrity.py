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


class PublicationGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load()

    def gate(self, payload, model_fields=None, native_groups=None):
        diagnostics = self.module.validate_business_structure(
            payload, model_fields=model_fields, native_groups=native_groups,
        )
        compatibility = self.module.extract_compatibility(payload)
        return self.module.publication_gate(diagnostics, compatibility=compatibility)

    def complete_compat(self):
        return {
            "legacyCompatible": True,
            "compatibilityReason": "historical placeholder",
            "compatibilityScope": ["payment.request/649/1773"],
            "unresolvedDiagnostics": ["SECTION_FIELDS_EMPTY"],
            "owner": "business_config_admin",
            "migrationStatus": "pending_migration",
        }

    def test_complete_formal_is_formal(self):
        payload = {"view_orchestration": {"views": {"form": {
            "composition_mode": "entry_semantic_surface",
            "identity_fields": ["name"],
            "sections": [{"key": "identity", "title": "项目身份", "fields": ["name", "code"]}],
        }}}}
        self.assertEqual(self.gate(payload, {"name": {}, "code": {}})["verdict"], "formal")

    def test_missing_section_fields_blocks(self):
        payload = {"view_orchestration": {"views": {"form": {
            "composition_mode": "entry_semantic_surface",
            "identity_fields": ["name"],
            "sections": [{"key": "identity", "title": "项目身份"}],
        }}}}
        self.assertEqual(self.gate(payload, {"name": {}})["verdict"], "blocked")

    def test_empty_section_fields_blocks(self):
        payload = {"view_orchestration": {"views": {"form": {
            "composition_mode": "entry_semantic_surface",
            "identity_fields": ["name"],
            "sections": [{"key": "identity", "title": "项目身份", "fields": []}],
        }}}}
        self.assertEqual(self.gate(payload, {"name": {}})["verdict"], "blocked")

    def test_missing_identity_blocks(self):
        payload = {"view_orchestration": {"views": {"form": {
            "composition_mode": "entry_semantic_surface",
            "sections": [{"key": "identity", "title": "项目身份", "fields": ["name"]}],
        }}}}
        self.assertEqual(self.gate(payload, {"name": {}})["verdict"], "blocked")

    def test_multiple_section_warning_is_not_blocking(self):
        payload = {"view_orchestration": {"views": {"form": {
            "composition_mode": "entry_semantic_surface",
            "identity_fields": ["name"],
            "sections": [
                {"key": "identity", "title": "项目身份", "fields": ["name"]},
                {"key": "summary", "title": "项目摘要", "fields": ["name"]},
            ],
        }}}}
        verdict = self.gate(payload, {"name": {}})["verdict"]
        self.assertEqual(verdict, "formal")

    def test_invalid_native_group_blocks(self):
        payload = {"view_orchestration": {"views": {"form": {
            "composition_mode": "entry_semantic_surface",
            "identity_fields": ["name"],
            "sections": [{
                "key": "identity", "title": "项目身份", "fields": ["name"],
                "native_group": "ghost_group",
            }],
        }}}}
        self.assertEqual(
            self.gate(payload, {"name": {}}, native_groups={"real_group"})["verdict"],
            "blocked",
        )

    def test_explicit_legacy_allows_non_blocking_gaps(self):
        payload = {"view_orchestration": {
            "compatibility": self.complete_compat(),
            "views": {"form": {
                "composition_mode": "entry_semantic_surface",
                "sections": [{"title": "项目身份"}],
            }},
        }}
        self.assertEqual(self.gate(payload, {"name": {}})["verdict"], "legacy_compatible")

    def test_incomplete_legacy_declaration_blocks(self):
        payload = {"view_orchestration": {
            "compatibility": {"legacyCompatible": True},
            "views": {"form": {"composition_mode": "entry_semantic_surface"}},
        }}
        verdict = self.gate(payload, {"name": {}})
        self.assertEqual(verdict["verdict"], "blocked")
        self.assertEqual(verdict["reason"], "incomplete_legacy_declaration")

    def test_unverified_without_legacy_is_unclassified(self):
        payload = {"view_orchestration": {"views": {"form": {
            "composition_mode": "entry_semantic_surface",
            "identity_fields": ["name"],
            "sections": [{
                "key": "identity", "title": "项目身份", "fields": ["name"],
                "native_group": "real_group",
            }],
        }}}}
        verdict = self.gate(payload, {"name": {}})
        self.assertEqual(verdict["verdict"], "unclassified_historical")

    def test_gate_is_deterministic_for_same_diagnostics(self):
        diag = [{"severity": "ERROR", "code": "IDENTITY_MISSING", "target": "x", "message": "m"}]
        first = self.module.publication_gate(diag, compatibility={})
        second = self.module.publication_gate(diag, compatibility={})
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
