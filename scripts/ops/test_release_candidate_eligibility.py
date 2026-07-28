#!/usr/bin/env python3
"""Regression tests for release candidate supersession qualification."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import release_candidate_eligibility as eligibility


SHA = "a" * 40
IMAGE = "ghcr.io/lidefend/sce-product@sha256:" + "b" * 64


def candidate() -> dict:
    return {
        "candidate_name": "RCX",
        "source_sha": SHA,
        "image_ref": IMAGE,
    }


def supersession(**overrides) -> dict:
    payload = {
        "schema_version": eligibility.SUPERSESSION_SCHEMA,
        "candidate_name": "RCX",
        "failed_candidate_sha": SHA,
        "failed_image_ref": IMAGE,
        "status": "ACTIVE",
        "reason": "candidate remains eligible",
        "promotion_allowed": True,
        "new_candidate_required": False,
    }
    payload.update(overrides)
    return payload


class CandidateEligibilityTests(unittest.TestCase):
    def test_active_candidate_passes(self) -> None:
        result = eligibility.validate_supersession(candidate(), supersession())
        self.assertFalse(result["blocked"])
        self.assertEqual(result["reason_code"], "ELIGIBLE_CANDIDATE")

    def test_promotion_false_blocks(self) -> None:
        result = eligibility.validate_supersession(
            candidate(), supersession(promotion_allowed=False)
        )
        self.assertTrue(result["blocked"])
        self.assertEqual(result["reason_code"], "SUPERSEDED_CANDIDATE")

    def test_new_candidate_required_blocks(self) -> None:
        result = eligibility.validate_supersession(
            candidate(), supersession(new_candidate_required=True)
        )
        self.assertTrue(result["blocked"])

    def test_superseded_revoked_and_invalid_statuses_block(self) -> None:
        for status in ("SUPERSEDED", "REVOKED_BY_OWNER", "INVALID"):
            with self.subTest(status=status):
                self.assertTrue(
                    eligibility.validate_supersession(
                        candidate(), supersession(status=status)
                    )["blocked"]
                )

    def test_identity_mismatch_fails_closed(self) -> None:
        with self.assertRaisesRegex(
            eligibility.CandidateEligibilityError,
            "identity does not match",
        ) as raised:
            eligibility.validate_supersession(
                candidate(),
                supersession(failed_candidate_sha="c" * 40),
            )
        self.assertEqual(raised.exception.reason_code, "CANDIDATE_IDENTITY_MISMATCH")

    def test_missing_fields_fail_closed(self) -> None:
        payload = supersession()
        payload.pop("promotion_allowed")
        with self.assertRaises(eligibility.CandidateEligibilityError) as raised:
            eligibility.validate_supersession(candidate(), payload)
        self.assertEqual(
            raised.exception.reason_code,
            "INVALID_SUPERSESSION_DECLARATION",
        )

    def test_invalid_json_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "supersession.json"
            path.write_text("{broken", encoding="utf-8")
            with self.assertRaises(eligibility.CandidateEligibilityError) as raised:
                eligibility.load_json(path, "candidate supersession declaration")
        self.assertEqual(
            raised.exception.reason_code,
            "INVALID_SUPERSESSION_DECLARATION",
        )

    def test_audit_passes_while_qualification_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate_path = root / "candidate.json"
            supersession_path = root / "supersession.json"
            candidate_path.write_text(json.dumps(candidate()), encoding="utf-8")
            supersession_path.write_text(
                json.dumps(
                    supersession(
                        status="SUPERSEDED_BY_DEFECT",
                        promotion_allowed=False,
                        new_candidate_required=True,
                    )
                ),
                encoding="utf-8",
            )
            audit = eligibility.audit_supersession(
                candidate_path, supersession_path
            )
            self.assertEqual(audit["result"], "PASS")
            self.assertTrue(audit["blocked"])
            with self.assertRaises(eligibility.CandidateEligibilityError) as raised:
                eligibility.assert_candidate_eligible(
                    candidate_path, supersession_path
                )
        self.assertEqual(raised.exception.reason_code, "SUPERSEDED_CANDIDATE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
