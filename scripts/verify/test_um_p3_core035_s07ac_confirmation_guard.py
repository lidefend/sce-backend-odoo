#!/usr/bin/env python3
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


VERIFY_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(VERIFY_DIR))

import um_p3_core035_s07ac_confirmation_guard as guard


class Core035S07acConfirmationGuardTest(unittest.TestCase):
    def setUp(self):
        self.manifest = guard.load_json(guard.MANIFEST)
        self.payload = guard.load_json(guard.ITEMS)
        self.authorization = guard.load_json(guard.AUTHORIZATION)
        self.profile = guard.load_json(guard.S07A_PROFILE)
        self.items_sha = guard.file_sha256(guard.ITEMS)

    def validate(self, *, manifest=None, payload=None, authorization=None):
        return guard.validate(
            manifest or self.manifest,
            payload or self.payload,
            authorization or self.authorization,
            self.profile,
            self.items_sha,
        )

    def test_committed_confirmation_set_is_valid(self):
        self.assertEqual([], self.validate())

    def test_missing_item_is_rejected(self):
        changed = copy.deepcopy(self.payload)
        changed["REVIEW_ITEMS"].pop()
        self.assertIn(
            "confirmation set must contain 88 review items",
            self.validate(payload=changed),
        )

    def test_duplicate_review_item_id_is_rejected(self):
        changed = copy.deepcopy(self.payload)
        changed["REVIEW_ITEMS"][1]["review_item_id"] = changed["REVIEW_ITEMS"][
            0
        ]["review_item_id"]
        self.assertIn(
            "review item identifiers are missing duplicated or unstable",
            self.validate(payload=changed),
        )

    def test_attribute_candidate_cannot_be_preconfirmed(self):
        changed = copy.deepcopy(self.payload)
        item = next(
            row
            for row in changed["REVIEW_ITEMS"]
            if row["source_classification"] == "ATTRIBUTE_CANDIDATE_ONLY"
        )
        item["reviewer_decision"] = "CONFIRM_ONE"
        item["decision_status"] = "AUTHORIZED_FINAL"
        self.assertTrue(
            any(
                "attribute candidate is pre-confirmed" in error
                for error in self.validate(payload=changed)
            )
        )

    def test_conflict_cannot_silently_confirm_one(self):
        changed = copy.deepcopy(self.payload)
        item = next(
            row
            for row in changed["REVIEW_ITEMS"]
            if row["source_classification"] == "CONFLICTING"
        )
        item["reviewer_decision"] = "CONFIRM_ONE"
        self.assertTrue(
            any(
                "conflict silently confirms a candidate" in error
                for error in self.validate(payload=changed)
            )
        )

    def test_pid_rowindex_cannot_be_enabled(self):
        changed = copy.deepcopy(self.payload)
        item = next(
            row
            for row in changed["REVIEW_ITEMS"]
            if row["prohibited_link_evidence"]
        )
        item["prohibited_link_evidence"][0]["usable_as_relation"] = True
        self.assertTrue(
            any(
                "uses pid to RowIndex as a relation" in error
                for error in self.validate(payload=changed)
            )
        )

    def test_non_candidate_final_without_document_is_rejected(self):
        changed = copy.deepcopy(self.payload)
        item = next(
            row
            for row in changed["REVIEW_ITEMS"]
            if row["source_classification"] == "ATTRIBUTE_CANDIDATE_ONLY"
        )
        item.update(
            {
                "reviewer_decision": "CONFIRM_ONE",
                "decision_status": "AUTHORIZED_FINAL",
                "confirmed_register_ref": "LEGACY_SOURCE_B-REGISTER-FFFFFFFFFFFFFFFFFFFFFFFF",
                "reviewed_by": "ROLE_REF:FIRST",
                "reviewed_at": "2026-07-27T05:00:00Z",
                "authorization_evidence_id": "AUTH_REF:1",
                "second_review_by": "ROLE_REF:SECOND",
                "second_review_at": "2026-07-27T06:00:00Z",
            }
        )
        self.assertTrue(
            any(
                "confirms a non-candidate without evidence" in error
                for error in self.validate(payload=changed)
            )
        )

    def test_same_person_dual_review_is_rejected(self):
        changed = copy.deepcopy(self.payload)
        item = next(
            row
            for row in changed["REVIEW_ITEMS"]
            if row["source_classification"] == "ATTRIBUTE_CANDIDATE_ONLY"
        )
        item.update(
            {
                "reviewer_decision": "CONFIRM_ONE",
                "decision_status": "AUTHORIZED_FINAL",
                "confirmed_register_ref": item["candidate_register_refs"][0],
                "reviewed_by": "ROLE_REF:SAME",
                "reviewed_at": "2026-07-27T05:00:00Z",
                "authorization_evidence_id": "AUTH_REF:1",
                "second_review_by": "ROLE_REF:SAME",
                "second_review_at": "2026-07-27T06:00:00Z",
            }
        )
        self.assertTrue(
            any(
                "uses one person for dual review" in error
                for error in self.validate(payload=changed)
            )
        )

    def test_evidence_digest_tampering_is_rejected(self):
        changed = copy.deepcopy(self.payload)
        changed["REVIEW_ITEMS"][0]["project_anchor"] = (
            "PROJECT_SHA256:" + "0" * 64
        )
        self.assertTrue(
            any(
                "evidence digest mismatch" in error
                for error in self.validate(payload=changed)
            )
        )

    def test_unsigned_template_cannot_claim_s07b(self):
        changed = copy.deepcopy(self.authorization)
        changed["S07B_REVIEW_REQUESTED"] = True
        self.assertIn(
            "authorization template prematurely requests S07B",
            self.validate(authorization=changed),
        )


if __name__ == "__main__":
    unittest.main()
