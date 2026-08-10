#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import final_image_real_plan_gate as target


class FinalImageRealPlanGateTest(unittest.TestCase):
    source_sha = "a" * 40
    source_tree = "b" * 40
    image_id = "sha256:" + "c" * 64

    def evidence(self) -> dict:
        return {
            "schema_version": "final_image_real_plan.v2",
            "status": "PASS",
            "source_sha": self.source_sha,
            "source_tree": self.source_tree,
            "release_version": "1.0.0-rc.11",
            "image_content_id": self.image_id,
            "image_revision": self.source_sha,
            "command_contract": "release.production.tenant_payload.plan",
            "production_command_parity": True,
            "database_role": "isolated_customer_tenant_rehearsal",
            "environment_id": "sc_release_rc11_rehearsal_01",
            "runtime_isolation": True,
            "production_resource_overlap": False,
            "target_database": "sc_production",
            "tenant_key": "sample_tenant",
            "payload_digest": "d" * 64,
            "plan_computation_completed": True,
            "planned_records": 10,
            "planned_relationships": 20,
            "database_write_count": 0,
            "payload_batches_before": 0,
            "payload_batches_after": 0,
            "historical_facts_before": 0,
            "historical_facts_after": 0,
            "business_state_digest_before": "e" * 64,
            "business_state_digest_after": "e" * 64,
        }

    def validate(self, payload: dict) -> dict:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "final-image-real-plan.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return target.load_and_validate(
                path,
                expected_source_sha=self.source_sha,
                expected_source_tree=self.source_tree,
                expected_version="1.0.0-rc.11",
                expected_image_content_id=self.image_id,
            )

    def test_complete_real_plan_with_zero_writes_passes(self):
        self.assertEqual(self.validate(self.evidence())["status"], "PASS")

    def test_governed_restore_identity_passes(self):
        payload = self.evidence()
        payload["environment_id"] = "sc_restore_20260810t120000z_deadbeef"
        self.assertEqual(self.validate(payload)["status"], "PASS")

    def test_preflight_only_or_database_write_fails(self):
        for field, value in (
            ("plan_computation_completed", False),
            ("database_write_count", 1),
            ("production_command_parity", False),
        ):
            payload = self.evidence()
            payload[field] = value
            with self.assertRaises(target.RealPlanEvidenceError):
                self.validate(payload)

    def test_non_production_command_database_and_state_drift_fail(self):
        payload = self.evidence()
        payload["target_database"] = "sc_release_rc11_rehearsal_01"
        with self.assertRaises(target.RealPlanEvidenceError):
            self.validate(payload)
        payload = self.evidence()
        payload["historical_facts_after"] = 1
        with self.assertRaises(target.RealPlanEvidenceError):
            self.validate(payload)

    def test_environment_must_be_isolated_from_production(self):
        for field, value in (
            ("environment_id", "sc_production"),
            ("runtime_isolation", False),
            ("production_resource_overlap", True),
        ):
            payload = self.evidence()
            payload[field] = value
            with self.assertRaises(target.RealPlanEvidenceError):
                self.validate(payload)


if __name__ == "__main__":
    unittest.main()
