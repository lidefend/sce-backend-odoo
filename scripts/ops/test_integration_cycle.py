from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.ops import integration_cycle as cycle


class SnapshotTests(unittest.TestCase):
    def test_snapshot_distinguishes_committed_dirty_and_untracked_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            (root / "clean.txt").write_text("clean\n", encoding="utf-8")
            (root / "dirty.txt").write_text("before\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "baseline"], cwd=root, check=True)
            (root / "dirty.txt").write_text("after\n", encoding="utf-8")
            (root / "new.txt").write_text("new\n", encoding="utf-8")

            payload = cycle.snapshot(root, ["clean.txt", "dirty.txt", "new.txt", "absent.txt"])

            states = {row["path"]: row["state"] for row in payload["paths"]}
            self.assertFalse(payload["clean"])
            self.assertEqual(states["clean.txt"], "committed")
            self.assertEqual(states["dirty.txt"], "dirty_or_untracked")
            self.assertEqual(states["new.txt"], "dirty_or_untracked")
            self.assertEqual(states["absent.txt"], "absent")
            self.assertEqual(len(payload["head"]), 40)


class GateTests(unittest.TestCase):
    @staticmethod
    def check(run, job, state, workflow="gate", name="check"):
        return {"__typename": "CheckRun", "workflowName": workflow, "name": name,
                "detailsUrl": f"https://github.com/owner/repo/actions/runs/{run}/job/{job}",
                "status": "IN_PROGRESS" if state == "PENDING" else "COMPLETED",
                "conclusion": "" if state == "PENDING" else state}

    def test_new_success_supersedes_old_failure_in_either_api_order(self):
        rows = [self.check(10, 100, "FAILURE"), self.check(11, 101, "SUCCESS")]
        for ordered in (rows, rows[::-1]):
            self.assertEqual(cycle.checks_ready(ordered), (True, [], []))

    def test_latest_failure_cancel_or_pending_cannot_reuse_old_success(self):
        for state in ("FAILURE", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "PENDING"):
            with self.subTest(state=state):
                self.assertFalse(cycle.checks_ready([
                    self.check(10, 100, "SUCCESS"), self.check(11, 101, state)])[0])

    def test_same_run_retry_uses_new_job_identity(self):
        self.assertTrue(cycle.checks_ready([
            self.check(10, 100, "CANCELLED"), self.check(10, 101, "SUCCESS")])[0])

    def test_late_finishing_old_run_does_not_override_new_run(self):
        old = self.check(10, 100, "FAILURE")
        old["completedAt"] = "2026-10-29T12:00:00Z"
        new = self.check(11, 101, "SUCCESS")
        new["completedAt"] = "2026-10-29T11:00:00Z"
        self.assertTrue(cycle.checks_ready([old, new])[0])

    def test_same_name_in_different_workflows_is_not_collapsed(self):
        self.assertFalse(cycle.checks_ready([
            self.check(10, 100, "FAILURE", workflow="one"),
            self.check(11, 101, "SUCCESS", workflow="two")])[0])

    def test_ambiguous_identity_never_selects_a_success(self):
        for changes in ({"workflowName": ""}, {"detailsUrl": "invalid"},
                        {"detailsUrl": "https://example.com/owner/repo/actions/runs/11/job/101"},
                        {"detailsUrl": "https://github.com/other/repo/actions/runs/11/job/101"}):
            old = self.check(10, 100, "SUCCESS")
            new = self.check(11, 101, "SUCCESS")
            old.update(changes)
            with self.subTest(changes=changes):
                self.assertFalse(cycle.checks_ready([old, new])[0])

    def test_conflicting_duplicate_job_identity_blocks(self):
        self.assertFalse(cycle.checks_ready([
            self.check(10, 100, "FAILURE"), self.check(10, 100, "SUCCESS")])[0])

    def test_nonterminal_status_cannot_use_stale_success_conclusion(self):
        row = self.check(10, 100, "SUCCESS")
        row["status"] = "IN_PROGRESS"
        self.assertFalse(cycle.checks_ready([row])[0])

    def test_empty_checks_and_missing_required_check_block(self):
        self.assertFalse(cycle.checks_ready([])[0])
        self.assertFalse(cycle.checks_ready([self.check(10, 100, "SUCCESS")],
                                          required_names={"required"})[0])

    def test_merge_readiness_preserves_head_quick_and_platform_boundaries(self):
        head = "a" * 40
        rows = [self.check(10, 100, "SUCCESS", workflow=name, name=name)
                for name in cycle.REQUIRED_MERGE_CHECKS]
        base = {"state": "OPEN", "headRefOid": head, "mergeable": "MERGEABLE",
                "mergeStateStatus": "CLEAN", "statusCheckRollup": rows}
        for delta, quick, expected in (({}, True, 0), ({"headRefOid": "b" * 40}, True, 1),
                                     ({}, False, 1), ({"mergeStateStatus": "BLOCKED"}, True, 1),
                                     ({"state": "CLOSED"}, True, 1),
                                     ({"statusCheckRollup": rows[:-1]}, True, 1)):
            with self.subTest(delta=delta, quick=quick), \
                    patch.object(cycle, "git", return_value=head), \
                    patch.object(cycle, "_receipt_verified", return_value=quick), \
                    patch.object(cycle.subprocess, "run", return_value=subprocess.CompletedProcess(
                        [], 0, stdout=json.dumps({**base, **delta}), stderr="")):
                code, _ = cycle.merge_readiness(Path("/unused"), 769)
                self.assertEqual(code, expected)

    def test_fast_gates_aggregates_independent_failures(self):
        def fake_runner(command, **kwargs):
            code = 1 if "verify.frontend.lint.src" in command else 0
            return subprocess.CompletedProcess(command, code)

        with tempfile.TemporaryDirectory() as tmp:
            payload = cycle.fast_gates(Path(tmp), Path(tmp) / "logs", runner=fake_runner)

        self.assertFalse(payload["summary"]["ok"])
        self.assertEqual(payload["summary"]["failed"], ["frontend_lint"])
        self.assertEqual(len(payload["results"]), len(cycle.FAST_GATES))

    def test_checks_ready_separates_failures_and_pending(self):
        ready, failed, pending = cycle.checks_ready(
            [
                {"name": "ok", "conclusion": "SUCCESS"},
                {"name": "skip", "conclusion": "SKIPPED"},
                {"name": "bad", "conclusion": "FAILURE"},
                {"name": "wait", "status": "IN_PROGRESS"},
            ]
        )
        self.assertFalse(ready)
        self.assertEqual(failed, ["bad"])
        self.assertEqual(pending, ["wait"])

    def test_checks_ready_accepts_terminal_success(self):
        ready, failed, pending = cycle.checks_ready(
            [
                {"name": "ok", "conclusion": "SUCCESS"},
                {"name": "skip", "state": "SKIPPED"},
            ]
        )
        self.assertTrue(ready)
        self.assertEqual(failed, [])
        self.assertEqual(pending, [])

    def test_quick_paths_are_bound_to_head(self):
        root = Path("/tmp/example")
        meta, log = cycle.quick_paths(root, "0123456789abcdef")
        self.assertIn("quick-0123456789ab", str(meta))
        self.assertEqual(meta.with_suffix(".log"), log)

    def test_quick_env_removes_parent_make_overrides(self):
        env = cycle.quick_env(
            {
                "PATH": "/usr/bin",
                "MAKEFLAGS": "SUBCOMMAND=fast-gates",
                "MFLAGS": "-j2",
                "MAKELEVEL": "1",
                "MAKEOVERRIDES": "SUBCOMMAND=fast-gates",
            }
        )
        self.assertEqual(env, {"PATH": "/usr/bin"})


if __name__ == "__main__":
    unittest.main()
