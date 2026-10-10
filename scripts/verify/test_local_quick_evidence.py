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

MANIFEST_TARGETS = ("guard.prod.forbid", "verify.alpha", "verify.beta", "verify.gamma", "verify.delta")


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

    def test_dirty_worktree_is_refused_before_the_suite_runs(self) -> None:
        (self.root / "untracked.txt").write_text("dirty\n", encoding="utf-8")
        calls: list[list[str]] = []

        def runner(command, **_kwargs):
            calls.append(command)
            return subprocess.CompletedProcess(command, 0)

        with mock.patch.object(evidence, "is_linked_worktree", return_value=False):
            with self.assertRaisesRegex(evidence.EvidenceError, "worktree is not clean"):
                evidence.run_quick(self.root, runner=runner)
        self.assertEqual(calls, [])
        with self.assertRaisesRegex(evidence.EvidenceError, "must be clean"):
            evidence.verify(self.root, self.head)

    def test_explicit_diagnostic_runs_the_dirty_suite_without_a_receipt(self) -> None:
        (self.root / "untracked.txt").write_text("dirty\n", encoding="utf-8")
        calls: list[list[str]] = []

        def runner(command, **_kwargs):
            calls.append(command)
            return subprocess.CompletedProcess(command, 0)

        with mock.patch.object(evidence, "is_linked_worktree", return_value=False):
            self.assertIsNone(evidence.run_quick(self.root, runner=runner, diagnostic=True))
        self.assertEqual(calls, [["make", "--no-print-directory", "ci.local.quick.run"]])
        with self.assertRaisesRegex(evidence.EvidenceError, "must be clean"):
            evidence.verify(self.root, self.head)

    def test_receipt_retention_keeps_the_newest_window(self) -> None:
        folder = evidence.evidence_path(self.root, self.head).parent
        folder.mkdir(parents=True, exist_ok=True)
        stems = [f"{index:040x}" for index in range(1, 6)]
        for index, stem in enumerate(stems):
            path = folder / f"{stem}.json"
            path.write_text("{}", encoding="utf-8")
            os.utime(path, (1_000_000 + index, 1_000_000 + index))
        self.assertEqual(sorted(evidence.prune_receipts(self.root, keep=2, current_head=self.head)), sorted(stems[:3]))
        self.assertEqual(sorted(path.name for path in folder.glob("*.json")), sorted(f"{s}.json" for s in stems[3:]))

    def test_receipt_retention_requires_a_positive_keep(self) -> None:
        for keep in (0, -1, True):
            with self.subTest(keep=keep):
                with self.assertRaisesRegex(evidence.EvidenceError, "positive integer"):
                    evidence.prune_receipts(self.root, keep=keep, current_head=self.head)

    def test_receipt_retention_keeps_the_newest_ancestor_outside_the_window(self) -> None:
        tree = evidence.git(self.root, "rev-parse", "HEAD^{tree}")
        child = evidence.git(self.root, "-c", "user.name=Test", "-c", "user.email=t@example.invalid",
                             "commit-tree", tree, "-p", self.head, "-m", "child")
        evidence.git(self.root, "reset", "--hard", child)
        folder = evidence.evidence_path(self.root, child).parent
        folder.mkdir(parents=True, exist_ok=True)
        parent_receipt = folder / f"{self.head}.json"
        parent_receipt.write_text("{}", encoding="utf-8")
        os.utime(parent_receipt, (1_000_000, 1_000_000))
        newer = folder / f"{'f' * 40}.json"
        newer.write_text("{}", encoding="utf-8")
        os.utime(newer, (2_000_000, 2_000_000))
        self.assertEqual(evidence.prune_receipts(self.root, keep=1, current_head=child), [])
        self.assertTrue(parent_receipt.exists())

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



class ShardCompositionTests(unittest.TestCase):
    """The declared manifest drives real shard slicing, and only an identical
    head+tree union may compose into the standard exact-head receipt."""

    def setUp(self) -> None:
        self.environment = mock.patch.dict(
            os.environ,
            {key: "" for key in ("MAKEFLAGS", "MFLAGS", "MAKEOVERRIDES", "MAKEFILES", evidence.scans.COVERAGE_ENV)},
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        (self.root / "tracked.txt").write_text("baseline\n", encoding="utf-8")
        (self.root / "make").mkdir()
        (self.root / "make/ci.mk").write_text(
            "ci.local.quick.run: " + " ".join(MANIFEST_TARGETS) + "\n"
            "\t@git diff --check\n"
            '\t@echo "[OK] local quick gate passed"\n',
            encoding="utf-8",
        )
        for path in set(evidence.scans.COMMON_AUTHORITY).union(*evidence.scans.AUTHORITY.values()):
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("fixture authority\n")
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(self.root), "-c", "user.name=Codex Test",
             "-c", "user.email=codex-test@example.invalid", "commit", "-q", "-m", "fixture"],
            check=True,
        )
        self.head = subprocess.run(
            ["git", "-C", str(self.root), "rev-parse", "HEAD"],
            check=True, text=True, stdout=subprocess.PIPE,
        ).stdout.strip()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _record_scan_success(self) -> None:
        for kind in evidence.scans.AUTHORITY:
            evidence.scans.record_scan_success(self.root, kind)

    def _runner(self, calls):
        def runner(command, **kwargs):
            calls.append(command)
            if "env" in kwargs:
                with mock.patch.dict(os.environ, kwargs["env"]):
                    self._record_scan_success()
            return subprocess.CompletedProcess(command, 0)
        return runner

    def _run_all_shards(self, shards=2, calls=None):
        calls = [] if calls is None else calls
        with mock.patch.object(evidence, "is_linked_worktree", return_value=False):
            for index in range(shards):
                evidence.run_shard(self.root, shards, index, runner=self._runner(calls))
        return calls

    def _part_path(self, index, shards=2):
        return evidence.shard_part_path(self.root, self.head, index, shards)

    def _tamper(self, index, key, value, shards=2):
        path = self._part_path(index, shards)
        part = json.loads(path.read_text(encoding="utf-8"))
        part[key] = value
        path.write_text(json.dumps(part), encoding="utf-8")

    def test_only_verify_reports_a_pure_verification_label(self) -> None:
        self.assertEqual(evidence.result_label("verify"), "VERIFIED")
        for mode in ("run", "shard", "compose", "prune"):
            self.assertEqual(evidence.result_label(mode), "RECORDED", mode)

    def test_default_entry_shards_and_composes_in_the_primary_worktree(self) -> None:
        calls: list[list[str]] = []
        with mock.patch.object(evidence, "is_linked_worktree", return_value=False):
            receipt = evidence.run_default(self.root, shards=2, runner=self._runner(calls))
        assert receipt is not None
        self.assertEqual(evidence.verify(self.root, self.head), receipt)
        manifest = list(MANIFEST_TARGETS)
        self.assertEqual(calls, [["make", "--no-print-directory", *manifest[0::2]],
                                 ["make", "--no-print-directory", *manifest[1::2]]])

    def test_default_entry_keeps_the_single_governed_runner_in_a_linked_worktree(self) -> None:
        calls: list[list[str]] = []
        with mock.patch.object(evidence, "is_linked_worktree", return_value=True):
            evidence.run_default(self.root, shards=2, runner=self._runner(calls))
        self.assertEqual(calls, [["python3", "scripts/dev/local_dev_frontend_quick.py", "--full-ci-local-quick"]])

    def test_passed_shard_is_reused_on_resume(self) -> None:
        self._run_all_shards()
        resumed: list[list[str]] = []
        with mock.patch.object(evidence, "is_linked_worktree", return_value=False):
            path = evidence.run_shard(self.root, 2, 0, runner=self._runner(resumed))
        self.assertEqual(resumed, [])
        self.assertEqual(path, self._part_path(0))

    def test_shard_is_rerun_when_its_recorded_coverage_is_stale(self) -> None:
        self._run_all_shards()
        self._tamper(0, "coverage", {"protocol": "stale"})
        calls: list[list[str]] = []
        with mock.patch.object(evidence, "is_linked_worktree", return_value=False):
            evidence.run_shard(self.root, 2, 0, runner=self._runner(calls))
        self.assertEqual(len(calls), 1)

    def test_monolithic_recipe_line_absent_from_the_shard_path_fails_closed(self) -> None:
        (self.root / "make/ci.mk").write_text(
            "ci.local.quick.run: " + " ".join(MANIFEST_TARGETS) + "\n"
            "\t@git diff --check\n\t@python3 scripts/verify/a_new_check.py\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(evidence.EvidenceError, "not reproduced by the sharded lane"):
            evidence.assert_quick_recipe_covered(self.root)

    def test_declared_recipe_requires_a_body(self) -> None:
        (self.root / "make/ci.mk").write_text(
            "ci.local.quick.run: " + " ".join(MANIFEST_TARGETS) + "\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(evidence.EvidenceError, "declares no recipe"):
            evidence.assert_quick_recipe_covered(self.root)

    def test_shards_compose_into_one_verifiable_exact_head_receipt(self) -> None:
        calls = self._run_all_shards()
        manifest = list(MANIFEST_TARGETS)
        self.assertEqual(calls[0], ["make", "--no-print-directory", *manifest[0::2]])
        self.assertEqual(calls[1], ["make", "--no-print-directory", *manifest[1::2]])
        receipt = evidence.compose(self.root, 2, self.head)
        self.assertEqual(evidence.verify(self.root, self.head), receipt)
        payload = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual(payload["head"], self.head)
        self.assertEqual(payload["suite"], evidence.SUITE)
        self.assertEqual(payload["producer"], evidence.PRODUCER)
        self.assertEqual(payload["coverage"]["protocol"], evidence.scans.COVERAGE_PROTOCOL)
        composition = json.loads(
            (evidence.shard_root(self.root, self.head) / "composition.json").read_text(encoding="utf-8")
        )
        self.assertEqual([part["index"] for part in composition["parts"]], [0, 1])

    def test_missing_shard_part_cannot_compose(self) -> None:
        with mock.patch.object(evidence, "is_linked_worktree", return_value=False):
            evidence.run_shard(self.root, 2, 0, runner=self._runner([]))
        with self.assertRaisesRegex(evidence.EvidenceError, "no part receipt"):
            evidence.compose(self.root, 2, self.head)
        self.assertFalse(evidence.evidence_path(self.root, self.head).exists())

    def test_part_with_extra_or_reordered_targets_is_rejected(self) -> None:
        self._run_all_shards()
        self._tamper(1, "targets", list(MANIFEST_TARGETS[1::2]) + ["verify.injected"])
        with self.assertRaisesRegex(evidence.EvidenceError, "does not carry the declared shard targets"):
            evidence.compose(self.root, 2, self.head)
        self._tamper(1, "targets", list(reversed(MANIFEST_TARGETS[1::2])))
        with self.assertRaisesRegex(evidence.EvidenceError, "does not carry the declared shard targets"):
            evidence.compose(self.root, 2, self.head)
        self.assertFalse(evidence.evidence_path(self.root, self.head).exists())

    def test_part_bound_to_another_candidate_is_rejected(self) -> None:
        self._run_all_shards()
        self._tamper(1, "tree", "b" * 40)
        with self.assertRaisesRegex(evidence.EvidenceError, "binds another candidate"):
            evidence.compose(self.root, 2, self.head)
        self._tamper(1, "tree", evidence.git(self.root, "rev-parse", "HEAD^{tree}"))
        self._tamper(0, "head", "c" * 40)
        with self.assertRaisesRegex(evidence.EvidenceError, "binds another candidate"):
            evidence.compose(self.root, 2, self.head)

    def test_unpassed_shard_is_rejected(self) -> None:
        self._run_all_shards()
        self._tamper(0, "status", "failed")
        with self.assertRaisesRegex(evidence.EvidenceError, "not a passed shard"):
            evidence.compose(self.root, 2, self.head)

    def test_shard_layout_mismatch_is_rejected(self) -> None:
        self._run_all_shards()
        self._tamper(0, "shards", 3)
        with self.assertRaisesRegex(evidence.EvidenceError, "layout is invalid"):
            evidence.compose(self.root, 2, self.head)

    def test_compose_revalidates_scanner_coverage_proofs(self) -> None:
        self._run_all_shards()
        folder = evidence.shard_root(self.root, self.head) / "scan-proofs"
        for kind in evidence.scans.AUTHORITY:
            (folder / (kind + ".json")).unlink()
        with self.assertRaisesRegex(evidence.EvidenceError, "scanner proof missing or invalid"):
            evidence.compose(self.root, 2, self.head)
        self.assertFalse(evidence.evidence_path(self.root, self.head).exists())

    def test_failed_shard_issues_no_part(self) -> None:
        def runner(command, **_kwargs):
            return subprocess.CompletedProcess(command, 23)

        with mock.patch.object(evidence, "is_linked_worktree", return_value=False):
            with self.assertRaisesRegex(evidence.QuickRunFailed, "receipt not issued"):
                evidence.run_shard(self.root, 2, 0, runner=runner)
        self.assertFalse(self._part_path(0).exists())

    def test_shard_requires_a_clean_primary_worktree(self) -> None:
        unused = mock.Mock()
        with mock.patch.object(evidence, "is_linked_worktree", return_value=True):
            with self.assertRaisesRegex(evidence.EvidenceError, "primary worktree"):
                evidence.run_shard(self.root, 2, 0, runner=unused)
        with self.assertRaisesRegex(evidence.EvidenceError, "shards must be"):
            evidence.run_shard(self.root, 0, 0, runner=unused)
        with self.assertRaisesRegex(evidence.EvidenceError, "inside"):
            evidence.run_shard(self.root, 2, 2, runner=unused)
        unused.assert_not_called()

    def test_dirty_worktree_cannot_record_a_shard(self) -> None:
        (self.root / "dirty.txt").write_text("dirty\n", encoding="utf-8")
        with mock.patch.object(evidence, "is_linked_worktree", return_value=False):
            with self.assertRaisesRegex(evidence.EvidenceError, "clean worktree"):
                evidence.run_shard(self.root, 2, 0, runner=mock.Mock())
        self.assertFalse(self._part_path(0).exists())


class DeclaredManifestTests(unittest.TestCase):
    def _manifest_root(self, text):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        make = Path(directory.name) / "make"
        make.mkdir()
        (make / "ci.mk").write_text(text, encoding="utf-8")
        return Path(directory.name)

    def test_real_declared_manifest_is_literal_and_unique(self) -> None:
        targets = evidence.required_targets(ROOT)
        self.assertGreater(len(targets), 1)
        self.assertEqual(targets[0], "guard.prod.forbid")
        self.assertEqual(len(set(targets)), len(targets))
        self.assertTrue(all(not token.startswith("$") and "%" not in token and ":" not in token for token in targets))
        self.assertIn("verify.ui_contract.delivery_surface.unit", targets)

    def test_declared_manifest_drift_is_rejected(self) -> None:
        cases = {
            "duplicate": "ci.local.quick.run: guard.prod.forbid verify.a verify.a\n",
            "line_continuation": "ci.local.quick.run: guard.prod.forbid verify.a \\\n\tverify.b\n",
            "variable": "ci.local.quick.run: guard.prod.forbid $(EXTRA)\n",
            "pattern": "ci.local.quick.run: guard.prod.forbid verify.%\n",
            "target_prefix": "ci.local.quick.run: guard.prod.forbid verify.a:dep\n",
            "wrong_first": "ci.local.quick.run: verify.a guard.prod.forbid\n",
            "duplicate_row": "ci.local.quick.run: guard.prod.forbid verify.a\nci.local.quick.run: guard.prod.forbid\n",
            "absent": "# no declaration here\n",
        }
        for name, text in cases.items():
            with self.subTest(name=name):
                with self.assertRaises(evidence.EvidenceError):
                    evidence.required_targets(self._manifest_root(text))



if __name__ == "__main__":
    unittest.main()
