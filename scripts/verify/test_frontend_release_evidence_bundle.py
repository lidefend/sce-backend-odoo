#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/release"))
from frontend_release_evidence import (  # noqa: E402
    EvidenceBundleError,
    create_deterministic_zip,
    generate_bundle,
    scan_sensitive_paths,
    sha256_file,
    verify_bundle,
)


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class FrontendReleaseEvidenceBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        cls.tree = subprocess.check_output(
            ["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, text=True
        ).strip()
        cls.base_tmp = tempfile.TemporaryDirectory(prefix="frontend-evidence-tests-")
        cls.base = Path(cls.base_tmp.name)
        frontend = cls.base / "frontend-input"
        cls._write_frontend(frontend)
        dist = cls.base / "dist"
        (dist / "assets").mkdir(parents=True)
        (dist / "index.html").write_text("<!doctype html><title>SCE</title>", encoding="utf-8")
        (dist / "assets/app.js").write_text("console.log('release');", encoding="utf-8")
        checks = []
        runs = {}
        for index, name in enumerate(
            (
                "public_guard",
                "professional_authorization",
                "professional_quality_gate",
                "frontend_release_gate",
            ),
            start=10,
        ):
            run_id = str(index)
            checks.append(
                {
                    "name": name,
                    "status": "completed",
                    "conclusion": "success",
                    "head_sha": cls.sha,
                    "details_url": f"https://github.com/lidefend/sce-backend-odoo/actions/runs/{run_id}/job/{index}0",
                    "app": {"slug": "github-actions"},
                    "started_at": "2026-01-01T00:00:00Z",
                    "completed_at": "2026-01-01T00:01:00Z",
                }
            )
            runs[run_id] = {
                "id": int(run_id),
                "name": name,
                "head_sha": cls.sha,
                "event": "push",
                "head_branch": "main",
                "conclusion": "success",
                "run_attempt": 1,
            }
        write_json(cls.base / "checks.json", {"check_runs": checks})
        write_json(cls.base / "runs.json", runs)
        write_json(cls.base / "statuses.json", {"statuses": []})
        write_json(
            cls.base / "artifacts.json",
            {
                "artifacts": [
                    {
                        "id": 77,
                        "name": f"frontend-release-evidence-13-1-{cls.sha}",
                        "digest": "sha256:" + "d" * 64,
                        "size_in_bytes": 1024,
                        "created_at": "2026-01-01T00:01:00Z",
                        "expired": False,
                        "workflow_run": {"id": 13},
                    }
                ]
            },
        )
        write_json(
            cls.base / "ruleset.json",
            {
                "name": "main-github-authoritative-pr",
                "enforcement": "active",
                "bypass_actors": [],
                "rules": [
                    {
                        "type": "required_status_checks",
                        "parameters": {
                            "required_status_checks": [
                                {"context": row["name"]} for row in checks
                            ]
                        },
                    }
                ],
            },
        )
        write_json(
            cls.base / "build-metadata.json",
            {
                "node_version": "v22.0.0",
                "pnpm_version": "9.12.3",
                "frontend_package_version": "1.0.0",
                "build_started_at": "2026-01-01T00:00:00Z",
                "build_completed_at": "2026-01-01T00:01:00Z",
            },
        )
        cls.bundle = cls.base / "bundle"
        generate_bundle(
            cls.bundle,
            frontend_root=frontend,
            dist=dist,
            raw_checks=cls.base / "checks.json",
            run_metadata=cls.base / "runs.json",
            statuses=cls.base / "statuses.json",
            artifacts=cls.base / "artifacts.json",
            branch_protection=cls.base / "ruleset.json",
            build_metadata=cls.base / "build-metadata.json",
            candidate_sha=cls.sha,
            candidate_tree=cls.tree,
            source_run_id="99",
            source_run_attempt="1",
        )
        cls.archive = cls.base / "bundle.zip"
        create_deterministic_zip(cls.bundle, cls.archive)

    @classmethod
    def tearDownClass(cls):
        cls.base_tmp.cleanup()

    @classmethod
    def _write_frontend(cls, root: Path) -> None:
        sections = {
            name: {"result": "PASS"}
            for name in (
                "accessibility",
                "delivery_hardening",
                "error_recovery",
                "navigation",
                "performance",
                "responsive",
                "static",
            )
        }
        evidence = {
            name: {"git_sha": cls.sha, "sha256": "a" * 64}
            for name in sections
        }
        common = {"git_sha": cls.sha}
        write_json(
            root / "frontend-release-audit/report.json",
            {
                "schema_version": "frontend-release-audit/v2",
                "git_sha": cls.sha,
                "git_tree": cls.tree,
                "result": "PASS",
                "summary_exit_code": 0,
                "blocking_failures": [],
                "missing_evidence": [],
                "sections": sections,
                "evidence": evidence,
            },
        )
        write_json(
            root / "frontend-release-audit/gate-result.json",
            {
                "schema_version": "frontend-release-gate-result/v1",
                "git_sha": cls.sha,
                "git_tree": cls.tree,
                "result": "PASS",
            },
        )
        write_json(
            root / "frontend-page-identity/navigation-report.json",
            {
                **common,
                "total": {
                    "result": "PASS",
                    "expected_count": 71,
                    "actual_count": 71,
                    "matched_count": 71,
                    "missing_leaf_keys": [],
                    "unexpected_leaf_keys": [],
                    "duplicate_leaf_keys": [],
                    "invalid_leaf_keys": [],
                },
            },
        )
        write_json(
            root / "frontend-delivery-hardening/accessibility.json",
            {**common, "result": "PASS", "critical": 0, "serious": 0, "scans": [{"page": "home"}]},
        )
        write_json(
            root / "frontend-delivery-hardening/performance.json",
            {
                **common,
                "result": "PASS",
                "budget_source": "config/frontend/release_performance_budgets_v1.json",
                "scenarios": {"home": {"sample_count": 5}},
            },
        )
        write_json(
            root / "frontend-delivery-hardening/report.json",
            {
                **common,
                "pass": True,
                "journeys": {"J02": "PASS"},
                "runtime": {"console": [], "pageerror": [], "unhandled": [], "http": []},
            },
        )
        write_json(
            root / "frontend-delivery-hardening/responsive.json",
            {**common, "horizontal_overflow": 0, "pages": [{"page": "home", "pass": True}]},
        )
        write_json(
            root / "frontend-delivery-hardening/error-recovery.json",
            {
                **common,
                "network_retry": "PASS",
                "conflict_refresh": "PASS",
                "session_expired": "PASS",
            },
        )

    def copy_bundle(self) -> tuple[tempfile.TemporaryDirectory, Path]:
        temporary = tempfile.TemporaryDirectory(prefix="frontend-evidence-case-")
        target = Path(temporary.name) / "bundle"
        shutil.copytree(self.bundle, target)
        return temporary, target

    def resign(self, bundle: Path) -> None:
        manifest_path = bundle / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["bundle_contents"] = [
            {
                "path": path.relative_to(bundle).as_posix(),
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in sorted(item for item in bundle.rglob("*") if item.is_file())
            if path.relative_to(bundle).as_posix() not in {"manifest.json", "digests/SHA256SUMS"}
        ]
        write_json(manifest_path, manifest)
        paths = sorted(item for item in bundle.rglob("*") if item.is_file())
        (bundle / "digests/SHA256SUMS").write_text(
            "\n".join(
                f"{sha256_file(path)}  {path.relative_to(bundle).as_posix()}"
                for path in paths
                if path.relative_to(bundle).as_posix() != "digests/SHA256SUMS"
            )
            + "\n",
            encoding="utf-8",
        )

    def assert_blocked(self, expected: str, mutator, *, resign: bool = True) -> None:
        temporary, bundle = self.copy_bundle()
        try:
            mutator(bundle)
            if resign:
                self.resign(bundle)
            with self.assertRaisesRegex(EvidenceBundleError, expected):
                verify_bundle(bundle, self.sha, self.tree)
        finally:
            temporary.cleanup()

    def mutate_json(self, relative: str, transform):
        def mutate(bundle: Path):
            path = bundle / relative
            payload = json.loads(path.read_text())
            transform(payload)
            write_json(path, payload)

        return mutate

    def test_valid_directory_and_archive_pass(self):
        self.assertEqual(verify_bundle(self.bundle, self.sha, self.tree)["result"], "PASS")
        digest = sha256_file(self.archive)
        self.assertEqual(
            verify_bundle(self.archive, self.sha, self.tree, digest)["result"], "PASS"
        )

    def test_manifest_missing_corrupt_schema_sha_tree_and_source_identity_fail(self):
        cases = [
            ("MANIFEST_MISSING", lambda b: (b / "manifest.json").unlink(), False),
            ("MANIFEST_MISSING", lambda b: (b / "manifest.json").write_text("{"), False),
            (
                "SCHEMA_UNSUPPORTED",
                self.mutate_json("manifest.json", lambda p: p.__setitem__("schema_version", "bad")),
                False,
            ),
            (
                "CANDIDATE_SHA_MISMATCH",
                self.mutate_json("manifest.json", lambda p: p.__setitem__("candidate_sha", "0" * 40)),
                False,
            ),
            (
                "CANDIDATE_TREE_MISMATCH",
                self.mutate_json("manifest.json", lambda p: p.__setitem__("candidate_tree", "0" * 40)),
                False,
            ),
            (
                "SOURCE_IDENTITY_INVALID",
                self.mutate_json("manifest.json", lambda p: p.__setitem__("source_event", "pull_request")),
                False,
            ),
        ]
        for reason, mutation, resign in cases:
            with self.subTest(reason=reason):
                self.assert_blocked(reason, mutation, resign=resign)

    def test_run_identity_historical_pr_manual_and_duplicate_checks_fail(self):
        checks_path = "checks.json"

        def change_check(field, value, name="frontend_release_gate"):
            def transform(payload):
                row = next(item for item in payload["checks"] if item["check_name"] == name)
                row[field] = value

            return self.mutate_json(checks_path, transform)

        for reason, mutation in [
            ("MANIFEST_MISMATCH", change_check("run_id", "old")),
            ("MANIFEST_MISMATCH", change_check("run_attempt", "2")),
            ("FRONTEND_RELEASE_GATE_INVALID", change_check("event", "pull_request")),
            ("FRONTEND_RELEASE_GATE_INVALID", change_check("head_sha", "0" * 40)),
            ("FRONTEND_RELEASE_GATE_INVALID", change_check("manual_commit_status", True)),
            (
                "REQUIRED_CHECK_COUNT",
                self.mutate_json(
                    checks_path,
                    lambda p: p["checks"].append(copy.deepcopy(p["checks"][-1])),
                ),
            ),
        ]:
            with self.subTest(reason=reason):
                self.assert_blocked(reason, mutation)

    def test_missing_extra_digest_bundle_digest_and_preforged_report_fail(self):
        self.assert_blocked(
            "BUNDLE_FILE_SET_MISMATCH",
            lambda b: (b / "frontend/accessibility.json").unlink(),
            resign=False,
        )
        self.assert_blocked(
            "BUNDLE_FILE_SET_MISMATCH",
            lambda b: (b / "extra.txt").write_text("unexpected"),
            resign=False,
        )
        self.assert_blocked(
            "FILE_DIGEST_MISMATCH",
            lambda b: (b / "frontend/accessibility.json").write_text("{}"),
            resign=False,
        )
        with self.assertRaisesRegex(EvidenceBundleError, "BUNDLE_DIGEST_MISMATCH"):
            verify_bundle(self.archive, self.sha, self.tree, "0" * 64)
        self.assert_blocked(
            "PREFORGED_VERIFICATION_REPORT",
            lambda b: write_json(b / "verification/verification-report.json", {"result": "PASS"}),
        )

    def test_main_gate_conclusion_duplicate_manual_and_branch_protection_fail(self):
        for check in (
            "public_guard",
            "professional_authorization",
            "professional_quality_gate",
            "frontend_release_gate",
        ):
            mutation = self.mutate_json(
                "checks.json",
                lambda p, check=check: next(
                    row for row in p["checks"] if row["check_name"] == check
                ).__setitem__("conclusion", "failure"),
            )
            self.assert_blocked("INVALID", mutation)
        self.assert_blocked(
            "MANUAL_COMMIT_STATUS",
            self.mutate_json(
                "governance/manual-statuses.json",
                lambda p: p.__setitem__("statuses", [{"context": "frontend_release_gate"}]),
            ),
        )
        self.assert_blocked(
            "BRANCH_PROTECTION_UNTRUSTED",
            self.mutate_json(
                "governance/branch-protection.json",
                lambda p: p.__setitem__("bypass_actors", [{"actor_id": 1}]),
            ),
        )

    def test_navigation_accessibility_performance_not_run_and_child_sha_fail(self):
        cases = [
            (
                "NAVIGATION_IDENTITY",
                "frontend/navigation-report.json",
                lambda p: p["total"]["missing_leaf_keys"].append("missing"),
            ),
            (
                "NAVIGATION_IDENTITY",
                "frontend/navigation-report.json",
                lambda p: p["total"]["unexpected_leaf_keys"].append("unexpected"),
            ),
            (
                "NAVIGATION_IDENTITY",
                "frontend/navigation-report.json",
                lambda p: p["total"]["duplicate_leaf_keys"].append("duplicate"),
            ),
            (
                "NAVIGATION_IDENTITY",
                "frontend/navigation-report.json",
                lambda p: p["total"]["invalid_leaf_keys"].append("invalid"),
            ),
            (
                "ACCESSIBILITY_NOT_PASS",
                "frontend/accessibility.json",
                lambda p: p.__setitem__("serious", 1),
            ),
            (
                "ACCESSIBILITY_NOT_PASS",
                "frontend/accessibility.json",
                lambda p: p.__setitem__("critical", 1),
            ),
            (
                "PERFORMANCE_NOT_PASS",
                "frontend/performance.json",
                lambda p: p.__setitem__("result", "FAIL"),
            ),
            (
                "PERFORMANCE_SAMPLES",
                "frontend/performance.json",
                lambda p: p["scenarios"]["home"].__setitem__("sample_count", 4),
            ),
            (
                "FRONTEND_REQUIRED_SECTION",
                "frontend/frontend-release-report.json",
                lambda p: p["sections"]["accessibility"].__setitem__("result", "NOT_RUN"),
            ),
            (
                "FRONTEND_EVIDENCE_SHA",
                "frontend/accessibility.json",
                lambda p: p.__setitem__("git_sha", "0" * 40),
            ),
        ]
        for reason, path, transform in cases:
            with self.subTest(reason=reason):
                self.assert_blocked(reason, self.mutate_json(path, transform))

    def test_build_lockfile_output_sensitive_database_and_qualification_fail(self):
        cases = [
            (
                "BUILD_IDENTITY",
                "build/build-manifest.json",
                lambda p: p.__setitem__("candidate_tree", "0" * 40),
            ),
            (
                "LOCKFILE_DIGEST",
                "build/build-manifest.json",
                lambda p: p.__setitem__("lockfile_sha256", "0" * 64),
            ),
            (
                "SENSITIVE_DATA_SCAN",
                "manifest.json",
                lambda p: p["sensitive_data_scan"].__setitem__("result", "FAIL"),
            ),
            (
                "DATABASE_ACCESS",
                "manifest.json",
                lambda p: p["database_access"].__setitem__("production", True),
            ),
            (
                "QUALIFICATION_STATE_FORBIDDEN",
                "manifest.json",
                lambda p: p.__setitem__("qualification_state", "FROZEN"),
            ),
            (
                "QUALIFICATION_STATE_FORBIDDEN",
                "manifest.json",
                lambda p: p.__setitem__("qualification_state", "RELEASED"),
            ),
        ]
        for reason, path, transform in cases:
            with self.subTest(reason=reason):
                self.assert_blocked(reason, self.mutate_json(path, transform), resign=path != "manifest.json")
        self.assert_blocked(
            "BUILD_OUTPUT_DIGEST",
            lambda b: (b / "build/output/index.html").write_text("modified"),
        )

    def test_sensitive_path_scanner_rejects_secret_shapes_and_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "safe.json").write_text('{"result":"PASS"}')
            scan_sensitive_paths([root])
            (root / "leak.txt").write_text("Authorization: Bearer " + "x" * 40)
            with self.assertRaisesRegex(EvidenceBundleError, "SENSITIVE_CONTENT_DETECTED"):
                scan_sensitive_paths([root])
            (root / "leak.txt").unlink()
            (root / ".env").write_text("SAFE=placeholder")
            with self.assertRaisesRegex(EvidenceBundleError, "SENSITIVE_FILE_FORBIDDEN"):
                scan_sensitive_paths([root])

    def test_archive_traversal_symlink_duplicate_and_compression_bomb_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            traversal = root / "traversal.zip"
            with zipfile.ZipFile(traversal, "w") as archive:
                archive.writestr("../manifest.json", "{}")
            with self.assertRaisesRegex(EvidenceBundleError, "ARCHIVE_PATH_UNSAFE"):
                verify_bundle(traversal, self.sha, self.tree)

            duplicate = root / "duplicate.zip"
            with zipfile.ZipFile(duplicate, "w") as archive:
                archive.writestr("A.json", "{}")
                archive.writestr("a.json", "{}")
            with self.assertRaisesRegex(EvidenceBundleError, "ARCHIVE_DUPLICATE_NAME"):
                verify_bundle(duplicate, self.sha, self.tree)

            symlink = root / "symlink.zip"
            with zipfile.ZipFile(symlink, "w") as archive:
                info = zipfile.ZipInfo("manifest.json")
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(info, "target")
            with self.assertRaisesRegex(EvidenceBundleError, "ARCHIVE_SYMLINK"):
                verify_bundle(symlink, self.sha, self.tree)

            bomb = root / "bomb.zip"
            with zipfile.ZipFile(bomb, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("payload.bin", b"0" * 1000000)
            with self.assertRaisesRegex(EvidenceBundleError, "ARCHIVE_COMPRESSION_RATIO"):
                verify_bundle(bomb, self.sha, self.tree)


if __name__ == "__main__":
    unittest.main()
