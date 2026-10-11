#!/usr/bin/env python3
"""Lock the parallel scan group's declaration to its actual behavior.

The group exists to remove a serial sum, not an assertion: the same three
governed targets must still run, each through the make entry point that owns its
command, and any non-zero member must still fail the lane. These tests read the
declaration out of make/ci.mk and out of the makefile's own prerequisites, so a
recipe that quietly stops covering a scan cannot pass as "still green".
"""
from __future__ import annotations

import os
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import trusted_scan_group as group  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def _rule(target: str) -> tuple[list[str], list[str]]:
    """Prerequisites and recipe lines of one literal make rule."""
    prerequisites: list[str] = []
    recipe: list[str] = []
    seen = False
    for line in (ROOT / "make/ci.mk").read_text(encoding="utf-8").splitlines():
        if line.startswith("\t"):
            if seen:
                recipe.append(line.strip())
            continue
        name, separator, rest = line.partition(":")
        if separator and name.strip() == target:
            prerequisites = rest.split()
            seen = True
            continue
        if seen:
            break
    assert seen, f"{target} is not declared in make/ci.mk"
    return prerequisites, recipe


class GroupDeclarationTests(unittest.TestCase):
    def test_group_covers_exactly_the_three_governed_scans(self) -> None:
        self.assertEqual(list(group.SCAN_MEMBERS), [
            "security.secrets.scan",
            "security.personal_data_scan",
            "repository.clean_history.scan",
        ])
        self.assertEqual(len(set(group.SCAN_MEMBERS)), len(group.SCAN_MEMBERS))

    def test_each_scan_target_still_owns_its_own_command(self) -> None:
        # A member is covered when it still runs its own command through its own
        # declared prerequisite. The owning prerequisite is per target: the two
        # secret/personal passes gate on their scan unit, the history pass gates
        # on the shared production guard. Asserting one common prerequisite would
        # invite a redundant, non-owning prerequisite just to satisfy the test.
        owner = {
            "security.secrets.scan": (
                "scripts/ci/secret_scan.py",
                {"security.online_capture.unit"},
            ),
            "security.personal_data_scan": (
                "scripts/ci/personal_data_scan.py",
                {"security.personal_data.unit"},
            ),
            "repository.clean_history.scan": (
                "scripts/verify/repository_clean_history_guard.py",
                {"guard.prod.forbid"},
            ),
        }
        for target in group.SCAN_MEMBERS:
            command, owning_prerequisites = owner[target]
            prerequisites, recipe = _rule(target)
            self.assertIn(command, " ".join(recipe), target)
            self.assertTrue(
                owning_prerequisites.issubset(set(prerequisites)),
                f"{target} prerequisites {prerequisites} lost {owning_prerequisites}",
            )

    def test_clean_history_reaches_the_scans_through_the_group_only(self) -> None:
        prerequisites, recipe = _rule("verify.repository.clean_history")
        self.assertIn("security.trusted_scan.group", prerequisites)
        for scan in group.SCAN_MEMBERS:
            self.assertNotIn(scan, prerequisites, scan)
        self.assertEqual(len(recipe), 1)

    def test_group_entry_point_is_a_driver_the_lane_compiles_and_tests(self) -> None:
        prerequisites, recipe = _rule("security.trusted_scan.group")
        self.assertIn("security.trusted_scan_group.unit", prerequisites)
        self.assertIn("scripts/ci/trusted_scan_group.py", " ".join(recipe))
        unit_prerequisites, unit_recipe = _rule("security.trusted_scan_group.unit")
        self.assertIn("guard.prod.forbid", unit_prerequisites)
        text = " ".join(unit_recipe)
        self.assertIn("scripts/ci/trusted_scan_group.py", text)
        self.assertIn("scripts/ci/test_trusted_scan_group.py", text)


class WorkerBudgetTests(unittest.TestCase):
    def test_requested_count_is_bounded_by_the_member_count(self) -> None:
        self.assertEqual(group.resolve_jobs(8, 3), 3)
        self.assertEqual(group.resolve_jobs(2, 3), 2)

    def test_machine_default_uses_cpu_and_memory_like_a_ratchet(self) -> None:
        self.assertEqual(group.resolve_jobs(None, 8, cpu=16, memory=64 * 1024**3), 8)
        self.assertEqual(group.resolve_jobs(None, 8, cpu=16, memory=3 * 1024**3), 1)

    def test_unknown_memory_keeps_only_the_cpu_bound(self) -> None:
        self.assertEqual(group.resolve_jobs(None, 8, cpu=4, memory=None), 2)
        self.assertEqual(group.resolve_jobs(None, 8, cpu=1, memory=None), 1)

    def test_zero_negative_or_empty_is_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "positive integer"):
            group.resolve_jobs(0, 3, cpu=8, memory=64 * 1024**3)
        with self.assertRaisesRegex(ValueError, "positive integer"):
            group.resolve_jobs(-1, 3, cpu=8, memory=64 * 1024**3)
        with self.assertRaisesRegex(ValueError, "at least one member"):
            group.resolve_jobs(None, 0, cpu=8, memory=64 * 1024**3)


class RunMembersTests(unittest.TestCase):
    def _popen(self, active: list[int], lock: threading.Lock, failing: str | None = None):
        class _Process:
            def __init__(self, returncode: int) -> None:
                self.returncode = returncode

            def communicate(self):
                time.sleep(0.1)
                return "", None

        def popen(command, **_kwargs):
            with lock:
                active[0] += 1
                active[1] = max(active[1], active[0])
            time.sleep(0.05)
            with lock:
                active[0] -= 1
            target = command[-1]
            return _Process(1 if target == failing else 0)

        return popen

    def test_every_member_runs_and_the_declared_order_is_preserved(self) -> None:
        lock, active = threading.Lock(), [0, 0]
        results = group.run_members(ROOT, group.SCAN_MEMBERS, 3, popen=self._popen(active, lock))
        self.assertEqual([row.target for row in results], list(group.SCAN_MEMBERS))
        self.assertTrue(all(row.returncode == 0 for row in results))

    def test_concurrency_never_exceeds_the_requested_workers(self) -> None:
        lock, active = threading.Lock(), [0, 0]
        group.run_members(ROOT, group.SCAN_MEMBERS, 2, popen=self._popen(active, lock))
        self.assertLessEqual(active[1], 2)
        self.assertGreaterEqual(active[1], 2)

    def test_serial_worker_count_still_runs_every_member_in_order(self) -> None:
        lock, active = threading.Lock(), [0, 0]
        results = group.run_members(ROOT, group.SCAN_MEMBERS, 1, popen=self._popen(active, lock))
        self.assertEqual(active[1], 1)
        self.assertEqual([row.target for row in results], list(group.SCAN_MEMBERS))

    def test_a_failing_member_keeps_its_exit_and_fails_the_group(self) -> None:
        lock, active = threading.Lock(), [0, 0]
        failing = "security.personal_data_scan"
        results = group.run_members(ROOT, group.SCAN_MEMBERS, 3,
                                    popen=self._popen(active, lock, failing=failing))
        self.assertEqual([row.returncode for row in results], [0, 1, 0])
        with mock.patch("sys.stdout"):
            self.assertEqual(group.report(results, 3), 1)
            self.assertEqual(group.report([row for row in results if row.returncode == 0], 3), 0)


class MainTests(unittest.TestCase):
    def _record_jobs(self):
        calls: list[int] = []

        def fake(root, targets, jobs, popen=None):
            calls.append(jobs)
            return [group.MemberResult(target, 0, "", 0.0) for target in targets]

        return calls, fake

    def test_serial_switch_forces_one_worker(self) -> None:
        calls, fake = self._record_jobs()
        with mock.patch.object(group, "run_members", side_effect=fake), mock.patch("sys.stdout"):
            self.assertEqual(group.main([]), 0)
            self.assertGreaterEqual(calls[-1], 1)
            self.assertEqual(group.main(["--serial"]), 0)
            self.assertEqual(calls[-1], 1)
            with mock.patch.dict(os.environ, {"SC_TRUSTED_SCAN_JOBS": "1"}):
                self.assertEqual(group.main([]), 0)
            self.assertEqual(calls[-1], 1)

    def test_non_integer_environment_jobs_is_refused(self) -> None:
        with mock.patch.dict(os.environ, {"SC_TRUSTED_SCAN_JOBS": "many"}), mock.patch("sys.stderr"):
            with self.assertRaises(SystemExit) as raised:
                group.main([])
        self.assertEqual(raised.exception.code, 2)

    def test_zero_jobs_is_refused_without_running_a_member(self) -> None:
        calls, fake = self._record_jobs()
        with mock.patch.object(group, "run_members", side_effect=fake), mock.patch("sys.stderr"):
            self.assertEqual(group.main(["--jobs", "0"]), 2)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
