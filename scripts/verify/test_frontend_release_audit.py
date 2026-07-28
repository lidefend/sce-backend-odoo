#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from frontend_release_audit import (
    EvidenceError,
    read_json,
    validate_accessibility,
    validate_navigation,
    validate_performance,
    validate_responsive,
    validate_error_recovery,
)

SHA = "a" * 40


class FrontendReleaseAuditFailClosedTest(unittest.TestCase):
    def test_missing_or_damaged_report_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(EvidenceError):
                read_json(root / "missing.json")
            damaged = root / "damaged.json"
            damaged.write_text("{", encoding="utf-8")
            with self.assertRaises(EvidenceError):
                read_json(damaged)

    def test_navigation_missing_unexpected_duplicate_is_rejected(self):
        base = {
            "git_sha": SHA,
            "total": {"result": "PASS", "expected_count": 70},
            "roles": {
                role: {
                    "expected_count": count,
                    "actual_count": count,
                    "matched_count": count,
                    "missing_leaf_keys": [],
                    "unexpected_leaf_keys": [],
                    "duplicate_leaf_keys": [],
                }
                for role, count in {"finance": 42, "project_a_member": 9, "pm": 14, "owner": 5}.items()
            },
        }
        validate_navigation(base, SHA)
        for field in ("missing_leaf_keys", "unexpected_leaf_keys", "duplicate_leaf_keys"):
            report = json.loads(json.dumps(base))
            report["roles"]["finance"][field] = ["x"]
            with self.assertRaises(EvidenceError):
                validate_navigation(report, SHA)

    def test_accessibility_missing_serious_or_sha_mismatch_is_rejected(self):
        valid = {"git_sha": SHA, "result": "PASS", "critical": 0, "serious": 0, "scans": [{"page": "/"}]}
        validate_accessibility(valid, SHA)
        for report in (
            {**valid, "scans": []},
            {**valid, "serious": 1},
            {**valid, "git_sha": "b" * 40},
        ):
            with self.assertRaises(EvidenceError):
                validate_accessibility(report, SHA)

    def test_performance_sample_and_budget_fail_closed(self):
        metrics = {"sample_count": 5, "median_ms": 10, "p95_ms": 20, "max_ms": 20}
        budget = {"median_ms": 20, "p95_ms": 30, "max_ms": 30}
        valid = {
            "git_sha": SHA,
            "result": "PASS",
            "budget_source": "config.json",
            "scenarios": {"home": metrics},
            "budgets": {"home": budget},
            "absolute_budget_pass": True,
            "relative_budget_pass": False,
        }
        validate_performance(valid, SHA)
        for report in (
            {**valid, "scenarios": {"home": {**metrics, "sample_count": 4}}},
            {**valid, "scenarios": {"home": {**metrics, "p95_ms": 31}}},
            {**valid, "result": "NOT_RUN"},
        ):
            with self.assertRaises(EvidenceError):
                validate_performance(report, SHA)

        relative = {
            **valid,
            "absolute_budget_pass": False,
            "relative_budget_pass": True,
            "scenarios": {
                "home": {
                    **metrics,
                    "median_ms": 21,
                    "p95_ms": 31,
                    "max_ms": 31,
                }
            },
            "metric_regression_percent": {
                "home": {"median_ms": 5.0, "p95_ms": -5.0, "max_ms": -5.0}
            },
        }
        validate_performance(relative, SHA)
        for metric in ("median_ms", "p95_ms", "max_ms"):
            regressed = json.loads(json.dumps(relative))
            regressed["metric_regression_percent"]["home"][metric] = 11.0
            with self.assertRaises(EvidenceError):
                validate_performance(regressed, SHA)

    def test_responsive_and_error_recovery_fail_closed(self):
        responsive = {
            "git_sha": SHA,
            "pages": [{"name": "home", "pass": True}],
            "viewports": [{"width": 390, "height": 844}],
            "horizontal_overflow": 0,
        }
        validate_responsive(responsive, SHA)
        with self.assertRaises(EvidenceError):
            validate_responsive({**responsive, "pages": []}, SHA)
        with self.assertRaises(EvidenceError):
            validate_responsive({**responsive, "horizontal_overflow": 1}, SHA)

        recovery = {
            "git_sha": SHA,
            "network_retry": "PASS",
            "conflict_refresh": "PASS",
            "session_expired": "PASS",
        }
        validate_error_recovery(recovery, SHA)
        with self.assertRaises(EvidenceError):
            validate_error_recovery({**recovery, "session_expired": "NOT_RUN"}, SHA)


if __name__ == "__main__":
    unittest.main()
