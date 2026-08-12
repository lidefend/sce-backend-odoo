#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import io
import json
import tempfile
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import personal_data_scan


class PersonalDataScanTests(unittest.TestCase):
    def test_rules_report_metadata_without_values(self) -> None:
        samples = (
            ("PD001", "110105" + "19491231" + "002X"),
            ("PD002", "139" + "1234" + "5678"),
            ("PD003", "bank_account=" + "622202" + "1234567890123"),
        )
        for expected_rule, value in samples:
            findings = personal_data_scan.scan_text(value, "fixture.txt", "a" * 40)
            self.assertIn(expected_rule, [item.rule_id for item in findings])
            self.assertNotIn(value, repr(findings))

    def test_clean_placeholders_pass(self) -> None:
        text = "id=DEMO-ID-001 phone=DEMO-PHONE-001 bank_account=DEMO-ACCOUNT-001"
        self.assertEqual(personal_data_scan.scan_text(text, "fixture.txt", "b" * 40), [])

    def test_hash_embedded_phone_shaped_digits_pass(self) -> None:
        text = (
            "candidate_ref=abcdef01234a"
            + "139"
            + "1234"
            + "5678"
            + "babcdef012345"
        )
        self.assertEqual(personal_data_scan.scan_text(text, "fixture.txt", "d" * 40), [])

    def test_main_never_prints_match_values(self) -> None:
        sensitive = "139" + "1234" + "5678"
        finding = personal_data_scan.scan_text(sensitive, "fixture.txt", "c" * 40)[0]
        stderr = io.StringIO()
        with (
            mock.patch.object(personal_data_scan, "worktree_findings", return_value=[finding]),
            mock.patch.object(personal_data_scan, "history_findings", return_value=[]),
            contextlib.redirect_stderr(stderr),
        ):
            self.assertEqual(personal_data_scan.main(["--scope", "all"]), 1)
        self.assertNotIn(sensitive, stderr.getvalue())
        self.assertIn("rule=PD002", stderr.getvalue())

    def test_exact_false_positive_suppresses_only_matching_blob_and_path(self) -> None:
        finding = personal_data_scan.Finding(
            "PD002", "demo.py", "a" * 40, "MOBILE_PHONE_PATTERN"
        )
        registry = {
            "schema_version": 1,
            "entries": [
                {
                    "rule_id": "PD002",
                    "path": "demo.py",
                    "blob_id": "a" * 40,
                    "classification": "MOBILE_PHONE_PATTERN",
                    "reason": "verified_synthetic_fixture",
                }
            ],
        }
        with self.subTest("exact match"), tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "registry.json"
            path.write_text(json.dumps(registry), encoding="utf-8")
            with mock.patch.object(personal_data_scan, "FALSE_POSITIVE_FILE", path):
                allowed = personal_data_scan.load_false_positives()
            self.assertIn((finding.rule_id, finding.path, finding.blob_id, finding.classification), allowed)
            self.assertNotIn((finding.rule_id, "other.py", finding.blob_id, finding.classification), allowed)

    def test_false_positive_registry_rejects_short_blob_identity(self) -> None:
        registry = {
            "schema_version": 1,
            "entries": [{
                "rule_id": "PD002",
                "path": "demo.py",
                "blob_id": "a" * 12,
                "classification": "MOBILE_PHONE_PATTERN",
                "reason": "too_broad",
            }],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "registry.json"
            path.write_text(json.dumps(registry), encoding="utf-8")
            with (
                mock.patch.object(personal_data_scan, "FALSE_POSITIVE_FILE", path),
                self.assertRaisesRegex(ValueError, "full SHA-1"),
            ):
                personal_data_scan.load_false_positives()


if __name__ == "__main__":
    unittest.main()
