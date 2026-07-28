#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "docs/audit/um_p1/um_p1_s01_ownership_visibility_contract_v1.json"
GUARD = ROOT / "scripts/verify/um_p1_ownership_visibility_contract_guard.py"


class TestUmP1OwnershipVisibilityContractGuard(unittest.TestCase):
    def test_guard_accepts_the_committed_contract_and_source_topology(self):
        result = subprocess.run(
            [sys.executable, str(GUARD)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("P1_ENTRY_COUNT=6", result.stdout)
        self.assertIn("CONTRACT_CONFLICTS=0", result.stdout)
        self.assertIn("PRODUCT_GAPS=0", result.stdout)
        self.assertIn("NEXT_SLICE=UM-P1-DOCUMENT-ORDER-COMPLETE", result.stdout)

    def test_every_entry_preserves_evidence_and_closes_product_gaps(self):
        payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
        entries = payload["ENTRIES"]

        self.assertEqual(len(entries), 6)
        self.assertEqual(len({entry["ENTRY_ID"] for entry in entries}), 6)
        for entry in entries:
            self.assertTrue(entry["CONTRACT_EVIDENCE"], entry["ENTRY_ID"])
            self.assertEqual(entry["PRODUCT_GAP"], [], entry["ENTRY_ID"])
            self.assertTrue(
                any(
                    marker in entry["UNAUTHORIZED_AND_NONEXISTENT_EQUIVALENCE"]
                    for marker in ("VERIFIED", "PROVEN")
                ),
                entry["ENTRY_ID"],
            )
            if entry["ENTRY_ID"] in {
                "UM-P1-ENTRY-01-PROJECT-RECEIPT",
                "UM-P1-ENTRY-02-PAYMENT-REQUEST-EXECUTION",
            }:
                self.assertEqual(
                    entry["S01_BASELINE"]["CURRENT_PRODUCT_IMPLEMENTATION_STATUS"],
                    (
                        "PRODUCT_GAP"
                        if entry["ENTRY_ID"] == "UM-P1-ENTRY-01-PROJECT-RECEIPT"
                        else "PARTIAL_CONTRACT_PROVEN"
                    ),
                )

    def test_cost_ledger_contract_records_approved_backend_authority(self):
        payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
        by_id = {entry["ENTRY_ID"]: entry for entry in payload["ENTRIES"]}
        entry = by_id["UM-P1-ENTRY-06-COST-LEDGER"]
        self.assertEqual(entry["PRODUCT_GAP"], [])
        self.assertIn("project_id.user_id", entry["OWNERSHIP_FIELD"])
        self.assertIn("project_id.message_is_follower", entry["OWNERSHIP_FIELD"])
        self.assertIn("manager_id is not", entry["OWNERSHIP_FIELD"])
        self.assertEqual(len(entry["EXPECTED_RECORD_RULE_IDS"]), 4)

        self.assertEqual(
            payload["NEXT_DOCUMENT_ORDER_SLICE"]["IMPLEMENTATION_GATE"],
            "NO_REMAINING_P1_ENTRY",
        )

    def test_cost_ledger_slice_records_real_orm_evidence_and_exact_cleanup(self):
        payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
        verification = payload["S07_VERIFICATION"]

        self.assertEqual(verification["RESULT"], "PASS")
        self.assertTrue(verification["REAL_ODOO_REGISTRY_USED"])
        self.assertTrue(verification["REAL_ORM_USED"])
        self.assertFalse(verification["CONTROLLED_ORM_DOUBLES_USED"])
        self.assertTrue(verification["FINAL_TEMP_DATABASE_REMOVED"])
        self.assertTrue(verification["FINAL_TEMP_RESOURCES_REMOVED"])
        for resource in ("DATABASE", "CONTAINER", "NETWORK", "VOLUME"):
            self.assertTrue(verification[f"{resource}_BASELINE_RESTORED"])
        self.assertEqual(verification["UM_P1_S07_COST_LEDGER_TESTS"], 10)
        self.assertEqual(verification["NEW_OR_WORSENED_FAILURES"], [])

    def test_receipt_slice_records_real_orm_evidence_and_exact_cleanup(self):
        payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
        verification = payload["S02_VERIFICATION"]

        self.assertEqual(verification["RESULT"], "PASS")
        self.assertTrue(verification["REAL_ODOO_REGISTRY_USED"])
        self.assertTrue(verification["REAL_ORM_USED"])
        self.assertFalse(verification["CONTROLLED_ORM_DOUBLES_USED"])
        self.assertTrue(verification["TEMP_DATABASE_REMOVED"])
        self.assertTrue(verification["TEMP_RESOURCES_REMOVED"])
        for resource in ("DATABASE", "CONTAINER", "NETWORK", "VOLUME"):
            self.assertTrue(verification[f"{resource}_BASELINE_RESTORED"])
        self.assertEqual(verification["UM_P1_S02_RECEIPT_TESTS"], 5)
        self.assertEqual(verification["NEW_OR_WORSENED_FAILURES"], [])

    def test_payment_slice_records_real_orm_evidence_without_product_changes(self):
        payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
        verification = payload["S03_VERIFICATION"]

        self.assertEqual(verification["RESULT"], "PASS")
        self.assertEqual(verification["PRODUCT_FILES_CHANGED"], [])
        self.assertFalse(verification["FIRST_RUN_PRODUCT_DEFECT"])
        self.assertTrue(verification["FIRST_RUN_TEMP_DATABASE_REMOVED"])
        self.assertTrue(verification["FIRST_RUN_TEMP_RESOURCES_REMOVED"])
        self.assertTrue(verification["FINAL_TEMP_DATABASE_REMOVED"])
        self.assertTrue(verification["FINAL_TEMP_RESOURCES_REMOVED"])
        self.assertEqual(verification["TOTAL_POST_TESTS"], 20)
        self.assertEqual(verification["UM_P1_S03_PAYMENT_TESTS"], 5)
        self.assertEqual(verification["NEW_OR_WORSENED_FAILURES"], [])


if __name__ == "__main__":
    unittest.main()
