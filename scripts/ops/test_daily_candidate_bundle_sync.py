#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import os
import shlex
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("daily_candidate_bundle_sync.py")
SPEC = importlib.util.spec_from_file_location("daily_candidate_bundle_sync", SCRIPT)
assert SPEC and SPEC.loader
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)
GUARD = SCRIPT.with_name("daily_dev_runtime_repo_guard.sh")


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise AssertionError(result.stderr)
    return result.stdout.strip()


class DailyCandidateBundleSyncTests(unittest.TestCase):
    def test_remote_command_preserves_candidate_identity(self) -> None:
        command = sync.remote_command(
            "a" * 40,
            "b" * 40,
            "c" * 64,
            "feature/example",
            "d" * 40,
        )
        self.assertEqual(
            shlex.split(command),
            [
                "python3",
                "-c",
                sync.REMOTE_SYNC,
                "a" * 40,
                "b" * 40,
                "c" * 64,
                "feature/example",
                "d" * 40,
                sync.REMOTE_ROOT,
            ],
        )

    def test_remote_contract_keeps_origin_main_and_uses_detached_candidate(self) -> None:
        source = sync.REMOTE_SYNC
        self.assertIn('git("checkout", "--detach", expected_sha)', source)
        self.assertIn('"refs/daily-candidates/" + source_branch', source)
        self.assertIn('"origin_main_mutated": False', source)
        self.assertNotIn('update-ref", "refs/remotes/origin/main', source)
        self.assertNotIn("reset --hard", source)

    def test_candidate_bundle_switch_and_guard(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            target = root / "target"
            source.mkdir()
            target.mkdir()
            git(source, "init", "-b", "main")
            git(source, "config", "user.name", "Candidate Test")
            git(source, "config", "user.email", "candidate@example.invalid")
            (source / "value.txt").write_text("base\n", encoding="utf-8")
            git(source, "add", "value.txt")
            git(source, "commit", "-m", "base")
            base_sha = git(source, "rev-parse", "HEAD")

            git(source, "switch", "-c", "feature/candidate")
            (source / "candidate.txt").write_text("candidate\n", encoding="utf-8")
            git(source, "add", "candidate.txt")
            git(source, "commit", "-m", "candidate")
            candidate_sha = git(source, "rev-parse", "HEAD")
            git(source, "switch", "main")
            (source / "daily.txt").write_text("daily\n", encoding="utf-8")
            git(source, "add", "daily.txt")
            git(source, "commit", "-m", "daily")
            old_sha = git(source, "rev-parse", "HEAD")

            git(target, "init", "-b", "main")
            git(target, "config", "user.name", "Runtime Test")
            git(target, "config", "user.email", "runtime@example.invalid")
            git(target, "remote", "add", "origin", str(source))
            git(target, "fetch", "origin", "main")
            git(target, "checkout", "-B", "main", "FETCH_HEAD")
            git(target, "update-ref", "refs/remotes/origin/main", old_sha)
            git(target, "branch", "--set-upstream-to=origin/main", "main")

            bundle_path = root / "candidate.bundle"
            git(
                source,
                "bundle",
                "create",
                str(bundle_path),
                "refs/heads/feature/candidate",
                f"^{base_sha}",
            )
            bundle = bundle_path.read_bytes()
            digest = hashlib.sha256(bundle).hexdigest()
            test_program = sync.REMOTE_SYNC.replace(
                'Path("/opt/projects/repos/sce-product-odoo")',
                f"Path({str(target)!r})",
                1,
            )
            result = subprocess.run(
                [
                    "python3",
                    "-c",
                    test_program,
                    candidate_sha,
                    old_sha,
                    digest,
                    "feature/candidate",
                    base_sha,
                    str(target),
                ],
                input=bundle,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertEqual(git(target, "rev-parse", "HEAD"), candidate_sha)
            self.assertEqual(git(target, "branch", "--show-current"), "")
            self.assertEqual(
                git(target, "rev-parse", "refs/remotes/origin/main"), old_sha
            )
            self.assertEqual(
                git(target, "rev-parse", "refs/daily-candidates/feature/candidate"),
                candidate_sha,
            )
            self.assertEqual(git(target, "status", "--porcelain"), "")

            guard_environment = {
                **os.environ,
                "DAILY_DEV_DEPLOYMENT_MODE": "candidate",
                "DAILY_DEV_CANDIDATE_SOURCE_BRANCH": "feature/candidate",
                "DAILY_DEV_CANDIDATE_EXPECTED_SHA": candidate_sha,
            }
            guard = subprocess.run(
                ["bash", str(GUARD)],
                cwd=target,
                env=guard_environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(guard.returncode, 0, guard.stdout + guard.stderr)
            self.assertIn("mode=candidate", guard.stdout)

            main_guard = subprocess.run(
                ["bash", str(GUARD)],
                cwd=target,
                env={**os.environ, "DAILY_DEV_DEPLOYMENT_MODE": "main"},
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertNotEqual(main_guard.returncode, 0)
            self.assertIn("expected branch 'main'", main_guard.stdout)

    def test_candidate_guard_fails_without_explicit_identity(self) -> None:
        source = GUARD.read_text(encoding="utf-8")
        self.assertIn("candidate expected SHA must be a full lowercase commit identity", source)
        self.assertIn("candidate runtime must use detached HEAD", source)
        self.assertIn("candidate evidence ref is missing", source)
        self.assertIn("main deployment mode cannot override the expected branch", source)


if __name__ == "__main__":
    unittest.main()
