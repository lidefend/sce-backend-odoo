from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.verify import p1_payment_request_field_completeness_guard as guard


class PaymentRequestFieldCompletenessGuardTest(unittest.TestCase):
    def test_repository_contract_is_complete(self) -> None:
        self.assertEqual(guard.validate(), [])

    def test_every_rule_has_an_acceptance_obligation(self) -> None:
        payload = json.loads(guard.MATRIX.read_text(encoding="utf-8"))
        for rule in payload["field_rules"]:
            self.assertTrue(rule["acceptance"], f"missing acceptance for {rule['model']}.{rule['field']}")
            self.assertTrue(rule["surfaces"], f"missing surfaces for {rule['model']}.{rule['field']}")

    def test_form_surface_profile_mapping_keeps_create_and_edit_distinct(self) -> None:
        self.assertEqual(
            guard.form_profiles_for_surfaces(["create_edit"]),
            {"create", "edit"},
        )
        self.assertEqual(guard.form_profiles_for_surfaces(["create"]), {"create"})
        self.assertEqual(guard.form_profiles_for_surfaces(["edit"]), {"edit"})
        self.assertEqual(
            guard.form_profiles_for_surfaces(["list", "readonly", "mobile"]),
            {"readonly"},
        )

        original = json.loads(guard.MATRIX.read_text(encoding="utf-8"))
        for surface in ("create", "edit"):
            with self.subTest(surface=surface), tempfile.TemporaryDirectory() as directory:
                payload = json.loads(json.dumps(original))
                payload["field_rules"].append(
                    {
                        "model": "payment.request",
                        "field": "actual_paid_amount_display",
                        "label": "负例字段",
                        "classification": "derived",
                        "source": "negative_test",
                        "applicability": "always",
                        "required_gate": "render",
                        "editability": "readonly",
                        "surfaces": [surface],
                        "acceptance": "must_be_rejected_without_form_declarations",
                    }
                )
                matrix = Path(directory) / "matrix.json"
                matrix.write_text(json.dumps(payload), encoding="utf-8")
                with mock.patch.object(guard, "MATRIX", matrix):
                    errors = guard.validate()
                self.assertIn(
                    "native form missing field: payment.request.actual_paid_amount_display",
                    errors,
                )
                self.assertIn(
                    "product contract missing field: payment.request.actual_paid_amount_display",
                    errors,
                )

    def test_required_and_conditional_fields_declare_a_gate(self) -> None:
        payload = json.loads(guard.MATRIX.read_text(encoding="utf-8"))
        for rule in payload["field_rules"]:
            if rule["classification"] in {"required", "conditional"}:
                self.assertNotEqual(rule["required_gate"], "", f"missing gate for {rule['model']}.{rule['field']}")

    def test_industry_dimensions_have_owner_decision_and_evidence(self) -> None:
        payload = json.loads(guard.MATRIX.read_text(encoding="utf-8"))
        dimensions = payload["industry_benchmarks"]["dimensions"]
        self.assertGreaterEqual(len(dimensions), 10)
        for dimension in dimensions:
            self.assertIn(dimension["status"], guard.ALLOWED_BENCHMARK_STATUSES)
            self.assertTrue(dimension["ownership"], dimension["key"])
            self.assertTrue(dimension["decision"], dimension["key"])
            self.assertTrue(dimension["acceptance"], dimension["key"])
            if dimension["status"] != "gap":
                self.assertTrue(dimension["source_fields"], dimension["key"])

    def test_user_journey_coverage_is_explicit_and_not_overclaimed(self) -> None:
        payload = json.loads(guard.MATRIX.read_text(encoding="utf-8"))
        journeys = payload["journey_gates"]
        self.assertGreaterEqual(len(journeys), 14)
        self.assertFalse(any(row["coverage_status"] == "implemented" for row in journeys))
        self.assertTrue(any(row["coverage_status"] != "implemented" for row in journeys))
        for journey in journeys:
            self.assertIn(journey["coverage_status"], guard.ALLOWED_JOURNEY_COVERAGE)
            self.assertTrue(journey["required_assertions"], journey["key"])


if __name__ == "__main__":
    unittest.main()
