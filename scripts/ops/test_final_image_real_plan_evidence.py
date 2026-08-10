from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("final_image_real_plan_evidence.py")
SPEC = importlib.util.spec_from_file_location("final_image_real_plan_evidence", SCRIPT)
assert SPEC and SPEC.loader
EVIDENCE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EVIDENCE)


class FinalImageRealPlanEvidenceTests(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[Path, dict]:
        candidate = root / "candidate"
        candidate.mkdir()
        source = "a" * 40
        tree = "b" * 40
        version = "1.0.0-rc.16"
        (candidate / "release-report.json").write_text(
            json.dumps(
                {
                    "status": "ready",
                    "CANDIDATE_READY": True,
                    "source": {
                        "commit_sha": source,
                        "tree_sha": tree,
                        "product_version": version,
                    },
                }
            ),
            encoding="utf-8",
        )
        (candidate / "image-manifest.json").write_text(
            json.dumps(
                {
                    "source_sha": source,
                    "source_tree_sha": tree,
                    "product_version": version,
                    "local_image_id": "sha256:" + "c" * 64,
                }
            ),
            encoding="utf-8",
        )
        plan = {
            "status": "PASS",
            "action": "plan",
            "mode": "plan",
            "production_database_connected": False,
            "database_write_count": 0,
            "filestore_write_count": 0,
            "restore_id": "sc_restore_20260810t120000z_deadbeef",
            "isolated_network": "sc_restore_20260810t120000z_deadbeef_internal",
            "tenant_key": "sample_tenant",
            "payload_checksum": "d" * 64,
            "planned_records": 12,
            "planned_relationships": 7,
            "payload_batches_before": 1,
            "payload_batches_after": 1,
            "historical_facts_before": 3,
            "historical_facts_after": 3,
            "business_state_digest_before": "e" * 64,
            "business_state_digest_after": "e" * 64,
        }
        return candidate, plan

    def test_builds_exact_gate_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            candidate, plan = self.fixture(Path(temporary))
            payload = EVIDENCE.build(candidate, plan)
            self.assertEqual(payload["environment_id"], plan["restore_id"])
            self.assertEqual(payload["planned_records"], 12)
            self.assertEqual(payload["planned_relationships"], 7)
            self.assertEqual(payload["business_state_digest_before"], "e" * 64)

    def test_rejects_state_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            candidate, plan = self.fixture(Path(temporary))
            plan["business_state_digest_after"] = "f" * 64
            with self.assertRaisesRegex(EVIDENCE.EvidenceError, "plan contract"):
                EVIDENCE.build(candidate, plan)

    def test_existing_evidence_is_idempotent_only_when_equal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "evidence.json"
            EVIDENCE.atomic_write(output, {"status": "PASS"})
            EVIDENCE.atomic_write(output, {"status": "PASS"})
            with self.assertRaisesRegex(EVIDENCE.EvidenceError, "differs"):
                EVIDENCE.atomic_write(output, {"status": "FAIL"})


if __name__ == "__main__":
    unittest.main()
