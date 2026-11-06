#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from frontend_release_audit import (
    EvidenceError,
    authoritative_navigation_counts,
    read_json,
    validate_accessibility,
    validate_navigation,
    validate_performance,
    validate_responsive,
    validate_error_recovery,
    validate_role_release_projection,
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
        expected_roles = authoritative_navigation_counts()
        expected_total = sum(expected_roles.values())
        base = {
            "git_sha": SHA,
            "total": {
                "result": "PASS",
                "expected_count": expected_total,
                "actual_count": expected_total,
                "matched_count": expected_total,
            },
            "roles": {
                role: {
                    "expected_count": count,
                    "actual_count": count,
                    "matched_count": count,
                    "missing_leaf_keys": [],
                    "unexpected_leaf_keys": [],
                    "duplicate_leaf_keys": [],
                }
                for role, count in expected_roles.items()
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

    @patch('frontend_release_audit.read_json', return_value={
        'minimum_sample_count': 5,
        'scenarios': {'home': {'median_ms': 20, 'p95_ms': 30, 'max_ms': 30}}})
    def test_performance_sample_and_budget_fail_closed(self, policy_read):
        metrics = {"samples_ms": [10, 10, 10, 20, 20], "sample_count": 5, "median_ms": 10, "p95_ms": 20, "max_ms": 20}
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
            {**valid, "scenarios": {}, "budgets": {}},
            {**valid, "scenarios": {"home": {key: value for key, value in metrics.items() if key != "median_ms"}}},
            {**valid, "scenarios": {"home": {**metrics, "median_ms": float('nan')}}},
            {**valid, "budgets": {"home": {**budget, "median_ms": 99999}}},
            {**valid, "scenarios": {"home": {**metrics, "samples_ms": [1, 1, 1, 1, 1]}}},
            {**valid, "scenarios": {"home": {**metrics, "samples_ms": [10, 10, 10, 20, float('nan')]}}},
            {**valid, "scenarios": {"home": {**metrics, "samples_ms": None}}},
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
        with self.assertRaises(EvidenceError):
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


class RoleReleaseProjectionValidatorTest(unittest.TestCase):
    SUBJECTS = {
        "finance": ("fixture_role_finance", "finance"),
        "project_a_member": ("fixture_role_project_a_member", "project_member"),
        "pm": ("fixture_role_pm", "pm"),
        "owner": ("fixture_role_owner", "owner"),
    }
    RECEIPT = {
        "git_sha": SHA,
        "receipt": {
            "database": "sc_frontend_acceptance",
            "snapshot_id": 3,
            "fingerprint": "12e8edf300b58ea9d82fff9525677c8467453445c5228f780c75fc5840ab9b1f",
            "version": f"frontend-audit-{SHA[:12]}",
            "source_revision": SHA,
        },
    }

    def _manifest(self):
        root = Path(__file__).resolve().parents[2]
        return json.loads((root / "config/frontend/authoritative_navigation.json").read_text())

    def setUp(self):
        env_patch = patch.dict(
            os.environ,
            {
                "SC_ACCEPTANCE_RUN_ID": "test-managed-run",
                "GITHUB_RUN_ID": "42191333658",
                "GITHUB_RUN_ATTEMPT": "7",
            },
            clear=False,
        )
        env_patch.start()
        self.addCleanup(env_patch.stop)

    def _report(self, mutate=None, scope_status="VERIFIED"):
        manifest = self._manifest()
        roles = {
            role: {
                "login": self.SUBJECTS[role][0],
                "role_code": self.SUBJECTS[role][1],
                "p0": {"primary_home_identities": list(row["leaf_keys"]), "error": None},
            }
            for role, row in manifest["roles"].items()
        }
        report = {
            "git_sha": SHA,
            "db": "sc_frontend_acceptance",
            "scope_status": scope_status,
            "run_id": os.environ.get("SC_ACCEPTANCE_RUN_ID")
            or os.environ.get("GITHUB_RUN_ID", "local"),
            "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", "1"),
            "release_snapshot": {
                "database": "sc_frontend_acceptance",
                "snapshot_id": 3,
                "fingerprint": "12e8edf300b58ea9d82fff9525677c8467453445c5228f780c75fc5840ab9b1f",
                "version": f"frontend-audit-{SHA[:12]}",
            },
            "roles": roles,
        }
        if mutate:
            mutate(report, manifest)
        return report

    def _validate(self, report):
        return validate_role_release_projection(report, SHA, self.RECEIPT)

    def test_matching_identities_pass(self):
        self._validate(self._report())

    def test_matching_identities_with_unverified_scope_still_fail(self):
        with self.assertRaises(EvidenceError) as ctx:
            self._validate(self._report(scope_status="NOT_VERIFIED"))
        self.assertIn("ROLE_RELEASE_PROJECTION_SCOPE_MISMATCH", str(ctx.exception))

    def test_missing_or_misspelled_scope_still_fail(self):
        for scope in (None, "VERIFYED", "not-verified"):
            report = self._report()
            report["scope_status"] = scope
            with self.assertRaises(EvidenceError) as ctx:
                self._validate(report)
            self.assertIn("ROLE_RELEASE_PROJECTION_SCOPE_MISMATCH", str(ctx.exception))

    def test_stale_run_attempt_rejected(self):
        def mutate(report, _manifest):
            report["run_attempt"] = "1"
        with self.assertRaises(EvidenceError) as ctx:
            self._validate(self._report(mutate))
        self.assertIn("ROLE_RELEASE_PROJECTION_RUN_ATTEMPT_MISMATCH", str(ctx.exception))

    def test_stale_run_id_rejected(self):
        def mutate(report, _manifest):
            report["run_id"] = "test-managed-run-other"
        with self.assertRaises(EvidenceError) as ctx:
            self._validate(self._report(mutate))
        self.assertIn("ROLE_RELEASE_PROJECTION_RUN_ID_MISMATCH", str(ctx.exception))

    def test_stale_snapshot_rejected(self):
        def mutate(report, _manifest):
            report["release_snapshot"]["version"] = "frontend-audit-000000000000"
        with self.assertRaises(EvidenceError) as ctx:
            self._validate(self._report(mutate))
        self.assertIn("ROLE_RELEASE_PROJECTION_SNAPSHOT_VERSION_MISMATCH", str(ctx.exception))

    def test_stale_snapshot_fingerprint_rejected(self):
        def mutate(report, _manifest):
            report["release_snapshot"]["fingerprint"] = "0" * 64
        with self.assertRaises(EvidenceError) as ctx:
            self._validate(self._report(mutate))
        self.assertIn("ROLE_RELEASE_PROJECTION_SNAPSHOT_FINGERPRINT_MISMATCH", str(ctx.exception))

    def test_invalid_snapshot_id_rejected(self):
        def mutate(report, _manifest):
            report["release_snapshot"]["snapshot_id"] = "abc"
        with self.assertRaises(EvidenceError) as ctx:
            self._validate(self._report(mutate))
        self.assertIn("ROLE_RELEASE_PROJECTION_SNAPSHOT_ID_INVALID", str(ctx.exception))

    def test_missing_receipt_rejected(self):
        with self.assertRaises(EvidenceError) as ctx:
            validate_role_release_projection(self._report(), SHA, None)
        self.assertIn("ROLE_RELEASE_PROJECTION_RECEIPT_MISSING", str(ctx.exception))

    def test_receipt_missing_fingerprint_rejected(self):
        receipt = json.loads(json.dumps(self.RECEIPT))
        del receipt["receipt"]["fingerprint"]
        with self.assertRaises(EvidenceError) as ctx:
            validate_role_release_projection(self._report(), SHA, receipt)
        self.assertIn("ROLE_RELEASE_PROJECTION_RECEIPT_FINGERPRINT_MISSING", str(ctx.exception))

    def test_receipt_sha_mismatch_rejected(self):
        receipt = json.loads(json.dumps(self.RECEIPT))
        receipt["git_sha"] = "b" * 40
        with self.assertRaises(EvidenceError) as ctx:
            validate_role_release_projection(self._report(), SHA, receipt)
        self.assertIn("ROLE_RELEASE_PROJECTION_RECEIPT_SHA_MISMATCH", str(ctx.exception))

    def test_receipt_stale_source_revision_rejected(self):
        receipt = json.loads(json.dumps(self.RECEIPT))
        receipt["receipt"]["source_revision"] = "c" * 40
        receipt["receipt"]["version"] = "frontend-audit-cccccccccccc"
        with self.assertRaises(EvidenceError) as ctx:
            validate_role_release_projection(self._report(), SHA, receipt)
        self.assertIn("ROLE_RELEASE_PROJECTION_RECEIPT_SOURCE_REVISION_MISMATCH", str(ctx.exception))

    def test_same_count_wrong_identity_rejected(self):
        def mutate(report, _manifest):
            identities = report["roles"]["pm"]["p0"]["primary_home_identities"]
            for index, key in enumerate(identities):
                if key.startswith("smart_construction_core.menu_sc_boq_analysis|"):
                    identities[index] = (
                        "smart_construction_core.menu_sc_project_tender|"
                        "smart_construction_core.action_sc_project_tender|tender.bid"
                    )
        with self.assertRaises(EvidenceError) as ctx:
            self._validate(self._report(mutate))
        self.assertIn("ROLE_RELEASE_PROJECTION_IDENTITY_MISMATCH", str(ctx.exception))

    def test_same_entries_wrong_role_rejected(self):
        def mutate(report, _manifest):
            report["roles"]["pm"]["role_code"] = "finance"
            report["roles"]["pm"]["login"] = "fixture_role_finance"
        with self.assertRaises(EvidenceError) as ctx:
            self._validate(self._report(mutate))
        self.assertIn("ROLE_RELEASE_PROJECTION_IDENTITY_MISMATCH", str(ctx.exception))
        self.assertIn("subject_identity_mismatch", str(ctx.exception))

    def test_wrong_database_rejected(self):
        def mutate(report, _manifest):
            report["db"] = "sc_frontend_acceptance_candidate"
        with self.assertRaises(EvidenceError) as ctx:
            self._validate(self._report(mutate))
        self.assertIn("ROLE_RELEASE_PROJECTION_DB_MISMATCH", str(ctx.exception))

    def test_scope_not_verified_keeps_all_role_diagnostics(self):
        manifest = self._manifest()

        def mutate(report, _manifest):
            for role in report["roles"]:
                report["roles"][role]["p0"]["primary_home_identities"] = [
                    "smart_construction_core.menu_sc_workspace_home||"
                ]
        with self.assertRaises(EvidenceError) as ctx:
            self._validate(self._report(mutate, scope_status="NOT_VERIFIED"))
        text = str(ctx.exception)
        self.assertIn("ROLE_RELEASE_PROJECTION_SCOPE_MISMATCH", text)
        for role in manifest["roles"]:
            self.assertIn(f'"{role}"', text)

    def test_missing_role_rejected(self):
        def mutate(report, _manifest):
            report["roles"].pop("owner")
        with self.assertRaises(EvidenceError) as ctx:
            self._validate(self._report(mutate))
        self.assertIn("ROLE_RELEASE_PROJECTION_ROLE_SET_MISMATCH", str(ctx.exception))

    def test_sha_mismatch_rejected(self):
        with self.assertRaises(EvidenceError) as ctx:
            validate_role_release_projection(self._report(), "b" * 40)
        self.assertIn("EVIDENCE_SHA_MISMATCH", str(ctx.exception))

    def test_duplicate_identity_rejected(self):
        def mutate(report, _manifest):
            identities = report["roles"]["finance"]["p0"]["primary_home_identities"]
            identities.append(identities[0])
        with self.assertRaises(EvidenceError) as ctx:
            self._validate(self._report(mutate))
        self.assertIn("ROLE_RELEASE_PROJECTION_IDENTITY_MISMATCH", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
