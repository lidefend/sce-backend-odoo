#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "candidate_scan_contract", ROOT / "scripts/release/candidate_scan_contract.py"
)
assert SPEC and SPEC.loader
scan = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scan)

SHA = "a" * 40
DIGEST = "sha256:" + "b" * 64


def summary(report: dict, **overrides):
    values = {
        "report": report,
        "trivy_version": {"Version": "0.63.0"},
        "trivy_db_metadata": {"UpdatedAt": "2026-07-23T00:00:00Z"},
        "syft_version": {"version": "1.27.1"},
        "image_manifest": {"source_sha": SHA, "image_digest": DIGEST},
        "expected_source_sha": SHA,
        "expected_image_digest": DIGEST,
        "scanned_at": "2026-07-23T01:00:00Z",
    }
    values.update(overrides)
    return scan.build_summary(**values)


class CandidateScanContractTests(unittest.TestCase):
    def test_formal_scan_requests_all_observed_severities_and_secret_scanner(self):
        entrypoint = (ROOT / "scripts/release/immutable_candidate_scan.sh").read_text()
        self.assertIn("--severity UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL", entrypoint)
        self.assertIn("--scanners vuln,secret", entrypoint)

    def test_medium_low_are_captured_but_do_not_block(self):
        result = summary(
            {"Results": [{"Vulnerabilities": [{"Severity": "MEDIUM"}, {"Severity": "LOW"}]}]}
        )
        self.assertEqual(result["counts"]["MEDIUM"], 1)
        self.assertEqual(result["counts"]["LOW"], 1)
        self.assertEqual(result["policy"]["result"], "pass")

    def test_missing_results_or_tool_metadata_fails_closed(self):
        with self.assertRaises(scan.ScanContractError):
            summary({})
        with self.assertRaises(scan.ScanContractError):
            summary({"Results": []}, trivy_db_metadata={})

    def test_formal_entrypoint_reads_trivy_db_metadata_from_cache(self):
        entrypoint = (ROOT / "scripts/release/immutable_candidate_scan.sh").read_text()
        self.assertIn("trivy-cache/trivy/db/metadata.json", entrypoint)
        self.assertIn("--trivy-db-metadata", entrypoint)

    def test_critical_high_and_secret_each_block(self):
        rows = (
            {"Vulnerabilities": [{"Severity": "CRITICAL"}]},
            {"Vulnerabilities": [{"Severity": "HIGH"}]},
            {"Secrets": [{"RuleID": "secret"}]},
        )
        for row in rows:
            with self.subTest(row=row):
                self.assertEqual(summary({"Results": [row]})["policy"]["result"], "fail")

    def test_scan_identity_mismatch_is_rejected(self):
        with self.assertRaises(scan.ScanContractError):
            summary(
                {"Results": []},
                image_manifest={"source_sha": "c" * 40, "image_digest": DIGEST},
            )
        with self.assertRaises(scan.ScanContractError):
            summary(
                {"Results": []},
                image_manifest={"source_sha": SHA, "image_digest": "sha256:" + "c" * 64},
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
