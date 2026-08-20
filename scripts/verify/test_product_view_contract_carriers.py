from __future__ import annotations

import unittest
from copy import deepcopy
from pathlib import Path

import yaml

from scripts.contract.complete_worktree_fingerprint import EXCLUDED_PATHS
from scripts.contract.product_view_contract_carriers_common import (
    assert_system_identity,
    sha256_json,
    stable_selector_payload,
    with_manifest,
)
from scripts.verify.product_view_contract_carriers_guard import validate_carriers


ROOT = Path(__file__).resolve().parents[2]


class ProductViewContractCarriersTests(unittest.TestCase):
    def setUp(self) -> None:
        entries = [{"path": "x", "tracked": True, "mode": "100644", "index_blob": "a" * 40, "worktree_kind": "file", "worktree_sha256": "1" * 64}]
        canonical_fingerprint = {
            "algorithm": "codex_complete_worktree_fingerprint/v1",
            "branch": "feature/test",
            "git_head": "1" * 40,
            "baseline_sha": "2" * 40,
            "scope_manifest_sha256": sha256_json(entries),
            "excluded_paths": EXCLUDED_PATHS,
            "entries": entries,
        }
        self.fingerprint = {**canonical_fingerprint, "digest": sha256_json(canonical_fingerprint)}
        fp = {key: self.fingerprint[key] for key in ("algorithm", "git_head", "baseline_sha", "scope_manifest_sha256", "digest")}
        self.surface = {
            "contract_ref": "menu.x::form",
            "menu_xmlid": "x.menu",
            "action_xmlid": "x.action",
            "model": "x.model",
            "view_type": "form",
            "view_ref": "x.view",
            "source_kind": "database_view",
            "hashes": {"source_graph_sha256": "5" * 64, "resolved_arch_sha256": "6" * 64, "semantic_structure_sha256": "7" * 64},
        }
        module_set = [{"name": "base", "installed_version": "17.0"}]
        self.structure = with_manifest({
            "schema": "product_view_structure_contract/v1",
            "authority": {"candidate_fingerprint": fp, "formal_menu_policy_sha256": "b" * 64, "module_set_sha256": sha256_json(module_set), "user": "__system__", "company": "base.main_company", "language": "en_US", "group_profile": ["base.group_system"]},
            "summary": {"formal_menu_count": 1, "model_count": 1, "resolved_surface_count": 1},
            "entries": [{"surfaces": [self.surface]}],
        })
        self.authority = {
            "branch": "feature/test", "candidate_fingerprint": fp, "runtime_profile": "local.clean", "compose_project": "sc-local-clean", "database": "sc_clean", "database_filter": "^sc_clean$", "demo_data": False,
            "module_set": module_set, "module_set_sha256": sha256_json(module_set), "user": "__system__", "company": "base.main_company", "language": "en_US", "group_profile": ["base.group_system"],
            "handler": "odoo.addons.smart_core.handlers.load_contract.LoadContractHandler", "capture_mode": "final_response_rollback_sandbox", "force_refresh": True, "external_contract_service_absent": True, "exporter_version": "product_view_contract_carriers/v1",
            "capture_transaction_strategy": "dedicated_cursor_rollback",
        }
        value = {"model": "x.model", "view_type": "form", "layout": {}, "statusbar": {}, "header_buttons": [], "field_modifiers": {}, "subviews": {}, "capabilities": {}}
        entry = {
            **self.surface,
            "runtime_binding": {"menu_id": 1, "action_id": 2, "requested_view_id": 3, "selector_sha256": ""},
            "request": {"menu_id": 1, "action_id": 2, "model": "x.model", "view_type": "form", "include": "all", "force_refresh": True, "context": {"requested_view_id": 3}},
            "response": {"status": "success", "code": 200, "source_authority": "load_contract_final_response", "etag": "", "degraded": False, "warnings": []},
            "normalized_carriers": [{"source_selector": "/data/views/form", "artifact_selector": "/entries/0/normalized_carriers/0/value", "source_authority": "normalized_contract", "value": value, "value_hash": sha256_json(value)}],
            "semantic_carriers": [],
            "capture_outcome": {"status": "normalized_only", "reason_code": "CAPABILITY_SEMANTIC_CARRIER_MISSING"},
        }
        entry["runtime_binding"]["selector_sha256"] = sha256_json(stable_selector_payload(entry, self.authority))
        self.artifact = with_manifest({
            "schema": "product_view_contract_carriers/v1",
            "authority": self.authority,
            "structure_input": {"path": "artifacts/contract/product_view_structure_contract.json", "sha256": "a" * 64, "manifest_sha256": self.structure["manifest_sha256"], "candidate_fingerprint": fp, "formal_menu_policy_sha256": "b" * 64, "expected_formal_menu_count": 1, "expected_model_count": 1, "expected_surface_count": 1},
            "summary": {"formal_menu_count": 1, "model_count": 1, "surface_count": 1, "complete_count": 0, "normalized_only_count": 1, "error_count": 0, "normalized_carrier_count": 1, "semantic_carrier_count": 0, "view_type_counts": {"form": 1}},
            "entries": [entry],
        })
        self.schema = yaml.safe_load((ROOT / "contracts/schemas/product-view-contract-carriers-v1.yaml").read_text(encoding="utf-8"))

    def errors(self, artifact=None):
        return validate_carriers(artifact or self.artifact, self.structure, self.fingerprint, self.schema, "a" * 64, self.fingerprint)

    def test_minimal_normalized_only_carrier_is_valid(self) -> None:
        self.assertEqual(self.errors(), [])

    def test_manifest_drift_fails(self) -> None:
        value = deepcopy(self.artifact)
        value["summary"]["surface_count"] = 2
        self.assertTrue(any("manifest" in error for error in self.errors(value)))

    def test_structure_hash_drift_fails(self) -> None:
        value = deepcopy(self.artifact)
        value["entries"][0]["hashes"]["resolved_arch_sha256"] = "c" * 64
        value = with_manifest(value)
        self.assertTrue(any("structure field mismatch" in error for error in self.errors(value)))

    def test_numeric_runtime_ids_do_not_change_stable_selector(self) -> None:
        value = deepcopy(self.artifact["entries"][0])
        before = sha256_json(stable_selector_payload(value, self.authority))
        value["runtime_binding"].update(menu_id=99, action_id=98, requested_view_id=97)
        value["request"].update(menu_id=99, action_id=98, context={"requested_view_id": 97})
        self.assertEqual(before, sha256_json(stable_selector_payload(value, self.authority)))

    def test_semantic_producer_mismatch_fails(self) -> None:
        value = deepcopy(self.artifact)
        semantic = {"version": "v1", "source": "other", "model": "x.model", "view_type": "form"}
        value["entries"][0]["semantic_carriers"] = [{"source_selector": "/data/semantic_page", "artifact_selector": "/entries/0/semantic_carriers/0/value", "source_authority": "semantic_page", "value": semantic, "value_hash": sha256_json(semantic)}]
        value["entries"][0]["capture_outcome"] = {"status": "complete", "reason_code": ""}
        value["summary"].update(complete_count=1, normalized_only_count=0, semantic_carrier_count=1)
        value = with_manifest(value)
        self.assertTrue(any("semantic producer mismatch" in error for error in self.errors(value)))

    def test_normalized_source_selector_tampering_fails(self) -> None:
        value = deepcopy(self.artifact)
        value["entries"][0]["normalized_carriers"][0]["source_selector"] = "/data/native_view/views/form"
        value = with_manifest(value)
        self.assertTrue(any("source selector" in error for error in self.errors(value)))

    def test_normalized_identity_tampering_fails(self) -> None:
        value = deepcopy(self.artifact)
        carrier = value["entries"][0]["normalized_carriers"][0]
        carrier["value"]["model"] = "other.model"
        carrier["value_hash"] = sha256_json(carrier["value"])
        value = with_manifest(value)
        self.assertTrue(any("identity mismatch" in error for error in self.errors(value)))

    def test_runtime_authority_tampering_fails(self) -> None:
        value = deepcopy(self.artifact)
        value["authority"]["language"] = "zh_CN"
        value["entries"][0]["runtime_binding"]["selector_sha256"] = sha256_json(stable_selector_payload(value["entries"][0], value["authority"]))
        value = with_manifest(value)
        self.assertTrue(any("differs from structure" in error for error in self.errors(value)))

    def test_stale_internally_valid_fingerprint_fails(self) -> None:
        current = deepcopy(self.fingerprint)
        current["git_head"] = "f" * 40
        canonical = {key: current[key] for key in ("algorithm", "git_head", "baseline_sha", "branch", "scope_manifest_sha256", "excluded_paths", "entries")}
        current["digest"] = sha256_json(canonical)
        errors = validate_carriers(self.artifact, self.structure, self.fingerprint, self.schema, "a" * 64, current)
        self.assertTrue(any("current complete worktree" in error for error in errors))

    def test_response_fallback_warning_fails(self) -> None:
        value = deepcopy(self.artifact)
        value["entries"][0]["response"]["warnings"] = ["view_contract_fallback:form"]
        value = with_manifest(value)
        self.assertTrue(any("fallback warning" in error for error in self.errors(value)))

    def test_structure_expected_count_tampering_fails(self) -> None:
        value = deepcopy(self.artifact)
        value["structure_input"]["expected_surface_count"] = 2
        value = with_manifest(value)
        self.assertTrue(any("expected_surface_count" in error for error in self.errors(value)))

    def test_semantic_scalar_fails_closed(self) -> None:
        value = deepcopy(self.artifact)
        carrier = {"source_selector": "/data/semantic_page", "artifact_selector": "/entries/0/semantic_carriers/0/value", "source_authority": "semantic_page", "value": "bad", "value_hash": sha256_json("bad")}
        value["entries"][0]["semantic_carriers"] = [carrier]
        value["entries"][0]["capture_outcome"] = {"status": "complete", "reason_code": ""}
        value["summary"].update(complete_count=1, normalized_only_count=0, semantic_carrier_count=1)
        value = with_manifest(value)
        self.assertTrue(any("semantic" in error for error in self.errors(value)))

    def test_system_identity_requires_exact_superuser_uid(self) -> None:
        assert_system_identity(1, 1, "__system__")
        with self.assertRaises(ValueError):
            assert_system_identity(2, 1, "__system__")

    def test_synthetic_default_view_rejects_runtime_view_id(self) -> None:
        value = deepcopy(self.artifact)
        entry = value["entries"][0]
        entry["source_kind"] = "synthetic_default_view"
        entry["runtime_binding"]["requested_view_id"] = 0
        entry["request"]["context"] = {}
        value = with_manifest(value)
        structure = deepcopy(self.structure)
        structure["entries"][0]["surfaces"][0]["source_kind"] = "synthetic_default_view"
        structure = with_manifest(structure)
        value["structure_input"]["manifest_sha256"] = structure["manifest_sha256"]
        value = with_manifest(value)
        errors = validate_carriers(value, structure, self.fingerprint, self.schema, "a" * 64, self.fingerprint)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
