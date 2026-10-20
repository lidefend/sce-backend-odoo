from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
