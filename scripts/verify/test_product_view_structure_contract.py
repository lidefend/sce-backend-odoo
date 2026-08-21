from __future__ import annotations

from copy import deepcopy
import unittest

from scripts.contract.complete_worktree_fingerprint import EXCLUDED_PATHS, validate_fingerprint
from scripts.contract.product_view_structure_common import (
    FINGERPRINT_SCHEMA, collect_occurrences, collect_references, content_digest,
    normalize_arch, policy_menu_rows, resolve_odoo17_view, sha256_json,
)
from scripts.verify.product_view_structure_contract_guard import validate_manifest


class ProductViewStructureContractTests(unittest.TestCase):
    def test_schema_uses_semantic_version_and_has_no_v1_alias(self):
        from scripts.contract.product_view_structure_common import SCHEMA

        self.assertEqual(SCHEMA, "product_view_structure_contract/1.0.0")
        self.assertNotIn("/v1", SCHEMA)

    def setUp(self):
        self.policy = {"products": [{"capabilities": [{"enabled": True, "release_state": "released", "menu_xmlid": "x.menu", "res_model": "x.model"}]}]}
        entries = [{"path": "x", "tracked": True, "mode": "100644", "index_blob": "a" * 40, "worktree_kind": "file", "worktree_sha256": "1" * 64}]
        canonical = {"algorithm": FINGERPRINT_SCHEMA, "git_head": "2" * 64, "baseline_sha": "3" * 64, "branch": "feature/x", "scope_manifest_sha256": sha256_json(entries), "excluded_paths": EXCLUDED_PATHS, "entries": entries}
        self.fingerprint = {**canonical, "digest": sha256_json(canonical)}
        semantic = normalize_arch('<form><field name="name"/><field name="name"/><button name="go" type="object"/></form>', semantic=True)
        resolved = normalize_arch('<form data-native="x"><field name="name"/><field name="name"/><button name="go" type="object"/></form>', semantic=False)
        occurrences = collect_occurrences(semantic, "x.view")
        graph_body = {"root_ref": "x.view", "contributors": [{"view_ref": "x.view", "inherit_ref": "", "mode": "primary", "priority": 16, "active": True, "groups": [], "arch_sha256": "4" * 64, "applicability": "applied"}], "edges": [], "application_order": ["x.view"]}
        graph = {**graph_body, "graph_sha256": sha256_json(graph_body)}
        surface = {"contract_ref": "x.menu::form", "menu_xmlid": "x.menu", "action_xmlid": "x.action", "model": "x.model", "view_type": "form", "view_ref": "x.view", "source_kind": "database_view", "hashes": {"source_graph_sha256": graph["graph_sha256"], "resolved_arch_sha256": sha256_json(resolved), "semantic_structure_sha256": sha256_json(semantic)}, "source_graph": graph, "parse_outcome": {"primary": "success", "fallback": "inactive"}, "references": collect_references(occurrences), "occurrences": occurrences, "resolved_structure": resolved, "semantic_structure": semantic}
        authority = {"branch": "feature/x", "candidate_fingerprint": {key: self.fingerprint[key] for key in ("algorithm", "git_head", "baseline_sha", "scope_manifest_sha256", "digest")}, "database_policy_path": "docs/governance/database_architecture_policy.md", "database_policy_sha256": "6" * 64, "formal_menu_policy_path": "scripts/verify/baselines/formal_business_product_menu_policy_v1.json", "formal_menu_policy_sha256": "5" * 64, "runtime_profile": "local.clean", "compose_project": "sc-local-clean", "database": "sc_clean", "database_filter": "^sc_clean$", "demo_data": False, "module_set": [{"name": "base", "installed_version": "1"}], "module_set_sha256": sha256_json([{"name": "base", "installed_version": "1"}]), "user": "admin", "company": "base.main_company", "language": "en_US", "group_profile": ["base.group_user"], "exporter_version": "product_view_structure_contract/1.0.0", "runtime_source": "odoo.get_view_resolved_arch_and_native_inheritance_engine"}
        self.manifest = {"schema": "product_view_structure_contract/1.0.0", "authority": authority, "summary": {"formal_menu_count": 1, "resolved_view_action_count": 1, "non_view_action_count": 0, "error_count": 0, "resolved_surface_count": 1, "model_count": 1, "view_type_counts": {"form": 1}}, "entries": [{"menu_xmlid": "x.menu", "res_model": "x.model", "status": "resolved_view_action", "declared_view_types": ["form"], "surfaces": [surface]}]}
        self.manifest["manifest_sha256"] = content_digest(self.manifest, "manifest_sha256")

    def errors(self, manifest=None):
        return validate_manifest(manifest or self.manifest, self.policy, "5" * 64, "6" * 64, self.fingerprint)

    def test_valid_nonzero_manifest(self):
        self.assertEqual(self.errors(), [])

    def test_duplicate_fields_keep_distinct_occurrences(self):
        rows = self.manifest["entries"][0]["surfaces"][0]["references"]["field_occurrences"]
        self.assertEqual([row["occurrence_index"] for row in rows], [1, 2])
        self.assertNotEqual(rows[0]["locator"], rows[1]["locator"])

    def test_semantic_hash_covers_column_invisible(self):
        left = normalize_arch('<tree><field name="x"/></tree>', semantic=True)
        right = normalize_arch('<tree><field name="x" column_invisible="1"/></tree>', semantic=True)
        self.assertNotEqual(sha256_json(left), sha256_json(right))

    def test_empty_policy_fails(self):
        with self.assertRaises(ValueError):
            policy_menu_rows({"products": []})

    def test_zero_surfaces_fails(self):
        value = deepcopy(self.manifest)
        value["entries"][0]["surfaces"] = []
        self.assertTrue(any("zero surfaces" in error or "non-zero" in error for error in self.errors(value)))

    def test_list_view_type_fails(self):
        value = deepcopy(self.manifest)
        value["entries"][0]["declared_view_types"] = ["list"]
        value["entries"][0]["surfaces"][0]["view_type"] = "list"
        self.assertTrue(any("non-canonical" in error for error in self.errors(value)))

    def test_duplicate_contract_ref_fails(self):
        value = deepcopy(self.manifest)
        value["entries"][0]["surfaces"].append(deepcopy(value["entries"][0]["surfaces"][0]))
        self.assertTrue(any("duplicate contract_ref" in error for error in self.errors(value)))

    def test_structure_tampering_fails(self):
        value = deepcopy(self.manifest)
        value["entries"][0]["surfaces"][0]["semantic_structure"]["attrs"] = {"string": "tampered"}
        self.assertTrue(any("semantic structure hash" in error for error in self.errors(value)))

    def test_source_graph_tampering_fails(self):
        value = deepcopy(self.manifest)
        value["entries"][0]["surfaces"][0]["source_graph"]["application_order"] = []
        self.assertTrue(any("source graph" in error for error in self.errors(value)))

    def test_policy_hash_mismatch_fails(self):
        value = deepcopy(self.manifest)
        value["authority"]["formal_menu_policy_sha256"] = "0" * 64
        self.assertTrue(any("formal menu policy hash" in error for error in self.errors(value)))

    def test_candidate_fingerprint_mismatch_fails(self):
        value = deepcopy(self.manifest)
        value["authority"]["candidate_fingerprint"]["digest"] = "0" * 64
        self.assertTrue(any("candidate fingerprint" in error for error in self.errors(value)))

    def test_evidence_carrier_head_change_preserves_identical_scope(self):
        current = deepcopy(self.fingerprint)
        current["git_head"] = "9" * 64
        canonical = {key: current[key] for key in ("algorithm", "git_head", "baseline_sha", "branch", "scope_manifest_sha256", "excluded_paths", "entries")}
        current["digest"] = sha256_json(canonical)
        self.assertEqual(
            validate_manifest(self.manifest, self.policy, "5" * 64, "6" * 64, current),
            [],
        )

    def test_evidence_carrier_scope_change_fails(self):
        current = deepcopy(self.fingerprint)
        current["scope_manifest_sha256"] = "9" * 64
        self.assertTrue(any("scope_manifest_sha256" in error for error in validate_manifest(self.manifest, self.policy, "5" * 64, "6" * 64, current)))

    def test_fingerprint_digest_tampering_fails(self):
        value = deepcopy(self.fingerprint)
        value["digest"] = "0" * 64
        self.assertTrue(validate_fingerprint(value))

    def test_fingerprint_rejects_broad_or_missing_exclusion(self):
        value = deepcopy(self.fingerprint)
        value["excluded_paths"] = [{"path": "contracts/generated", "reason": "broad"}]
        self.assertTrue(any("exclusions" in error for error in validate_fingerprint(value)))

    def test_summary_tampering_fails(self):
        value = deepcopy(self.manifest)
        value["summary"]["resolved_surface_count"] = 2
        self.assertTrue(any("summary" in error for error in self.errors(value)))

    def test_manifest_hash_tampering_fails(self):
        value = deepcopy(self.manifest)
        value["manifest_sha256"] = "0" * 64
        self.assertTrue(any("manifest hash" in error for error in self.errors(value)))

    def test_odoo17_explicit_view_is_passed_to_both_layers(self):
        model = _FakeModel(public_id=17, native_id=17)
        result = resolve_odoo17_view(model, 17, "form")
        self.assertEqual(result[3], "database_view")
        self.assertEqual(model.calls, [("native", {"view_type": "form", "view_id": 17}), ("public", {"view_type": "form", "view_id": 17})])

    def test_odoo17_default_selection_omits_view_id(self):
        model = _FakeModel(public_id=18, native_id=18)
        result = resolve_odoo17_view(model, 0, "tree")
        self.assertEqual(result[3], "database_view")
        self.assertEqual(model.calls, [("native", {"view_type": "tree"}), ("public", {"view_type": "tree"})])

    def test_odoo17_synthetic_default_accepts_false_id(self):
        result = resolve_odoo17_view(_FakeModel(public_id=False, native_id=False), 0, "search")
        self.assertEqual(result[3], "synthetic_default_view")

    def test_odoo17_public_native_id_mismatch_fails(self):
        with self.assertRaisesRegex(ValueError, "public/native selected view mismatch"):
            resolve_odoo17_view(_FakeModel(public_id=17, native_id=18), 0, "form")


class _FakeView:
    def __init__(self, view_id):
        self.id = view_id


class _FakeModel:
    def __init__(self, public_id, native_id):
        self.public_id = public_id
        self.native_id = native_id
        self.calls = []

    def _get_view(self, **kwargs):
        self.calls.append(("native", kwargs))
        return object(), _FakeView(self.native_id)

    def get_view(self, **kwargs):
        self.calls.append(("public", kwargs))
        return {"id": self.public_id, "arch": "<form/>"}


if __name__ == "__main__":
    unittest.main()
