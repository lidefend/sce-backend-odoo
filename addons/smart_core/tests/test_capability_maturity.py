"""Pure tests: evidence failures cannot promote a capability."""
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

_spec = importlib.util.spec_from_file_location(
    "capability_maturity", Path(__file__).resolve().parents[1] / "core/capability_maturity.py")
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)


class CapabilityMaturityTests(unittest.TestCase):
    def setUp(self):
        self.key = "sample.query"
        self.dependencies = {"implementation": "a" * 64, "acceptance_contract": "b" * 64}
        self.criteria = {"preview": {"entry": ["open", "denied"]},
                         "standard": {"entry": ["open", "denied"], "workflow": ["complete"]}}
        self.receipts = []
        self.artifacts = {}
        self.add("entry", [{"id": "open", "status": "pass"}, {"id": "denied", "status": "pass"}])

    def add(self, check, cases, **changes):
        payload = {"capability_key": self.key, "fingerprint": gate.maturity_fingerprint(self.key, self.dependencies, self.criteria),
                   "check_id": check, "cases": cases, **changes}
        raw = json.dumps(payload).encode()
        digest = hashlib.sha256(raw).hexdigest()
        self.artifacts[digest] = raw
        self.receipts.append({"capability_key": self.key, "fingerprint": payload["fingerprint"],
                              "check_id": check, "artifact_sha256": digest})

    def result(self):
        return gate.evaluate_maturity(capability_key=self.key, dependencies=self.dependencies,
                                      criteria=self.criteria, receipts=self.receipts, artifacts=self.artifacts)

    def test_preview_does_not_require_standard_workflow_evidence(self):
        self.assertEqual(self.result()["eligible_edition"], "preview")

    def test_complete_evidence_qualifies_for_standard(self):
        self.add("workflow", [{"id": "complete", "status": "pass"}])
        self.assertEqual(self.result()["eligible_edition"], "standard")

    def test_changed_dependency_invalidates_previous_evidence(self):
        self.dependencies["implementation"] = "c" * 64
        result = self.result()
        self.assertIsNone(result["eligible_edition"])
        self.assertEqual(result["editions"]["preview"]["checks"]["entry"], "EVIDENCE_STALE")

    def test_relaxed_criteria_cannot_reuse_old_evidence(self):
        self.criteria["preview"]["entry"] = ["open"]
        self.assertIsNone(self.result()["eligible_edition"])

    def test_tampered_artifact_is_rejected(self):
        self.artifacts[self.receipts[0]["artifact_sha256"]] = b'{}'
        self.assertIsNone(self.result()["eligible_edition"])

    def test_other_capability_receipt_cannot_be_reused(self):
        self.receipts[0]["capability_key"] = "another.query"
        self.assertIsNone(self.result()["eligible_edition"])

    def test_artifact_scope_is_checked_independently_of_receipt(self):
        self.receipts.clear()
        self.add("entry", [{"id": "open", "status": "pass"}], capability_key="another.query")
        self.assertEqual(self.result()["editions"]["preview"]["checks"]["entry"], "ARTIFACT_SCOPE_MISMATCH")

    def test_empty_failed_skipped_and_incomplete_results_never_qualify(self):
        for cases in ([], [{"id": "open", "status": "pass"}],
                      [{"id": "open", "status": "pass"}, {"id": "denied", "status": "skip"}],
                      [{"id": "open", "status": "pass"}, {"id": "denied", "status": "fail"}],
                      [{"id": "open", "status": "pass"}, {"id": "denied", "status": "error"}]):
            with self.subTest(cases=cases):
                self.receipts.clear()
                self.add("entry", cases)
                self.assertIsNone(self.result()["eligible_edition"])

    def test_duplicate_receipts_cannot_hide_a_failure(self):
        self.add("entry", [{"id": "open", "status": "fail"}])
        self.assertEqual(self.result()["editions"]["preview"]["checks"]["entry"], "DUPLICATE_RECEIPT")

    def test_duplicate_case_ids_are_rejected(self):
        self.receipts.clear()
        self.add("entry", [{"id": "open", "status": "fail"}, {"id": "open", "status": "pass"}])
        self.assertIsNone(self.result()["eligible_edition"])

    def test_standard_cannot_drop_preview_permission_case(self):
        self.criteria["standard"]["entry"] = ["open"]
        with self.assertRaisesRegex(ValueError, "STANDARD_MUST_INCLUDE_PREVIEW"):
            self.result()

    def test_empty_or_malformed_criteria_fail_closed(self):
        for criteria in ({}, {"preview": {}, "standard": {}},
                         {"preview": {"entry": []}, "standard": {"entry": []}}):
            with self.subTest(criteria=criteria):
                self.criteria = criteria
                with self.assertRaises(ValueError):
                    self.result()

    def test_fingerprint_is_stable_but_capability_specific(self):
        first = gate.candidate_fingerprint(self.key, self.dependencies)
        self.assertEqual(first, gate.candidate_fingerprint(self.key, dict(reversed(list(self.dependencies.items())))))
        self.assertNotEqual(first, gate.candidate_fingerprint("other", self.dependencies))

    def test_unregistered_dependency_set_is_not_a_valid_candidate(self):
        for dependencies in ({}, {"implementation": "latest"}, {"": "a" * 64}):
            with self.subTest(dependencies=dependencies), self.assertRaises(ValueError):
                gate.candidate_fingerprint(self.key, dependencies)


class BusinessHandlingEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.product = {"implementation": "a" * 64}
        self.authorization = {"acl": "b" * 64}
        self.scenario = {"role_code": "approver", "principal_fingerprint": "c" * 64,
                         "operation": "approve", "company_scope": "company-a", "data_scope": "assigned-project",
                         "record_state": "pending", "expected": {"decision": "allow", "reason_code": "",
                         "business_effect": {"state": "approved", "audit_events": 1}}}
        self.scenarios = {"approve-assigned": self.scenario}
        self.receipts = []
        self.artifacts = {}

    def evidence(self, *, observed=None, observed_context=None, evidence_key=None):
        identity = gate.business_handling_identity("example.approve", self.product, self.authorization, self.scenarios)
        fingerprint = gate.maturity_fingerprint(**identity)
        context = {k: v for k, v in self.scenario.items() if k != "expected"}
        payload = {"capability_key": evidence_key or identity["capability_key"], "fingerprint": fingerprint,
                   "check_id": "business_handling", "cases": [{"id": "approve-assigned", "status": "pass",
                   "observed_context": context if observed_context is None else observed_context,
                   "observed": self.scenario["expected"] if observed is None else observed}]}
        raw = json.dumps(payload).encode()
        digest = hashlib.sha256(raw).hexdigest()
        self.artifacts[digest] = raw
        self.receipts = [{"capability_key": payload["capability_key"], "fingerprint": fingerprint,
                          "check_id": "business_handling", "artifact_sha256": digest}]

    def result(self):
        return gate.evaluate_business_handling(capability_key="example.approve", product_dependencies=self.product,
            authorization_dependencies=self.authorization, scenarios=self.scenarios, receipts=self.receipts, artifacts=self.artifacts)

    def test_allow_requires_observed_business_transition_and_audit(self):
        self.evidence()
        self.assertTrue(self.result()["verified"])
        self.assertNotIn("eligible_edition", self.result())
        self.assertFalse(self.result()["authorization_performed"])

    def test_expected_denial_is_correct_handling_not_an_immature_product(self):
        self.scenario["expected"] = {"decision": "deny", "reason_code": "OUTSIDE_PROJECT",
                                     "business_effect": {"state": "pending", "records_changed": 0}}
        self.evidence()
        self.assertTrue(self.result()["verified"])

    def test_pass_label_without_business_effect_is_not_proof(self):
        self.evidence(observed={})
        self.assertFalse(self.result()["verified"])

    def test_denied_action_with_side_effects_fails(self):
        self.scenario["expected"] = {"decision": "deny", "reason_code": "ACCESS_DENIED",
                                     "business_effect": {"records_changed": 0}}
        self.evidence(observed={"decision": "deny", "reason_code": "ACCESS_DENIED",
                                "business_effect": {"records_changed": 1}})
        self.assertFalse(self.result()["verified"])

    def test_other_principal_or_company_observation_cannot_pass(self):
        context = {k: v for k, v in self.scenario.items() if k != "expected"}
        self.evidence(observed_context={**context, "company_scope": "company-b"})
        self.assertFalse(self.result()["verified"])

    def test_product_domain_receipt_cannot_stand_in_for_role_receipt(self):
        self.evidence(evidence_key="example.approve")
        self.assertFalse(self.result()["verified"])

    def test_authorization_change_invalidates_role_evidence(self):
        self.evidence()
        self.authorization["acl"] = "d" * 64
        self.assertFalse(self.result()["verified"])

    def test_product_change_invalidates_business_handling_evidence(self):
        self.evidence()
        self.product["implementation"] = "d" * 64
        self.assertFalse(self.result()["verified"])

    def test_bare_role_label_without_principal_and_data_scope_is_rejected(self):
        self.scenario.pop("principal_fingerprint")
        with self.assertRaisesRegex(ValueError, "BUSINESS_HANDLING_CONTEXT_REQUIRED"):
            self.result()


if __name__ == "__main__":
    unittest.main()
