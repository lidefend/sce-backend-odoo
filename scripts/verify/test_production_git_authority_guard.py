#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "production_git_authority_guard",
    ROOT / "scripts/verify/production_git_authority_guard.py",
)
assert SPEC and SPEC.loader
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)
SHA = "a" * 40


def runner(
    *,
    head: str = SHA,
    live: str = SHA,
    tracking: str = SHA,
    remote: str = guard.APPROVED_REMOTE_URL,
    status: str = "",
    detached: bool = False,
    network_failure: bool = False,
):
    def run(command: list[str], _timeout: int):
        key = tuple(command)
        if key == ("git", "rev-parse", "--is-inside-work-tree"):
            return 0, "true", ""
        if key == ("git", "symbolic-ref", "--quiet", "--short", "HEAD"):
            return (1, "", "detached") if detached else (0, "main", "")
        if key == ("git", "rev-parse", "HEAD"):
            return 0, head, ""
        if key == ("git", "status", "--porcelain", "--untracked-files=all"):
            return 0, status, ""
        if key == ("git", "remote", "get-url", "origin"):
            return 0, remote, ""
        if key == ("git", "rev-parse", "refs/remotes/origin/main"):
            return 0, tracking, ""
        if key == ("git", "ls-remote", "--heads", "origin", "main"):
            if network_failure:
                return 128, "", "network unavailable"
            return 0, f"{live}\trefs/heads/main", ""
        raise AssertionError(command)

    return run


class ProductionGitAuthorityGuardTests(unittest.TestCase):
    def test_live_remote_local_and_expected_match(self):
        result = guard.evaluate_authority(expected_sha=SHA, runner=runner())
        self.assertEqual(result["status"], "PASS")

    def test_stale_tracking_ref_cannot_mask_remote_change(self):
        result = guard.evaluate_authority(
            expected_sha=SHA,
            runner=runner(tracking=SHA, live="b" * 40),
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(result["stale_remote_ref_detected"])

    def test_wrong_remote_detached_dirty_and_network_each_block(self):
        cases = (
            {"remote": "https://github.com/Leedefend/sce-backend-odoo.git"},
            {"detached": True},
            {"status": " M production.env"},
            {"network_failure": True},
        )
        for case in cases:
            with self.subTest(case=case):
                self.assertEqual(
                    guard.evaluate_authority(expected_sha=SHA, runner=runner(**case))["status"],
                    "BLOCKED",
                )

    def test_local_or_expected_sha_mismatch_blocks(self):
        self.assertEqual(
            guard.evaluate_authority(expected_sha=SHA, runner=runner(head="c" * 40))["status"],
            "BLOCKED",
        )
        self.assertEqual(
            guard.evaluate_authority(expected_sha="d" * 40, runner=runner())["status"],
            "BLOCKED",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
