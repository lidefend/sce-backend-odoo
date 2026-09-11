from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).with_name("retire_historical_branch_refs.py")
SPEC = importlib.util.spec_from_file_location("retire_historical_branch_refs", MODULE_PATH)
assert SPEC and SPEC.loader
retirement = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = retirement
SPEC.loader.exec_module(retirement)


def git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    process = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if check and process.returncode:
        raise AssertionError(process.stdout)
    return process


class HistoricalBranchRetirementTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.remote = self.base / "remote.git"
        self.root = self.base / "working"
        git(self.base, "init", "--bare", str(self.remote))
        git(self.base, "init", "-b", "main", str(self.root))
        (self.root / "README.md").write_text("base\n", encoding="utf-8")
        git(self.root, "add", "README.md")
        git(
            self.root,
            "-c",
            "user.name=Retirement Test",
            "-c",
            "user.email=retirement@example.invalid",
            "commit",
            "-m",
            "base",
        )
        git(self.root, "remote", "add", "origin", str(self.remote))
        git(self.root, "push", "-u", "origin", "main")
        self.manifest_path = self.base / "manifest.json"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def make_branch(self, branch: str, *, push: bool) -> str:
        git(self.root, "switch", "-c", branch, "main")
        marker = self.root / f"{branch.replace('/', '-')}.txt"
        marker.write_text(f"{branch}\n", encoding="utf-8")
        git(self.root, "add", marker.name)
        git(
            self.root,
            "-c",
            "user.name=Retirement Test",
            "-c",
            "user.email=retirement@example.invalid",
            "commit",
            "-m",
            branch,
        )
        sha = git(self.root, "rev-parse", "HEAD").stdout.strip()
        if push:
            git(self.root, "push", "origin", branch)
        git(self.root, "switch", "main")
        return sha

    def write_manifest(self, entries: list[dict[str, object]]) -> None:
        payload = {
            "schema_version": 1,
            "repository": {"name": "working", "origin_url": str(self.remote)},
            "references": entries,
        }
        self.manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    @staticmethod
    def entry(branch: str, local_sha: str, remote_sha: str | None) -> dict[str, object]:
        return {
            "branch": branch,
            "local": {"sha": local_sha},
            "remote": {
                "state": "present" if remote_sha else "absent",
                "sha": remote_sha,
            },
            "reason": "reviewed historical reference",
            "evidence": ["test evidence"],
        }

    def execute(
        self,
        *,
        mode: str = "dry-run",
        bundle: Path | None = None,
        open_branches: set[str] | None = None,
        report: Path | None = None,
        report_persistor=None,
    ) -> dict[str, object]:
        digest = retirement.manifest_digest(self.manifest_path)
        if mode == "apply" and report is None:
            report = self.base / "retirement-report.json"
        return retirement.execute(
            self.root,
            self.manifest_path,
            mode=mode,
            bundle_path=bundle,
            approved_digest=digest if mode == "apply" else "",
            confirmation=retirement.CONFIRMATION if mode == "apply" else "",
            report_path=report,
            report_persistor=report_persistor or retirement.persist_report,
            open_branch_provider=lambda _root: set(open_branches or set()),
        )

    def test_default_dry_run_does_not_delete_refs(self) -> None:
        sha = self.make_branch("fix/dry-run", push=True)
        self.write_manifest([self.entry("fix/dry-run", sha, sha)])

        report = self.execute()

        self.assertEqual(report["mode"], "dry-run")
        self.assertEqual(report["references"][0]["assessment"], "eligible")
        self.assertEqual(retirement.local_ref_sha(self.root, "fix/dry-run"), sha)
        self.assertEqual(retirement.remote_ref_sha(self.root, "fix/dry-run"), sha)

    def test_sha_drift_and_open_related_work_are_skipped(self) -> None:
        drift_sha = self.make_branch("fix/drift", push=False)
        open_sha = self.make_branch("fix/open-work", push=False)
        self.write_manifest(
            [
                self.entry("fix/drift", "0" * 40, None),
                self.entry("fix/open-work", open_sha, None),
            ]
        )

        report = self.execute(open_branches={"fix/open-work"})

        references = {item["branch"]: item for item in report["references"]}
        self.assertEqual(references["fix/drift"]["assessment"], "skip")
        self.assertIn("local SHA drift", references["fix/drift"]["assessment_reasons"][0])
        self.assertEqual(references["fix/open-work"]["assessment"], "skip")
        self.assertIn("open pull request", references["fix/open-work"]["assessment_reasons"][0])
        self.assertEqual(retirement.local_ref_sha(self.root, "fix/drift"), drift_sha)

    def test_current_worktree_branch_is_skipped(self) -> None:
        sha = self.make_branch("fix/occupied", push=False)
        git(self.root, "switch", "fix/occupied")
        self.write_manifest([self.entry("fix/occupied", sha, None)])

        report = self.execute()

        self.assertEqual(report["references"][0]["assessment"], "skip")
        self.assertIn("checked out", report["references"][0]["assessment_reasons"][0])

    def test_remote_absent_apply_creates_bundle_and_deletes_only_local(self) -> None:
        sha = self.make_branch("fix/local-only", push=False)
        self.write_manifest([self.entry("fix/local-only", sha, None)])
        bundle = self.base / "recovery.bundle"

        report = self.execute(mode="apply", bundle=bundle)

        self.assertEqual(report["references"][0]["execution"]["status"], "retired")
        self.assertEqual(
            report["references"][0]["execution"]["details"],
            ["remote_absent_confirmed", "local_deleted"],
        )
        self.assertIsNone(retirement.local_ref_sha(self.root, "fix/local-only"))
        self.assertTrue(bundle.is_file())
        self.assertEqual(report["retirement_outcome"], "completed")
        durable = json.loads((self.base / "retirement-report.json").read_text())
        self.assertEqual(durable["retirement_outcome"], "completed")
        heads = git(self.root, "bundle", "list-heads", str(bundle)).stdout
        self.assertIn(sha, heads)

    def test_unwritable_report_target_aborts_before_bundle_or_deletion(self) -> None:
        sha = self.make_branch("fix/report-unwritable", push=False)
        self.write_manifest([self.entry("fix/report-unwritable", sha, None)])
        blocked_parent = self.base / "not-a-directory"
        blocked_parent.write_text("occupied by a file\n", encoding="utf-8")
        bundle = self.base / "recovery.bundle"

        with self.assertRaisesRegex(
            retirement.RetirementError,
            "audit report target is not writable; no references deleted",
        ):
            self.execute(
                mode="apply",
                bundle=bundle,
                report=blocked_parent / "report.json",
            )

        self.assertEqual(
            retirement.local_ref_sha(self.root, "fix/report-unwritable"), sha
        )
        self.assertFalse(bundle.exists())

    def test_progress_write_failure_stops_before_next_deletion(self) -> None:
        first = self.make_branch("fix/report-first", push=False)
        second = self.make_branch("fix/report-second", push=False)
        self.write_manifest(
            [
                self.entry("fix/report-first", first, None),
                self.entry("fix/report-second", second, None),
            ]
        )
        report_path = self.base / "progress-report.json"
        calls = 0

        def fail_after_first_deletion(report, path):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise OSError("injected audit sink failure")
            retirement.persist_report(report, path)

        with self.assertRaisesRegex(
            retirement.RetirementError,
            "result recording for fix/report-first status=retired",
        ):
            self.execute(
                mode="apply",
                bundle=self.base / "recovery.bundle",
                report=report_path,
                report_persistor=fail_after_first_deletion,
            )

        self.assertIsNone(retirement.local_ref_sha(self.root, "fix/report-first"))
        self.assertEqual(retirement.local_ref_sha(self.root, "fix/report-second"), second)
        durable = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(durable["retirement_outcome"], "in_progress")
        executions = {item["branch"]: item["execution"] for item in durable["references"]}
        self.assertEqual(executions["fix/report-first"]["status"], "in_progress")
        self.assertEqual(executions["fix/report-second"]["status"], "pending")

    def test_all_skipped_apply_writes_not_executed_report_without_bundle(self) -> None:
        actual = self.make_branch("fix/all-skipped", push=False)
        self.write_manifest([self.entry("fix/all-skipped", "0" * 40, None)])
        bundle = self.base / "must-not-exist.bundle"
        report_path = self.base / "all-skipped-report.json"

        report = self.execute(mode="apply", bundle=bundle, report=report_path)

        self.assertEqual(report["retirement_outcome"], "not_executed")
        self.assertIsNone(report["bundle"])
        self.assertEqual(report["references"][0]["execution"]["status"], "skipped")
        self.assertFalse(bundle.exists())
        self.assertEqual(retirement.local_ref_sha(self.root, "fix/all-skipped"), actual)
        durable = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(durable["retirement_outcome"], "not_executed")

    def test_incomplete_bundle_aborts_before_any_deletion(self) -> None:
        first = self.make_branch("fix/first", push=False)
        second = self.make_branch("fix/second", push=False)
        self.write_manifest(
            [self.entry("fix/first", first, None), self.entry("fix/second", second, None)]
        )
        bundle = self.base / "recovery.bundle"

        with mock.patch.object(
            retirement,
            "verify_bundle",
            side_effect=retirement.RetirementError("bundle incomplete"),
        ):
            with self.assertRaisesRegex(retirement.RetirementError, "bundle incomplete"):
                self.execute(mode="apply", bundle=bundle)

        self.assertEqual(retirement.local_ref_sha(self.root, "fix/first"), first)
        self.assertEqual(retirement.local_ref_sha(self.root, "fix/second"), second)

    def test_apply_rejects_unapproved_manifest_before_bundle_creation(self) -> None:
        sha = self.make_branch("fix/unapproved", push=False)
        self.write_manifest([self.entry("fix/unapproved", sha, None)])
        bundle = self.base / "recovery.bundle"

        with self.assertRaisesRegex(retirement.RetirementError, "approved-manifest"):
            retirement.execute(
                self.root,
                self.manifest_path,
                mode="apply",
                bundle_path=bundle,
                approved_digest="0" * 64,
                confirmation=retirement.CONFIRMATION,
                report_path=self.base / "unapproved-report.json",
                open_branch_provider=lambda _root: set(),
            )

        self.assertFalse(bundle.exists())
        self.assertEqual(retirement.local_ref_sha(self.root, "fix/unapproved"), sha)

    def test_unavailable_related_work_evidence_skips_without_deletion(self) -> None:
        sha = self.make_branch("fix/no-related-proof", push=False)
        self.write_manifest([self.entry("fix/no-related-proof", sha, None)])

        report = retirement.execute(
            self.root,
            self.manifest_path,
            mode="dry-run",
            bundle_path=None,
            approved_digest="",
            confirmation="",
            open_branch_provider=lambda _root: (_ for _ in ()).throw(
                retirement.RetirementError("review service unavailable")
            ),
        )

        self.assertEqual(report["references"][0]["assessment"], "skip")
        self.assertIn("evidence unavailable", report["references"][0]["assessment_reasons"][0])
        self.assertEqual(retirement.local_ref_sha(self.root, "fix/no-related-proof"), sha)

    def test_remote_partial_failure_keeps_local_and_continues(self) -> None:
        rejected = self.make_branch("fix/rejected", push=True)
        accepted = self.make_branch("fix/accepted", push=True)
        self.write_manifest(
            [
                self.entry("fix/rejected", rejected, rejected),
                self.entry("fix/accepted", accepted, accepted),
            ]
        )
        hook = self.remote / "hooks" / "pre-receive"
        hook.write_text(
            "#!/bin/sh\n"
            "while read old new ref; do\n"
            "  if [ \"$ref\" = refs/heads/fix/rejected ] && "
            "[ \"$new\" = 0000000000000000000000000000000000000000 ]; then\n"
            "    echo rejected-by-test >&2\n"
            "    exit 1\n"
            "  fi\n"
            "done\n",
            encoding="utf-8",
        )
        hook.chmod(0o755)

        report = self.execute(mode="apply", bundle=self.base / "recovery.bundle")

        references = {item["branch"]: item for item in report["references"]}
        self.assertEqual(references["fix/rejected"]["execution"]["status"], "partial")
        self.assertEqual(references["fix/accepted"]["execution"]["status"], "retired")
        self.assertEqual(retirement.local_ref_sha(self.root, "fix/rejected"), rejected)
        self.assertIsNone(retirement.local_ref_sha(self.root, "fix/accepted"))
        self.assertEqual(retirement.remote_ref_sha(self.root, "fix/rejected"), rejected)
        self.assertIsNone(retirement.remote_ref_sha(self.root, "fix/accepted"))


if __name__ == "__main__":
    unittest.main()
