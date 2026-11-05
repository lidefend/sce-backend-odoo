#!/usr/bin/env python3
"""Offline tests for the module capability reverse index."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load():
    spec = importlib.util.spec_from_file_location("module_capability_index", ROOT / "scripts/verify/module_capability_index.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


idx = _load()


class ModuleClassificationTests(unittest.TestCase):
    def test_repo_module_source_classification(self):
        repo = idx._repo_modules()
        self.assertEqual(repo["smart_core"]["source"], "sce_custom")
        self.assertEqual(repo["sce_customer_sample"]["source"], "customer_custom")

    def test_external_source_classification(self):
        self.assertEqual(idx._classify_external("project"), ("odoo_native", "curated_odoo_native_list"))
        self.assertEqual(idx._classify_external("base_tier_validation"), ("oca", "curated_oca_list"))
        source, _ = idx._classify_external("some_unknown_module")
        self.assertEqual(source, "unknown")


class ReverseIndexTests(unittest.TestCase):
    def test_native_project_module_is_reverse_mapped(self):
        index = idx._reverse_index()
        self.assertIn("project", index)
        keys = {c["capability_key"] for c in index["project"]}
        self.assertIn("project.initiation.create", keys)
        # project.progress.entry is SCE-owned, not native project
        self.assertNotIn("cost.progress.report", keys)

    def test_smart_construction_core_is_the_primary_provider(self):
        index = idx._reverse_index()
        self.assertGreaterEqual(len(index.get("smart_construction_core", [])), 13)

    def test_candidate_scene_diff_is_bidirectional(self):
        payload = idx.build()
        diff = payload["candidate_scene_diff"]
        self.assertTrue(diff["candidate_not_in_scene"])
        self.assertTrue(diff["scene_not_in_candidate"])

    def test_mechanism_impact_maps_oca_to_capabilities(self):
        impact = idx._mechanism_impact()
        self.assertIn("base_tier_validation", impact)
        self.assertIn("contract.settlement.audit", impact["base_tier_validation"])

    def test_module_snapshot_has_field_facts_and_digests(self):
        payload = idx.build()
        core = payload["module_snapshot"]["smart_construction_core"]
        self.assertGreater(len(core["models"]), 100)
        self.assertTrue(core["fact_digest"])
        self.assertGreater(len(core["file_digests"]), 100)

    def test_inherit_declares_is_precise(self):
        # a comment/string mention is not an _inherit declaration
        self.assertFalse(idx._inherit_declares("# tier.validation is used here\nname = fields.Char()", "tier.validation"))
        self.assertFalse(idx._inherit_declares('x = "tier.validation"', "tier.validation"))
        # a comment containing the literal _inherit = "..." text is still not a declaration
        self.assertFalse(idx._inherit_declares('# _inherit = "tier.validation"', "tier.validation"))
        # a class-level single-line declaration is recognized
        self.assertTrue(idx._inherit_declares('class M(models.Model):\n    _inherit = "tier.validation"', "tier.validation"))
        # a class-level multi-line list declaration is recognized
        self.assertTrue(idx._inherit_declares('class M(models.Model):\n    _inherit = [\n        "mail.thread",\n        "tier.validation",\n    ]', "tier.validation"))
        # function-local assignment is not a class declaration
        self.assertFalse(idx._inherit_declares('def f():\n    _inherit = "tier.validation"', "tier.validation"))

    def test_fact_digest_is_order_independent_and_content_sensitive(self):
        a = idx._fact_digest({"name": "m", "version": "1"}, [{"name": "x", "fields": [{"name": "a"}]}], {"groups": 1}, {"models": 1}, [], [])
        b = idx._fact_digest({"version": "1", "name": "m"}, [{"name": "x", "fields": [{"name": "a"}]}], {"groups": 1}, {"models": 1}, [], [])
        self.assertEqual(a, b)
        c = idx._fact_digest({"name": "m", "version": "1"}, [{"name": "x", "fields": [{"name": "a"}, {"name": "b"}]}], {"groups": 1}, {"models": 1}, [], [])
        self.assertNotEqual(a, c)

    def test_fact_digest_covers_manifest_depends(self):
        def digest(depends):
            return idx._fact_digest(
                {"name": "m", "version": "1", "depends": depends},
                [{"name": "x", "fields": []}],
                {"groups": 0},
                {"models": 1},
                [],
                [],
            )
        a = digest(["a", "b"])
        b = digest(["b", "a"])
        self.assertEqual(a, b)
        c = digest(["a"])
        self.assertNotEqual(a, c)


class NameDeclarationTests(unittest.TestCase):
    def test_model_name_kwarg_does_not_declare_name(self):
        self.assertFalse(idx._name_declares('model_name = "project.project"', "project.project"))
        self.assertFalse(idx._name_declares('some_model_name = "project.project"', "project.project"))

    def test_comment_and_string_mentions_are_not_declarations(self):
        self.assertFalse(idx._name_declares('# _name = "project.project"', "project.project"))
        self.assertFalse(idx._name_declares('x = "_name = \\"project.project\\""', "project.project"))
        self.assertFalse(idx._inherit_declares('x = "_inherit = \\"project.project\\""', "project.project"))

    def test_class_level_name_declaration_is_recognized(self):
        self.assertTrue(idx._name_declares('class M(models.Model):\n    _name = "project.project"', "project.project"))
        self.assertTrue(idx._name_declares('class M(models.Model):\n        _name = "project.project"', "project.project"))
        self.assertFalse(idx._name_declares('class M(models.Model):\n    _name = "project.task"', "project.project"))

    def test_multi_line_inherit_list_is_recognized(self):
        self.assertTrue(idx._inherit_declares(
            'class M(models.Model):\n    _inherit = [\n        "mail.thread",\n        "project.project",\n    ]', "project.project"))

    def test_function_local_name_and_inherit_assignment_do_not_match(self):
        self.assertFalse(idx._name_declares('def f():\n    _name = "project.project"', "project.project"))
        self.assertFalse(idx._inherit_declares('def f():\n    _inherit = "project.project"', "project.project"))

    def test_provider_module_has_no_false_positive_for_model_name(self):
        modules = idx._provider_module("odoo_model", "project.project")
        self.assertNotIn("smart_core", modules)
        self.assertNotIn("smart_construction_scene", modules)
        self.assertIn("smart_construction_core", modules)
        self.assertIn("project", modules)

    def test_provider_module_resolves_odoo_intent_from_contract_ref(self):
        modules = idx._provider_module(
            "odoo_intent", "project.dashboard.enter",
            "addons/smart_construction_core/handlers/project_dashboard_enter.py")
        self.assertEqual(modules, ["smart_construction_core"])


if __name__ == "__main__":
    unittest.main()
