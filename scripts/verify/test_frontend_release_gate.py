#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from frontend_release_gate import GateError, validate

SHA = "a" * 40
TREE = "b" * 40
SECTIONS = {
    "accessibility",
    "delivery_hardening",
    "error_recovery",
    "navigation",
    "performance",
    "responsive",
    "static",
}


def report() -> dict:
    return {
        "schema_version": "frontend-release-audit/v2",
        "git_sha": SHA,
        "git_tree": TREE,
        "result": "PASS",
        "summary_exit_code": 0,
        "blocking_failures": [],
        "required_sections": sorted(SECTIONS),
        "sections": {name: {"result": "PASS"} for name in SECTIONS},
        "evidence": {
            name: {"git_sha": SHA, "sha256": "c" * 64, "path": f"{name}.json"}
            for name in SECTIONS
        },
        "workflow": {
            "event": "push",
            "run_id": "7",
            "run_attempt": "1",
            "checkout_sha": SHA,
        },
    }


class FrontendReleaseGateFailClosedTests(unittest.TestCase):
    def run_fixture(self, payload: dict | str, **overrides):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            path.write_text(payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8")
            defaults = {
                "expected_sha": SHA,
                "expected_tree": TREE,
                "command_outcome": "success",
                "expected_event": "push",
                "expected_run_id": "7",
                "expected_run_attempt": "1",
            }
            defaults.update(overrides)
            return validate([path], **defaults)

    def assert_reason(self, expected: str, payload=None, **overrides):
        with self.assertRaisesRegex(GateError, expected):
            self.run_fixture(report() if payload is None else payload, **overrides)

    def test_valid_current_run_passes(self):
        self.assertEqual(self.run_fixture(report())["result"], "PASS")

    def test_valid_scheduled_run_passes(self):
        payload = report()
        payload["workflow"]["event"] = "schedule"
        result = self.run_fixture(payload, expected_event="schedule")
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["event"], "schedule")

    def test_unsupported_event_fails_even_when_report_matches(self):
        payload = report()
        payload["workflow"]["event"] = "repository_dispatch"
        self.assert_reason(
            "WORKFLOW_EVENT_MISMATCH",
            payload,
            expected_event="repository_dispatch",
        )

    def test_upstream_failure_skipped_cancelled_not_run_and_nonzero_fail(self):
        for outcome in ("failure", "skipped", "cancelled", "not_run"):
            with self.subTest(outcome=outcome):
                self.assert_reason("AUTHORITATIVE_COMMAND_", command_outcome=outcome)

    def test_missing_duplicate_empty_and_corrupt_reports_fail(self):
        with self.assertRaisesRegex(GateError, "REPORT_MISSING"):
            validate(
                [],
                expected_sha=SHA,
                expected_tree=TREE,
                command_outcome="success",
                expected_event="push",
                expected_run_id="7",
                expected_run_attempt="1",
            )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "r.json"
            path.write_text(json.dumps(report()), encoding="utf-8")
            with self.assertRaisesRegex(GateError, "DUPLICATE_REPORT"):
                validate(
                    [path, path],
                    expected_sha=SHA,
                    expected_tree=TREE,
                    command_outcome="success",
                    expected_event="push",
                    expected_run_id="7",
                    expected_run_attempt="1",
                )
        for damaged in ("", "{"):
            self.assert_reason("REPORT_INVALID", damaged)

    def test_schema_sha_checkout_tree_run_and_attempt_fail(self):
        cases = (
            ("schema_version", "bad", "REPORT_SCHEMA_MISMATCH"),
            ("git_sha", "d" * 40, "REPORT_SHA_MISMATCH"),
            ("git_tree", "d" * 40, "REPORT_TREE_MISMATCH"),
        )
        for key, value, reason in cases:
            payload = report()
            payload[key] = value
            self.assert_reason(reason, payload)
        for key, value, reason in (
            ("checkout_sha", "d" * 40, "CHECKOUT_SHA_MISMATCH"),
            ("run_id", "old", "WORKFLOW_RUN_MISMATCH"),
            ("run_attempt", "2", "WORKFLOW_ATTEMPT_MISMATCH"),
        ):
            payload = report()
            payload["workflow"][key] = value
            self.assert_reason(reason, payload)

    def test_required_section_not_run_and_missing_evidence_fail(self):
        payload = report()
        payload["sections"]["accessibility"]["result"] = "NOT_RUN"
        self.assert_reason("SECTION_ACCESSIBILITY_NOT_PASS", payload)
        payload = report()
        del payload["evidence"]["performance"]
        self.assert_reason("REQUIRED_EVIDENCE_MISSING", payload)

    def test_axe_performance_navigation_and_duplicate_key_fail_via_release_result(self):
        for reason in (
            "ACCESSIBILITY_BLOCKING_VIOLATIONS",
            "PERFORMANCE_BUDGET_EXCEEDED",
            "NAVIGATION_ROLE_MISMATCH",
            "NAVIGATION_DUPLICATE_STABLE_KEY",
        ):
            payload = report()
            payload["result"] = "FAIL"
            payload["summary_exit_code"] = 2
            payload["blocking_failures"] = [reason]
            self.assert_reason("RELEASE_AUDIT_NOT_PASS", payload)

    def test_historical_run_injection_and_evidence_sha_fail(self):
        payload = report()
        payload["workflow"]["run_id"] = "6"
        self.assert_reason("WORKFLOW_RUN_MISMATCH", payload)
        payload = report()
        payload["evidence"]["navigation"]["git_sha"] = "d" * 40
        self.assert_reason("EVIDENCE_NAVIGATION_SHA_MISMATCH", payload)

    def test_always_aggregator_cannot_turn_failure_into_success(self):
        self.assert_reason("AUTHORITATIVE_COMMAND_FAILURE", command_outcome="failure")

    def test_upload_diagnostics_cannot_override_release_failure(self):
        payload = report()
        payload["result"] = "FAIL"
        payload["summary_exit_code"] = 2
        self.assert_reason("RELEASE_AUDIT_NOT_PASS", payload)


if __name__ == "__main__":
    unittest.main()
