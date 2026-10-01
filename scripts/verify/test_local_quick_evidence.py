#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/ops/local_quick_evidence.py"
SPEC = importlib.util.spec_from_file_location("local_quick_evidence", MODULE_PATH)
assert SPEC and SPEC.loader
evidence = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evidence)


class LocalQuickEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.environment = mock.patch.dict(os.environ, {key: "" for key in ("MAKEFLAGS", "MFLAGS", "MAKEOVERRIDES", "MAKEFILES", evidence.scans.COVERAGE_ENV)})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        (self.root / "tracked.txt").write_text("baseline\n", encoding="utf-8")
        for path in set(evidence.scans.COMMON_AUTHORITY).union(*evidence.scans.AUTHORITY.values()):
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("fixture authority\n")
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(self.root),
                "-c",
                "user.name=Codex Test",
                "-c",
                "user.email=codex-test@example.invalid",
                "commit",
                "-q",
                "-m",
                "fixture",
            ],
            check=True,
        )
        self.head = subprocess.run(
            ["git", "-C", str(self.root), "rev-parse", "HEAD"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout.strip()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_success(self, *, linked: bool = False) -> tuple[Path, list[list[str]]]:
        calls: list[list[str]] = []

        def runner(command, **_kwargs):
            calls.append(command)
            if "env" in _kwargs:
                with mock.patch.dict(os.environ, _kwargs["env"]):
                    for kind in evidence.scans.AUTHORITY:
                        evidence.scans.record_scan_success(self.root, kind)
            return subprocess.CompletedProcess(command, 0)

        with mock.patch.object(evidence, "is_linked_worktree", return_value=linked):
            path = evidence.run_quick(self.root, runner=runner)
        assert path is not None
        return path, calls

    def test_successful_primary_quick_records_and_verifies(self) -> None:
        path, calls = self.run_success()
        self.assertEqual(evidence.verify(self.root, self.head), path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["head"], self.head)
        self.assertEqual(payload["suite"], "ci.local.quick")
        self.assertEqual(payload["producer"], evidence.PRODUCER)
        self.assertEqual(calls, [["make", "--no-print-directory", "ci.local.quick.run"]])

    def test_successful_linked_quick_uses_governed_authority_runner_once(self) -> None:
        _path, calls = self.run_success(linked=True)
        self.assertEqual(
            calls,
            [["python3", "scripts/dev/local_dev_frontend_quick.py", "--full-ci-local-quick"]],
        )

    def test_missing_or_tampered_receipt_is_rejected(self) -> None:
        with self.assertRaisesRegex(evidence.EvidenceError, "missing"):
            evidence.verify(self.root, self.head)
        path, _calls = self.run_success()
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["tree"] = "b" * 40
        path.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(evidence.EvidenceError, "does not match"):
            evidence.verify(self.root, self.head)

    def test_dirty_worktree_cannot_reuse_and_success_does_not_issue_receipt(self) -> None:
        (self.root / "untracked.txt").write_text("dirty\n", encoding="utf-8")
        calls: list[list[str]] = []

        def runner(command, **_kwargs):
            calls.append(command)
            return subprocess.CompletedProcess(command, 0)

        with mock.patch.object(evidence, "is_linked_worktree", return_value=False):
            self.assertIsNone(evidence.run_quick(self.root, runner=runner))
        with self.assertRaisesRegex(evidence.EvidenceError, "must be clean"):
            evidence.verify(self.root, self.head)
        self.assertEqual(len(calls), 1)

    def test_different_head_cannot_reuse_receipt(self) -> None:
        self.run_success()
        with self.assertRaisesRegex(evidence.EvidenceError, "HEAD changed"):
            evidence.verify(self.root, "b" * 40)

    def test_quick_failure_never_issues_receipt(self) -> None:
        def runner(command, **_kwargs):
            return subprocess.CompletedProcess(command, 17)

        with mock.patch.object(evidence, "is_linked_worktree", return_value=False):
            with self.assertRaisesRegex(evidence.QuickRunFailed, "receipt not issued"):
                evidence.run_quick(self.root, runner=runner)
        with self.assertRaisesRegex(evidence.EvidenceError, "missing"):
            evidence.verify(self.root, self.head)

    def test_success_with_end_state_drift_refuses_receipt(self) -> None:
        def runner(command, **_kwargs):
            (self.root / "tracked.txt").write_text("changed during Quick\n", encoding="utf-8")
            return subprocess.CompletedProcess(command, 0)

        with mock.patch.object(evidence, "is_linked_worktree", return_value=False):
            with self.assertRaisesRegex(evidence.EvidenceError, "must be clean"):
                evidence.run_quick(self.root, runner=runner)

    def test_success_with_head_drift_refuses_receipt(self) -> None:
        def runner(command, **_kwargs):
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(self.root),
                    "-c",
                    "user.name=Codex Test",
                    "-c",
                    "user.email=codex-test@example.invalid",
                    "commit",
                    "-q",
                    "--allow-empty",
                    "-m",
                    "head drift",
                ],
                check=True,
            )
            return subprocess.CompletedProcess(command, 0)

        with mock.patch.object(evidence, "is_linked_worktree", return_value=False):
            with self.assertRaisesRegex(evidence.EvidenceError, "HEAD changed"):
                evidence.run_quick(self.root, runner=runner)

    def test_exit_zero_without_actual_scanner_proofs_is_rejected(self) -> None:
        with self.assertRaisesRegex(evidence.EvidenceError, "scanner proof missing"):
            evidence.run_quick(self.root, runner=lambda command, **kwargs: subprocess.CompletedProcess(command, 0))
        self.assertFalse(evidence.evidence_path(self.root, self.head).exists())

    def test_redundant_remote_tip_does_not_invalidate_exact_head(self) -> None:
        path, _ = self.run_success()
        evidence.git(self.root, "update-ref", "refs/remotes/origin/feature", self.head)
        self.assertEqual(evidence.verify(self.root, self.head), path)

    def test_new_content_ref_invalidates_exact_head_verification(self) -> None:
        self.run_success()
        tree = evidence.git(self.root, "rev-parse", "HEAD^{tree}")
        extra = evidence.git(self.root, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit-tree", tree, "-p", self.head, "-m", "new side commit")
        evidence.git(self.root, "update-ref", "refs/tags/after-quick", extra)
        with self.assertRaisesRegex(evidence.EvidenceError, "does not match"):
            evidence.verify(self.root, self.head)

    def test_deleting_unique_covered_reference_invalidates_verification(self) -> None:
        tree = evidence.git(self.root, "rev-parse", "HEAD^{tree}")
        extra = evidence.git(self.root, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit-tree", tree, "-p", self.head, "-m", "side commit")
        evidence.git(self.root, "update-ref", "refs/tags/covered", extra)
        self.run_success()
        evidence.git(self.root, "update-ref", "-d", "refs/tags/covered")
        with self.assertRaisesRegex(evidence.EvidenceError, "does not match"):
            evidence.verify(self.root, self.head)

    def test_ref_drift_does_not_sign(self) -> None:
        def runner(command, **kwargs):
            subprocess.run(["git", "-C", str(self.root), "tag", "new-ref"], check=True)
            return subprocess.CompletedProcess(command, 0)
        with self.assertRaisesRegex(evidence.EvidenceError, "reference snapshot changed"):
            evidence.run_quick(self.root, runner=runner)
        self.assertFalse(evidence.evidence_path(self.root, self.head).exists())

    def test_unsafe_make_environment_rejected_before_either_runner(self) -> None:
        for linked in (False, True):
            for key, value in (("MAKEFLAGS", "n"), ("MFLAGS", "-q"), ("MAKEFLAGS", "--touch"),
                               ("MAKEFLAGS", "-o target"), ("MAKEFLAGS", "i"), ("MFLAGS", "--ignore-errors"),
                               ("MAKEFLAGS", "--eval=x"), ("MAKEFLAGS", "-f other.mk"), ("MFLAGS", "-C /tmp"), ("MAKEFILES", "/tmp/injected.mk"),
                               ("MAKEOVERRIDES", "SCANNER=true")):
                with self.subTest(linked=linked, key=key, value=value), mock.patch.dict(os.environ, {key: value}), mock.patch.object(evidence, "is_linked_worktree", return_value=linked):
                    runner = mock.Mock()
                    with self.assertRaises(evidence.EvidenceError): evidence.run_quick(self.root, runner=runner)
                    runner.assert_not_called()
        self.assertFalse(evidence.evidence_path(self.root, self.head).exists())

    def test_cancelled_runner_does_not_sign_and_cleans_temporary_proof(self) -> None:
        folders = []
        def runner(command, **kwargs):
            folders.append(Path(kwargs["env"][evidence.scans.COVERAGE_ENV]))
            raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt): evidence.run_quick(self.root, runner=runner)
        self.assertFalse(folders[0].exists())
        self.assertFalse(evidence.evidence_path(self.root, self.head).exists())

    def test_schema_two_remains_exact_head_evidence_only(self) -> None:
        path = evidence.evidence_path(self.root, self.head)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"schema_version": 2, "suite": evidence.SUITE,
            "producer": "atomic-ci-local-quick-runner-v1", "head": self.head,
            "tree": evidence.git(self.root, "rev-parse", "HEAD^{tree}")}))
        self.assertEqual(evidence.verify(self.root, self.head), path)

    def test_public_cli_cannot_sign_without_running_quick(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(MODULE_PATH), "record", "--expected-head", self.head],
            cwd=self.root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("invalid choice", completed.stdout)


if __name__ == "__main__":
    unittest.main()
