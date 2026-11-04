#!/usr/bin/env python3
"""Offline tests for CAP-02C-04 D1 unified projection and two-phase diff."""
from __future__ import annotations

import unittest

from scripts.verify import module_snapshot_diff as d1


def _repo_index(version="17.0.0.172", models=None, fact_digest="a" * 64, file_digests=None):
    return {
        "schema": "module.capability.index.v1",
        "module_baseline": {
            "smart_construction_core": {
                "technical_name": "smart_construction_core",
                "version": version,
                "source": "sce",
                "in_repo": True,
                "depends": ["base"],
            }
        },
        "module_sources": {"smart_construction_core": {"source": "sce", "capability_count": 3}},
        "module_snapshot": {
            "smart_construction_core": {
                "identity": {"technical_name": "smart_construction_core", "version": version,
                             "source": "sce", "category": "industry"},
                "models": models or [
                    {"file": "addons/smart_construction_core/models/boq.py",
                     "name": "project.boq.version", "inherit": '"mail.thread"',
                     "fields": [{"name": "name", "type": "Char", "relation": "",
                                 "required": True, "readonly": False,
                                 "compute": False, "related": False}]}
                ],
                "security": {"groups": 1, "record_rules": 2, "acl_files": 1},
                "mechanism_dependencies": [
                    {"mechanism": "mail.thread", "module": "mail", "module_source": "odoo_native",
                     "dependency_type": "mechanism", "evidence": "models/boq.py"}
                ],
                "file_digests": file_digests or {"boq.py": "f1"},
                "fact_digest": fact_digest,
            }
        },
    }


def _runtime(version="17.0.0.172", ownership=None, fields=None, actions=None):
    return {
        "schema": "module.runtime.facts.v1",
        "db_name": "sc_dev_demo",
        "registry": {"ready": True, "loaded": True, "db_matches": True},
        "modules": {"source": "runtime_registry", "completeness": "complete",
                    "items": {"smart_construction_core": {"state": "installed",
                                                           "installed_version": version}}},
        "model_ownership": {"source": "runtime_registry", "completeness": "complete",
                            "items": ownership if ownership is not None else [
                                {"model": "project.boq.version",
                                 "registry_modules": ["smart_construction_core", "mail"],
                                 "model_owner": "smart_construction_core",
                                 "model_extensions": ["mail"],
                                 "inherit_module_facts": {"mail.thread": "smart_construction_core"}}]},
        "fields": {"source": "runtime_registry", "completeness": "complete",
                   "items": fields if fields is not None else [
                       {"model": "project.boq.version", "name": "name", "ttype": "Char",
                        "relation": "", "required": True, "readonly": False,
                        "compute": False, "related": False,
                        "modules": ["smart_construction_core"]}]},
        "actions": {"source": "runtime_registry", "completeness": "complete",
                    "items": actions if actions is not None else []},
        "views": {"source": "runtime_registry", "completeness": "complete", "items": []},
        "menus": {"source": "runtime_registry", "completeness": "complete", "items": []},
        "security": {"source": "runtime_registry", "completeness": "complete",
                     "acl": [], "record_rules": [], "record_rules_count": 0, "groups_count": 0},
    }


class ProjectionTests(unittest.TestCase):
    def test_repository_projection_preserves_source_info(self):
        proj = d1.project_repository(_repo_index())
        facts = proj["modules"]["smart_construction_core"]["facts"]
        model = next(f for f in facts if f["fact_identity"] == "model:project.boq.version")
        self.assertEqual(model["source_mode"], "repository")
        self.assertEqual(model["source_module"], "smart_construction_core")
        self.assertEqual(model["source_ref"], "addons/smart_construction_core/models/boq.py")
        self.assertIn("field:project.boq.version:name",
                      [f["fact_identity"] for f in facts])

    def test_runtime_projection_uses_model_owner(self):
        proj = d1.project_runtime(_runtime())
        facts = proj["modules"]["smart_construction_core"]["facts"]
        model = next(f for f in facts if f["fact_identity"] == "model:project.boq.version")
        self.assertEqual(model["source_mode"], "runtime")
        self.assertEqual(model["source_module"], "smart_construction_core")
        self.assertEqual(model["value"]["model_owner"], "smart_construction_core")
        self.assertEqual(model["value"]["model_extensions"], ["mail"])


class AssetOwnershipTests(unittest.TestCase):
    def test_model_owner_unchanged_when_extension_added(self):
        before = d1.project_runtime(_runtime(ownership=[
            {"model": "project.project", "registry_modules": ["project"],
             "model_owner": "project", "model_extensions": []}]))
        after = d1.project_runtime(_runtime(ownership=[
            {"model": "project.project",
             "registry_modules": ["project", "smart_construction_core"],
             "model_owner": "project", "model_extensions": ["smart_construction_core"]}]))
        b_model = next(f for f in before["modules"]["project"]["facts"] if f["kind"] == "model")
        a_model = next(f for f in after["modules"]["project"]["facts"] if f["kind"] == "model")
        self.assertEqual(b_model["model_owner"], "project")
        self.assertEqual(a_model["model_owner"], "project")
        result = d1.phase2([b_model], [a_model])
        self.assertEqual(result["changes"][0]["change"], "changed")

    def test_native_model_owner_differs_from_added_field_asset_owner(self):
        proj = d1.project_runtime(_runtime(
            ownership=[{"model": "project.project", "registry_modules": ["project"],
                        "model_owner": "project", "model_extensions": []}],
            fields=[{"model": "project.project", "name": "x_custom_field",
                     "ttype": "Char", "relation": "", "required": False,
                     "readonly": False, "compute": False, "related": False,
                     "modules": ["smart_construction_core"]}]))
        fact = next(f for f in proj["modules"]["smart_construction_core"]["facts"] if f["kind"] == "field")
        self.assertEqual(fact["asset_modules"], ["smart_construction_core"])
        self.assertEqual(fact["model_owner"], "project")
        self.assertNotEqual(fact["asset_modules"], [fact["model_owner"]])

    def test_action_owner_differs_from_res_model_owner(self):
        proj = d1.project_runtime(_runtime(
            ownership=[{"model": "project.project", "registry_modules": ["project"],
                        "model_owner": "project", "model_extensions": []}],
            actions=[{"name": "action_project_custom", "res_model": "project.project",
                      "view_mode": "form", "module": "smart_construction_core"}]))
        fact = next(f for f in proj["modules"]["smart_construction_core"]["facts"] if f["kind"] == "action")
        self.assertEqual(fact["asset_modules"], ["smart_construction_core"])
        self.assertEqual(fact["model_owner"], "project")
        self.assertNotEqual(fact["asset_modules"], [fact["model_owner"]])

    def test_same_fact_correlates_across_sources_with_source_differences(self):
        repo = d1.project_repository(_repo_index())[
            "modules"]["smart_construction_core"]["facts"]
        run = d1.project_runtime(_runtime())["modules"]["smart_construction_core"]["facts"]
        r_field = next(f for f in repo if f["fact_identity"] == "field:project.boq.version:name")
        t_field = next(f for f in run if f["fact_identity"] == "field:project.boq.version:name")
        self.assertEqual(r_field["fact_identity"], t_field["fact_identity"])
        self.assertEqual(r_field["source_mode"], "repository")
        self.assertEqual(t_field["source_mode"], "runtime")
        self.assertNotEqual(r_field["completeness"], t_field["completeness"])
        result = d1.phase2([r_field], [t_field])
        self.assertFalse(result["has_unresolved_impact"])


class Phase1Tests(unittest.TestCase):
    def test_version_change_is_detected(self):
        gate = d1.phase1(
            d1.project_repository(_repo_index("17.0.0.171"))["modules"]["smart_construction_core"],
            d1.project_repository(_repo_index("17.0.0.172"))["modules"]["smart_construction_core"],
        )
        self.assertTrue(gate["version_changed"])
        self.assertTrue(gate["phase1_changed"])

    def test_file_only_change_is_not_fact_change(self):
        before = d1.project_repository(_repo_index(file_digests={"boq.py": "f1"}))["modules"]["smart_construction_core"]
        after = d1.project_repository(_repo_index(file_digests={"boq.py": "f2"}))["modules"]["smart_construction_core"]
        gate = d1.phase1(before, after)
        self.assertTrue(gate["file_digests_changed"])
        self.assertFalse(gate["fact_digest_changed"])
        self.assertFalse(gate["version_changed"])


class Phase2Tests(unittest.TestCase):
    def test_added_removed_changed_facts(self):
        before = [{"fact_identity": "field:m:f", "value": {"type": "Char"}},
                  {"fact_identity": "field:m:gone", "value": {"type": "Char"}}]
        after = [{"fact_identity": "field:m:f", "value": {"type": "Integer"}},
                 {"fact_identity": "field:m:new", "value": {"type": "Char"}}]
        result = d1.phase2(before, after)
        by_ident = {c["fact_identity"]: c["change"] for c in result["changes"]}
        self.assertEqual(by_ident, {"field:m:f": "changed", "field:m:gone": "removed",
                                    "field:m:new": "added"})
        self.assertFalse(result["has_unresolved_impact"])

    def test_missing_identity_is_unresolved(self):
        result = d1.phase2([{"value": {"x": 1}}], [{"value": {"x": 2}}])
        self.assertTrue(result["has_unresolved_impact"])
        self.assertEqual(len(result["unresolved"]), 2)


class EndToEndTests(unittest.TestCase):
    def test_diff_detects_cross_mode_version_change(self):
        before = d1.project_repository(_repo_index("17.0.0.171"))
        after = d1.project_runtime(_runtime("17.0.0.172"))
        result = d1.diff_projections(before, after)
        self.assertIn("smart_construction_core", result["phase1_changed_modules"])


class SemanticDiffTests(unittest.TestCase):
    def _field(self, **overrides):
        fact = {"fact_identity": "field:project.project:name", "asset_type": "field",
                "asset_modules": ["smart_construction_core"],
                "value": {"name": "name", "type": "Char", "relation": "",
                          "required": False, "readonly": False, "compute": False,
                          "related": False}}
        fact["value"].update(overrides)
        return fact

    def test_field_type_change_is_explained(self):
        before = self._field(type="Char")
        after = self._field(type="Integer")
        sem = d1.semantic_diff(before, after)
        self.assertIn("type", [x["attribute"] for x in sem["detail"]])
        self.assertFalse(sem["content_unresolved"])

    def test_field_relation_change_is_explained(self):
        before = self._field(type="Many2one", relation="")
        after = self._field(type="Many2one", relation="project.project")
        sem = d1.semantic_diff(before, after)
        self.assertIn("relation", [x["attribute"] for x in sem["detail"]])
        self.assertNotIn("type", [x["attribute"] for x in sem["detail"]])

    def test_view_inherit_change_is_explained(self):
        before = {"fact_identity": "view:m:myview", "asset_type": "view",
                  "asset_modules": ["smart_construction_core"],
                  "value": {"name": "myview", "model": "m", "inherit_id": 10}}
        after = dict(before)
        after["value"] = {**before["value"], "inherit_id": 20}
        sem = d1.semantic_diff(before, after)
        self.assertIn("inherit_id", [x["attribute"] for x in sem["detail"]])

    def test_action_res_model_change_is_explained(self):
        before = {"fact_identity": "action:m:act", "asset_type": "action",
                  "asset_modules": ["smart_construction_core"],
                  "value": {"name": "act", "res_model": "project.project", "view_mode": "form"}}
        after = dict(before)
        after["value"] = {**before["value"], "res_model": "project.task"}
        sem = d1.semantic_diff(before, after)
        self.assertIn("res_model", [x["attribute"] for x in sem["detail"]])

    def test_acl_group_change_is_explained(self):
        before = {"fact_identity": "acl:m:1,0,0,0", "asset_type": "security",
                  "asset_modules": ["smart_construction_core"],
                  "value": {"model": "m", "perm_read": True, "perm_write": False,
                            "perm_create": False, "perm_unlink": False, "group_id": 10}}
        after = dict(before)
        after["value"] = {**before["value"], "group_id": 20}
        sem = d1.semantic_diff(before, after)
        self.assertIn("group_id", [x["attribute"] for x in sem["detail"]])

    def test_model_owner_unchanged_but_extension_added(self):
        before = {"fact_identity": "model:m", "asset_type": "model",
                  "asset_modules": ["project"], "model_owner": "project", "model_extensions": [],
                  "value": {"name": "m", "model_owner": "project", "model_extensions": [],
                            "registry_modules": ["project"]}}
        after = {"fact_identity": "model:m", "asset_type": "model",
                 "asset_modules": ["project", "smart_construction_core"], "model_owner": "project",
                 "model_extensions": ["smart_construction_core"],
                 "value": {"name": "m", "model_owner": "project",
                           "model_extensions": ["smart_construction_core"],
                           "registry_modules": ["project", "smart_construction_core"]}}
        sem = d1.semantic_diff(before, after)
        attrs = [x["attribute"] for x in sem["detail"]]
        self.assertIn("model_extensions", attrs)
        self.assertNotIn("model_owner", attrs)

    def test_multi_module_contribution_is_not_collapsed(self):
        proj = d1.project_runtime(_runtime(
            ownership=[{"model": "project.project", "registry_modules": ["project"],
                        "model_owner": "project", "model_extensions": []}],
            fields=[{"model": "project.project", "name": "name", "ttype": "Char",
                     "relation": "", "required": False, "readonly": False,
                     "compute": False, "related": False,
                     "modules": ["project", "smart_construction_core"]}]))
        fact = next(f for f in proj["modules"]["project"]["facts"] if f["kind"] == "field")
        self.assertEqual(fact["asset_modules"], ["project", "smart_construction_core"])
        self.assertEqual(len(fact["asset_modules"]), 2)

    def test_same_count_but_asset_replaced_is_detected(self):
        before = [{"fact_identity": "action:m:actA", "asset_type": "action",
                   "asset_modules": ["x"], "value": {"res_model": "m", "view_mode": "form"}}]
        after = [{"fact_identity": "action:m:actB", "asset_type": "action",
                  "asset_modules": ["x"], "value": {"res_model": "m", "view_mode": "form"}}]
        result = d1.phase2(before, after)
        by_ident = {c["fact_identity"]: c["change"] for c in result["changes"]}
        self.assertEqual(by_ident, {"action:m:actA": "removed", "action:m:actB": "added"})

    def test_content_unresolved_when_no_semantic_schema(self):
        before = {"fact_identity": "x:1", "asset_type": "unknown",
                  "asset_modules": ["m"], "value": {"a": 1}}
        after = {"fact_identity": "x:1", "asset_type": "unknown",
                 "asset_modules": ["m"], "value": {"a": 2}}
        sem = d1.semantic_diff(before, after)
        self.assertTrue(sem["content_unresolved"])

    def test_menu_sequence_change_is_explained(self):
        before = {"fact_identity": "menu:my menu:3", "asset_type": "menu",
                  "asset_modules": ["smart_construction_core"],
                  "value": {"name": "my menu", "parent_id": 3, "action": "ir.actions.act_window,1",
                            "groups_id": [1], "sequence": 10}}
        after = dict(before)
        after["value"] = {**before["value"], "sequence": 20}
        sem = d1.semantic_diff(before, after)
        self.assertIn("sequence", [x["attribute"] for x in sem["detail"]])

    def test_record_rule_domain_change_is_explained(self):
        before = {"fact_identity": "rule:project.project:my rule", "asset_type": "rule",
                  "asset_modules": ["smart_construction_core"],
                  "value": {"model": "project.project", "name": "my rule",
                            "domain": "[('id','>',0)]", "groups": [1]}}
        after = dict(before)
        after["value"] = {**before["value"], "domain": "[('id','=',1)]"}
        sem = d1.semantic_diff(before, after)
        self.assertIn("domain", [x["attribute"] for x in sem["detail"]])

    def test_record_rule_group_change_is_explained(self):
        before = {"fact_identity": "rule:m:r", "asset_type": "rule",
                  "asset_modules": ["x"],
                  "value": {"model": "m", "name": "r", "domain": "[]", "groups": [1]}}
        after = dict(before)
        after["value"] = {**before["value"], "groups": [1, 2]}
        sem = d1.semantic_diff(before, after)
        self.assertIn("groups", [x["attribute"] for x in sem["detail"]])

    def test_intent_handler_change_is_explained(self):
        before = {"fact_identity": "intent:ui.contract:capability_describe", "asset_type": "intent",
                  "asset_modules": ["smart_construction_core"],
                  "value": {"intent": "ui.contract", "handler": "CapabilityDescribeHandler",
                            "module": "smart_construction_core"}}
        after = dict(before)
        after["value"] = {**before["value"], "handler": "CapabilityDescribeV2Handler"}
        sem = d1.semantic_diff(before, after)
        self.assertIn("handler", [x["attribute"] for x in sem["detail"]])

    def test_action_context_change_is_explained(self):
        before = {"fact_identity": "action:m:act", "asset_type": "action",
                  "asset_modules": ["x"],
                  "value": {"name": "act", "res_model": "m", "view_mode": "form",
                            "context": "{}", "groups_id": [1]}}
        after = dict(before)
        after["value"] = {**before["value"], "context": "{'default_x':1}"}
        sem = d1.semantic_diff(before, after)
        self.assertIn("context", [x["attribute"] for x in sem["detail"]])

    def test_view_arch_digest_change_is_explained(self):
        before = {"fact_identity": "view:m:v", "asset_type": "view",
                  "asset_modules": ["x"],
                  "value": {"name": "v", "model": "m", "inherit_id": 5, "arch_digest": "a"}}
        after = dict(before)
        after["value"] = {**before["value"], "arch_digest": "b"}
        sem = d1.semantic_diff(before, after)
        self.assertIn("arch_digest", [x["attribute"] for x in sem["detail"]])

    def test_model_extensions_distinct_from_registry_contributions(self):
        proj = d1.project_runtime(_runtime(ownership=[
            {"model": "project.project",
             "registry_modules": ["project", "smart_construction_core"],
             "model_owner": "project", "model_extensions": ["smart_construction_core"],
             "inherit_module_facts": {"project.project": "smart_construction_core"}}]))
        fact = next(f for f in proj["modules"]["project"]["facts"] if f["kind"] == "model")
        self.assertEqual(fact["model_owner"], "project")
        self.assertEqual(fact["model_extensions"], ["smart_construction_core"])
        self.assertEqual(fact["asset_modules"], ["project", "smart_construction_core"])
        self.assertNotEqual(fact["asset_modules"], fact["model_extensions"])

    def test_model_extensions_incomplete_when_contribution_unmapped(self):
        proj = d1.project_runtime(_runtime(ownership=[
            {"model": "project.project",
             "registry_modules": ["project", "smart_construction_core", "customer_custom"],
             "model_owner": "project", "model_extensions": ["smart_construction_core"],
             "inherit_module_facts": {"project.project": "smart_construction_core"}}]))
        fact = next(f for f in proj["modules"]["project"]["facts"] if f["kind"] == "model")
        self.assertTrue(fact["model_extensions_incomplete"])
        self.assertEqual(fact["unaccounted_contributions"], ["customer_custom"])


if __name__ == "__main__":
    unittest.main()
