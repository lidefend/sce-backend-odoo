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

    def main_sha(self) -> str:
        return git(self.root, "rev-parse", "refs/heads/main").stdout.strip()

    def make_branch(self, branch: str, *, push: bool, merged: bool = True) -> str:
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
        if merged:
            git(self.root, "merge", "--ff-only", branch)
            git(self.root, "push", "origin", "main")
        return sha

    def write_manifest(
        self, entries: list[dict[str, object]], *, origin_url: str | None = None
    ) -> None:
        payload = {
            "schema_version": 1,
            "repository": {
                "name": "working",
                "origin_url": str(self.remote) if origin_url is None else origin_url,
            },
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

    def reviewed_entry(
        self,
        branch: str,
        local_sha: str,
        remote_sha: str | None,
        *,
        authorization: str = "owner authorization 2026-10-04",
        reviewed_at: str = "2026-10-04",
    ) -> dict[str, object]:
        entry = self.entry(branch, local_sha, remote_sha)
        entry["containment"] = "reviewed_explicit"
        entry["reviewed_explicit"] = {
            "authorization": authorization,
            "reviewed_at": reviewed_at,
        }
        return entry

    def advance_main_without_the_tip(self, name: str = "landed.txt") -> None:
        """Advance main without containing the branch tip (the squash-merge shape)."""
        marker = self.root / name
        marker.write_text("landed\n", encoding="utf-8")
        git(self.root, "add", name)
        git(
            self.root,
            "-c",
            "user.name=Retirement Test",
            "-c",
            "user.email=retirement@example.invalid",
            "commit",
            "-m",
            "land unrelated main change",
        )
        git(self.root, "push", "origin", "main")

    def execute(
        self,
        *,
        mode: str = "dry-run",
        bundle: Path | None = None,
        open_branches: set[str] | None = None,
        report: Path | None = None,
        report_persistor=None,
        expected_main: str | None = None,
        remote: str = "origin",
        open_pr_check: str = "github",
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
            expected_main=expected_main if expected_main is not None else self.main_sha(),
            remote=remote,
            open_pr_check=open_pr_check,
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
                expected_main=self.main_sha(),
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
            expected_main=self.main_sha(),
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

    # --- merge proof, live main binding and runtime carriers ----------------
    def test_expected_main_must_match_the_live_remote_main(self) -> None:
        sha = self.make_branch("fix/live-main", push=False)
        self.write_manifest([self.entry("fix/live-main", sha, None)])

        with self.assertRaisesRegex(retirement.RetirementError, "main drift"):
            self.execute(expected_main="0" * 40)

        self.assertEqual(retirement.local_ref_sha(self.root, "fix/live-main"), sha)

    def test_unmerged_branch_is_skipped(self) -> None:
        sha = self.make_branch("fix/never-landed", push=True, merged=False)
        self.write_manifest([self.entry("fix/never-landed", sha, sha)])

        report = self.execute()

        reference = report["references"][0]
        self.assertEqual(reference["assessment"], "skip")
        self.assertTrue(
            any("not contained in origin/main" in reason for reason in reference["assessment_reasons"]),
            reference["assessment_reasons"],
        )
        self.assertEqual(retirement.local_ref_sha(self.root, "fix/never-landed"), sha)
        self.assertEqual(retirement.remote_ref_sha(self.root, "fix/never-landed"), sha)

    def test_squash_shaped_tip_is_skipped_under_default_ancestry_containment(self) -> None:
        sha = self.make_branch("fix/squash-shaped", push=True, merged=False)
        self.advance_main_without_the_tip()
        self.write_manifest([self.entry("fix/squash-shaped", sha, sha)])

        report = self.execute()

        reference = report["references"][0]
        self.assertEqual(reference["assessment"], "skip")
        self.assertTrue(
            any(
                "not contained in origin/main" in reason
                for reason in reference["assessment_reasons"]
            ),
            reference["assessment_reasons"],
        )

    def test_reviewed_explicit_entry_is_eligible_for_a_squash_shaped_tip(self) -> None:
        sha = self.make_branch("fix/reviewed-shaped", push=True, merged=False)
        self.advance_main_without_the_tip()
        self.write_manifest([self.reviewed_entry("fix/reviewed-shaped", sha, sha)])

        report = self.execute()

        self.assertEqual(report["references"][0]["assessment"], "eligible")

    def test_reviewed_explicit_apply_retires_and_creates_the_bundle(self) -> None:
        sha = self.make_branch("fix/reviewed-apply", push=True, merged=False)
        self.advance_main_without_the_tip()
        self.write_manifest([self.reviewed_entry("fix/reviewed-apply", sha, sha)])
        bundle = self.base / "reviewed-recovery.bundle"

        report = self.execute(mode="apply", bundle=bundle)

        self.assertEqual(report["references"][0]["execution"]["status"], "retired")
        self.assertIsNone(retirement.local_ref_sha(self.root, "fix/reviewed-apply"))
        self.assertIsNone(retirement.remote_ref_sha(self.root, "fix/reviewed-apply"))
        self.assertTrue(bundle.exists())

    def test_reviewed_explicit_requires_authorization_and_review_date(self) -> None:
        sha = self.make_branch("fix/reviewed-incomplete", push=True, merged=False)
        self.advance_main_without_the_tip()
        rejected = (
            {"containment": "reviewed_explicit"},
            {
                "containment": "reviewed_explicit",
                "reviewed_explicit": {"authorization": "owner"},
            },
            {
                "containment": "reviewed_explicit",
                "reviewed_explicit": {"authorization": "owner", "reviewed_at": "2026/10/04"},
            },
            {
                "containment": "reviewed_explicit",
                "reviewed_explicit": {"authorization": "", "reviewed_at": "2026-10-04"},
            },
        )
        for override in rejected:
            entry = self.entry("fix/reviewed-incomplete", sha, sha)
            entry.update(override)
            self.write_manifest([entry])
            with self.assertRaises(retirement.RetirementError):
                retirement.load_manifest(self.manifest_path)

    def test_unknown_containment_mode_is_rejected(self) -> None:
        sha = self.make_branch("fix/unknown-containment", push=True, merged=False)
        self.advance_main_without_the_tip()
        entry = self.entry("fix/unknown-containment", sha, sha)
        entry["containment"] = "trust_me"
        self.write_manifest([entry])

        with self.assertRaises(retirement.RetirementError):
            retirement.load_manifest(self.manifest_path)

    def test_reviewed_explicit_still_skips_sha_drift(self) -> None:
        sha = self.make_branch("fix/reviewed-drift", push=True, merged=False)
        self.advance_main_without_the_tip()
        self.write_manifest([self.reviewed_entry("fix/reviewed-drift", "0" * 40, sha)])

        report = self.execute()

        reference = report["references"][0]
        self.assertEqual(reference["assessment"], "skip")
        self.assertTrue(
            any("local SHA drift" in reason for reason in reference["assessment_reasons"]),
            reference["assessment_reasons"],
        )

    def test_reviewed_explicit_still_skips_an_open_pull_request(self) -> None:
        sha = self.make_branch("fix/reviewed-open", push=True, merged=False)
        self.advance_main_without_the_tip()
        self.write_manifest([self.reviewed_entry("fix/reviewed-open", sha, sha)])

        report = self.execute(open_branches={"fix/reviewed-open"})

        reference = report["references"][0]
        self.assertEqual(reference["assessment"], "skip")
        self.assertTrue(
            any("open pull request" in reason for reason in reference["assessment_reasons"]),
            reference["assessment_reasons"],
        )

    def test_reviewed_explicit_still_skips_a_checked_out_branch(self) -> None:
        sha = self.make_branch("fix/reviewed-occupied", push=True, merged=False)
        self.advance_main_without_the_tip()
        git(self.root, "switch", "fix/reviewed-occupied")
        try:
            self.write_manifest([self.reviewed_entry("fix/reviewed-occupied", sha, sha)])
            report = self.execute()
        finally:
            git(self.root, "switch", "main")

        reference = report["references"][0]
        self.assertEqual(reference["assessment"], "skip")
        self.assertTrue(
            any("checked out" in reason for reason in reference["assessment_reasons"]),
            reference["assessment_reasons"],
        )

    def test_reviewed_explicit_still_skips_a_runtime_carrier(self) -> None:
        sha = self.make_branch("fix/reviewed-carried", push=False, merged=False)
        self.write_manifest([self.reviewed_entry("fix/reviewed-carried", sha, None)])
        carrier = self.root / "scripts" / "reviewed_carrier.py"
        carrier.parent.mkdir(exist_ok=True)
        carrier.write_text("BRANCH = 'fix/reviewed-carried'\n", encoding="utf-8")
        git(self.root, "add", "scripts/reviewed_carrier.py")
        git(
            self.root,
            "-c",
            "user.name=Retirement Test",
            "-c",
            "user.email=retirement@example.invalid",
            "commit",
            "-m",
            "carry the reviewed branch identity",
        )
        git(self.root, "push", "origin", "main")

        report = self.execute()

        reference = report["references"][0]
        self.assertEqual(reference["assessment"], "skip")
        self.assertTrue(
            any("runtime carrier" in reason for reason in reference["assessment_reasons"]),
            reference["assessment_reasons"],
        )

    def test_branch_referenced_by_a_runtime_carrier_is_skipped(self) -> None:
        sha = self.make_branch("fix/carried", push=False)
        self.write_manifest([self.entry("fix/carried", sha, None)])
        carrier = self.root / "scripts" / "carrier.py"
        carrier.parent.mkdir()
        carrier.write_text("BRANCH = 'fix/carried'\n", encoding="utf-8")
        git(self.root, "add", "scripts/carrier.py")
        git(
            self.root,
            "-c",
            "user.name=Retirement Test",
            "-c",
            "user.email=retirement@example.invalid",
            "commit",
            "-m",
            "carry the branch identity",
        )
        git(self.root, "push", "origin", "main")

        report = self.execute()

        reference = report["references"][0]
        self.assertEqual(reference["assessment"], "skip")
        self.assertTrue(
            any("runtime carrier" in reason for reason in reference["assessment_reasons"]),
            reference["assessment_reasons"],
        )

    def test_unreadable_remote_is_never_treated_as_absent(self) -> None:
        sha = self.make_branch("fix/unreadable", push=False)
        # The remote URL still matches the manifest, but it is not a usable repository:
        # an unreadable remote must never be interpreted as "the branch does not exist".
        broken = self.base / "broken.git"
        broken.mkdir()
        self.write_manifest(
            [self.entry("fix/unreadable", sha, None)], origin_url=str(broken)
        )
        git(self.root, "remote", "set-url", "origin", str(broken))

        with self.assertRaisesRegex(retirement.RetirementError, "cannot read origin main"):
            self.execute(mode="apply", bundle=self.base / "recovery.bundle")

        self.assertEqual(retirement.local_ref_sha(self.root, "fix/unreadable"), sha)
        self.assertFalse((self.base / "recovery.bundle").exists())

    def test_non_origin_remote_requires_an_explicit_open_pr_provider(self) -> None:
        git(self.root, "remote", "add", "mirror", str(self.remote))
        sha = self.make_branch("fix/mirrored", push=True)
        self.write_manifest([self.entry("fix/mirrored", sha, sha)])

        with self.assertRaisesRegex(retirement.RetirementError, "cannot be checked with the GitHub"):
            self.execute(remote="mirror")

        report = self.execute(remote="mirror", open_pr_check="none")

        self.assertEqual(report["remote"], "mirror")
        self.assertEqual(report["open_pr_check"], "none")
        self.assertEqual(report["expected_main"], self.main_sha())
        self.assertEqual(report["references"][0]["assessment"], "eligible")
        self.assertEqual(retirement.local_ref_sha(self.root, "fix/mirrored"), sha)

    def test_apply_on_a_mirrored_remote_deletes_the_bound_remote_ref(self) -> None:
        git(self.root, "remote", "add", "mirror", str(self.remote))
        sha = self.make_branch("fix/mirrored-apply", push=True)
        self.write_manifest([self.entry("fix/mirrored-apply", sha, sha)])

        report = self.execute(
            mode="apply",
            bundle=self.base / "recovery.bundle",
            remote="mirror",
            open_pr_check="none",
        )

        self.assertEqual(report["references"][0]["execution"]["status"], "retired")
        self.assertIsNone(retirement.remote_ref_sha(self.root, "fix/mirrored-apply", "mirror"))
        self.assertIsNone(retirement.local_ref_sha(self.root, "fix/mirrored-apply"))

    def test_absent_local_entry_retires_only_the_remote_ref(self) -> None:
        sha = self.make_branch("fix/remote-only", push=True)
        git(self.root, "update-ref", "-d", "refs/heads/fix/remote-only")
        self.write_manifest(
            [
                {
                    "branch": "fix/remote-only",
                    "local": {"state": "absent", "sha": None},
                    "remote": {"state": "present", "sha": sha},
                    "reason": "reviewed historical reference",
                    "evidence": ["test evidence"],
                }
            ]
        )
        bundle = self.base / "recovery.bundle"

        report = self.execute(mode="apply", bundle=bundle)

        self.assertEqual(report["references"][0]["assessment"], "eligible")
        self.assertEqual(report["references"][0]["local_expected_state"], "absent")
        self.assertEqual(
            report["references"][0]["execution"]["details"],
            ["remote_deleted", "local_absent_confirmed"],
        )
        self.assertIsNone(retirement.remote_ref_sha(self.root, "fix/remote-only"))
        self.assertIsNone(retirement.local_ref_sha(self.root, "fix/remote-only"))

    def test_local_ref_outliving_an_absent_declaration_is_skipped(self) -> None:
        sha = self.make_branch("fix/declared-absent", push=True)
        self.write_manifest(
            [
                {
                    "branch": "fix/declared-absent",
                    "local": {"state": "absent", "sha": None},
                    "remote": {"state": "present", "sha": sha},
                    "reason": "reviewed historical reference",
                    "evidence": ["test evidence"],
                }
            ]
        )

        report = self.execute()

        reference = report["references"][0]
        self.assertEqual(reference["assessment"], "skip")
        self.assertIn("declared absent but exists", reference["assessment_reasons"][0])

    def test_emit_manifest_and_inventory_bind_the_live_main(self) -> None:
        contained = self.make_branch("fix/contained", push=True)
        unmerged = self.make_branch("fix/unmerged", push=True, merged=False)
        released = self.make_branch("release/rc-1", push=True)
        manifest_path = self.base / "emitted-manifest.json"
        inventory_path = self.base / "inventory.json"

        with mock.patch.object(
            sys,
            "argv",
            [
                "retire_historical_branch_refs.py",
                "--manifest",
                str(manifest_path),
                "--remote",
                "origin",
                "--expected-main",
                self.main_sha(),
                "--open-pr-provider",
                "github",
                "--emit-manifest",
                str(manifest_path),
                "--emit-inventory",
                str(inventory_path),
            ],
        ):
            cwd = Path.cwd()
            os.chdir(self.root)
            try:
                exit_code = retirement.main()
            finally:
                os.chdir(cwd)

        self.assertEqual(exit_code, 0)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        branches = [item["branch"] for item in manifest["references"]]
        self.assertEqual(branches, ["fix/contained"])
        entry = manifest["references"][0]
        self.assertEqual(entry["remote"]["sha"], contained)
        self.assertEqual(entry["local"]["sha"], contained)
        payload, entries = retirement.load_manifest(manifest_path)
        self.assertEqual(payload["repository"]["origin_url"], str(self.remote))
        self.assertEqual(entries[0].local_state, "present")

        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        states = {
            item["branch"]: item["status"] for item in inventory["references"]
        }
        self.assertEqual(states["fix/contained"], "contained")
        self.assertEqual(states["fix/unmerged"], "unmerged")
        self.assertEqual(states["release/rc-1"], "protected")
        self.assertEqual(inventory["pull_request_query"]["provider"], "github")
        self.assertEqual(retirement.remote_ref_sha(self.root, "fix/unmerged"), unmerged)
        self.assertEqual(retirement.remote_ref_sha(self.root, "release/rc-1"), released)

    def test_emit_manifest_refuses_a_stale_expected_main(self) -> None:
        self.make_branch("fix/contained", push=True)
        with mock.patch.object(
            sys,
            "argv",
            [
                "retire_historical_branch_refs.py",
                "--manifest",
                str(self.base / "unused.json"),
                "--remote",
                "origin",
                "--expected-main",
                "0" * 40,
                "--emit-manifest",
                str(self.base / "emitted-manifest.json"),
            ],
        ):
            cwd = Path.cwd()
            os.chdir(self.root)
            try:
                exit_code = retirement.main()
            finally:
                os.chdir(cwd)

        self.assertEqual(exit_code, 2)
        self.assertFalse((self.base / "emitted-manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
