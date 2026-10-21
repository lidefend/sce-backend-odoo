import hashlib
import ast
import json
from pathlib import Path
import tempfile
import unittest

from scripts.verify.capability_maturity_evidence import ACCEPTANCE_CONTRACTS, ROOT, gate, verify_bundle


class EvidenceBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "implementation.py").write_text("declared implementation")
        self.bundle = self.root / "bundle.json"
        dependency = hashlib.sha256((self.root / "implementation.py").read_bytes()).hexdigest()
        criteria = {"preview": {"read": ["open"]}, "standard": {"read": ["open"], "write": ["roundtrip"]}}
        dependencies = {"implementation.py": dependency}
        fingerprint = gate.maturity_fingerprint("example.query", dependencies, criteria)
        artifact = json.dumps({"capability_key": "example.query", "fingerprint": fingerprint,
                               "check_id": "read", "cases": [{"id": "open", "status": "pass"}]}).encode()
        (self.root / "result.json").write_bytes(artifact)
        digest = hashlib.sha256(artifact).hexdigest()
        self.data = {"schema": "capability.maturity.evidence.v2", "artifacts": {digest: "result.json"},
                     "capabilities": [{"capability_key": "example.query", "dependencies": dependencies,
                                       "criteria": criteria, "receipts": [{"check_id": "read",
                                       "capability_key": "example.query", "fingerprint": fingerprint,
                                       "artifact_sha256": digest}]}]}
        self.write_authority()

    def write_authority(self):
        capability = self.data["capabilities"][0]
        scenario = {"role_code": "reader", "operation": "submit", "company_scope": "company-a",
                    "data_scope": "own-project", "record_state": "draft",
                    "expected": {"decision": "deny", "reason_code": "ACCESS_DENIED",
                                 "business_effect": {"records_changed": 0, "state": "draft"}}}
        self.contract = {"product_dependencies": ["implementation.py"], "product_criteria": capability["criteria"],
                         "authorization_dependencies": ["authorization.json"],
                         "business_scenarios": {"reader-cannot-submit": scenario}}
        self.authority = self.root / ACCEPTANCE_CONTRACTS
        self.authority.parent.mkdir(parents=True)
        self.authority.write_text(json.dumps({"schema": "capability.acceptance.contracts.v1",
            "capabilities": {"example.query": self.contract}}))

    def add_handling(self):
        capability = self.data["capabilities"][0]
        scenario = {"role_code": "reader", "principal_fingerprint": "c" * 64,
                    "operation": "submit", "company_scope": "company-a", "data_scope": "own-project",
                    "record_state": "draft", "expected": {"decision": "deny", "reason_code": "ACCESS_DENIED",
                    "business_effect": {"records_changed": 0, "state": "draft"}}}
        scenarios = {"reader-cannot-submit": scenario}
        dependencies = capability["dependencies"]
        (self.root / "authorization.json").write_text("declared native authorization inputs")
        authorization = {"authorization.json": hashlib.sha256((self.root / "authorization.json").read_bytes()).hexdigest()}
        identity = gate.business_handling_identity("example.query", dependencies, authorization, scenarios)
        fingerprint = gate.maturity_fingerprint(**identity)
        payload = {"capability_key": identity["capability_key"], "fingerprint": fingerprint,
                   "check_id": "business_handling", "cases": [{"id": "reader-cannot-submit", "status": "pass",
                   "observed_context": {k: v for k, v in scenario.items() if k != "expected"},
                   "observed": scenario["expected"]}]}
        raw = json.dumps(payload).encode()
        digest = hashlib.sha256(raw).hexdigest()
        (self.root / "handling.json").write_bytes(raw)
        self.data["artifacts"][digest] = "handling.json"
        capability["role_business_handling"] = {"authorization_dependencies": authorization, "scenarios": scenarios,
            "receipts": [{"capability_key": identity["capability_key"], "fingerprint": fingerprint,
                          "check_id": "business_handling", "artifact_sha256": digest}]}

    def test_product_only_evidence_does_not_prove_role_business_handling(self):
        result = self.run_bundle()
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["status_scope"], "requested_edition_product_qualification")
        self.assertFalse(result["scoped_correctness_verified"])
        row = result["capabilities"][0]
        self.assertTrue(row["product_eligible"])
        self.assertFalse(row["role_business_handling"]["verified"])
        self.assertNotIn("publishable", row)

    def test_business_context_change_does_not_change_product_maturity(self):
        self.add_handling()
        self.data["capabilities"][0]["role_business_handling"]["scenarios"]["reader-cannot-submit"]["company_scope"] = "company-b"
        result = self.run_bundle()
        self.assertTrue(result["capabilities"][0]["product_eligible"])
        self.assertFalse(result["capabilities"][0]["role_business_handling"]["verified"])

    def test_role_evidence_does_not_replace_product_evidence(self):
        self.add_handling()
        self.data["capabilities"][0]["receipts"] = []
        result = self.run_bundle()
        self.assertTrue(result["capabilities"][0]["role_business_handling"]["verified"])
        self.assertFalse(result["capabilities"][0]["scoped_correctness_verified"])

    def test_stale_authorization_files_do_not_erase_product_result(self):
        self.add_handling()
        (self.root / "authorization.json").write_text("changed native permissions")
        result = self.run_bundle()
        self.assertTrue(result["capabilities"][0]["product_eligible"])
        self.assertFalse(result["capabilities"][0]["role_business_handling"]["verified"])
        self.assertEqual(result["status"], "pass")
        self.assertFalse(result["scoped_correctness_verified"])

    def run_bundle(self, edition="preview"):
        self.bundle.write_text(json.dumps(self.data))
        return verify_bundle(self.bundle, edition=edition, repository=self.root)

    def test_preview_pass_does_not_publish_or_claim_standard_readiness(self):
        self.add_handling()
        result = self.run_bundle()
        self.assertEqual(result["status"], "pass")
        self.assertFalse(result["publication_performed"])
        self.assertEqual(self.run_bundle("standard")["status"], "blocked")

    def test_current_source_must_match_recorded_dependency(self):
        (self.root / "implementation.py").write_text("changed implementation")
        with self.assertRaisesRegex(ValueError, "CANDIDATE_DEPENDENCY_CHANGED"):
            self.run_bundle()

    def test_artifact_tampering_blocks_requested_release(self):
        (self.root / "result.json").write_text("{}")
        self.assertEqual(self.run_bundle()["status"], "blocked")

    def test_empty_and_duplicate_capability_scope_rejected(self):
        row = self.data["capabilities"][0]
        for rows in ([], [row, row]):
            with self.subTest(rows=rows):
                self.data["capabilities"] = rows
                with self.assertRaises(ValueError):
                    self.run_bundle()

    def test_artifact_path_escape_rejected(self):
        digest = next(iter(self.data["artifacts"]))
        for path in ("../outside.json", "/etc/passwd"):
            with self.subTest(path=path):
                self.data["artifacts"][digest] = path
                with self.assertRaises(ValueError):
                    self.run_bundle()

    def test_missing_required_receipt_is_visible_per_capability(self):
        self.data["capabilities"][0]["receipts"] = []
        result = self.run_bundle()
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["capabilities"][0]["editions"]["preview"]["checks"]["read"], "EVIDENCE_MISSING")

    def test_bundle_cannot_lower_product_acceptance_criteria(self):
        self.data["capabilities"][0]["criteria"]["standard"] = {"read": ["open"]}
        with self.assertRaisesRegex(ValueError, "PRODUCT_ACCEPTANCE_CRITERIA_MISMATCH"):
            self.run_bundle()

    def test_bundle_cannot_omit_declared_product_dependency(self):
        self.data["capabilities"][0]["dependencies"] = {}
        with self.assertRaisesRegex(ValueError, "PRODUCT_DEPENDENCY_SCOPE_MISMATCH"):
            self.run_bundle()

    def test_bundle_cannot_omit_authorization_dependencies(self):
        self.add_handling()
        self.data["capabilities"][0]["role_business_handling"]["authorization_dependencies"] = {}
        row = self.run_bundle()["capabilities"][0]
        self.assertTrue(row["product_eligible"])
        self.assertEqual(row["role_business_handling"]["error"], "AUTHORIZATION_DEPENDENCY_SCOPE_MISMATCH")

    def test_bundle_cannot_drop_denial_scenario(self):
        self.add_handling()
        self.data["capabilities"][0]["role_business_handling"]["scenarios"] = {}
        row = self.run_bundle()["capabilities"][0]
        self.assertEqual(row["role_business_handling"]["error"], "BUSINESS_SCENARIO_SCOPE_MISMATCH")

    def test_bundle_cannot_redefine_denial_as_allow(self):
        self.add_handling()
        scenario = self.data["capabilities"][0]["role_business_handling"]["scenarios"]["reader-cannot-submit"]
        scenario["expected"]["decision"] = "allow"
        row = self.run_bundle()["capabilities"][0]
        self.assertIn("BUSINESS_SCENARIO_CONTRACT_MISMATCH", row["role_business_handling"]["error"])

    def test_unregistered_capability_cannot_self_certify(self):
        self.data["capabilities"][0]["capability_key"] = "unknown.query"
        with self.assertRaisesRegex(ValueError, "CAPABILITY_ACCEPTANCE_NOT_DECLARED"):
            self.run_bundle()

    def test_missing_authority_never_falls_back_to_bundle_criteria(self):
        self.authority.unlink()
        with self.assertRaises(FileNotFoundError):
            self.run_bundle()

    def test_preview_requires_role_surface_alignment_before_interaction_closeout(self):
        authority = json.loads((ROOT / ACCEPTANCE_CONTRACTS).read_text())
        criteria = authority["capabilities"]["project.list.open"]["product_criteria"]
        self.assertEqual(set(criteria["preview"]["role_surface_contract"]), {
            "role_surface_entry_visibility_alignment", "role_surface_action_availability_alignment",
            "role_surface_denial_reason_alignment", "frontend_consumes_authoritative_role_surface"})
        preview_cases = {case for cases in criteria["preview"].values() for case in cases}
        self.assertNotIn("interaction_roundtrip_browser", preview_cases)
        self.assertIn("interaction_roundtrip_browser", criteria["standard"]["query_regression"])

    def test_real_p1_pilot_references_implemented_capability_and_existing_inputs(self):
        authority = json.loads((ROOT / ACCEPTANCE_CONTRACTS).read_text())
        tree = ast.parse((ROOT / "addons/smart_construction_core/services/capability_registry.py").read_text())
        implemented = {node.args[0].value for node in ast.walk(tree)
                       if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                       and node.func.id == "_cap" and node.args and isinstance(node.args[0], ast.Constant)}
        for key, contract in authority["capabilities"].items():
            self.assertIn(key, implemented)
            for path in contract["product_dependencies"] + contract["authorization_dependencies"]:
                self.assertTrue((ROOT / path).is_file(), path)
            for check, cases in contract["product_criteria"]["preview"].items():
                self.assertTrue(set(cases) <= set(contract["product_criteria"]["standard"][check]))
            decisions = {scenario["expected"]["decision"] for scenario in contract["business_scenarios"].values()}
            self.assertEqual(decisions, {"allow", "deny"})
            self.assertTrue(all("principal_fingerprint" not in scenario for scenario in contract["business_scenarios"].values()))


if __name__ == "__main__":
    unittest.main()
