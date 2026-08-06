#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import shlex
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("daily_runtime_bundle_sync.py")
SPEC = importlib.util.spec_from_file_location("daily_runtime_bundle_sync", SCRIPT)
assert SPEC and SPEC.loader
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode:
        raise AssertionError(result.stderr)
    return result.stdout.strip()


class DailyRuntimeBundleSyncTests(unittest.TestCase):
    def test_remote_command_preserves_multiline_program_as_one_argument(self) -> None:
        expected = "a" * 40
        old = "b" * 40
        digest = "c" * 64
        command = sync.remote_command(expected, old, digest)
        self.assertEqual(
            shlex.split(command),
            ["python3", "-c", sync.REMOTE_SYNC, expected, old, digest, sync.REMOTE_ROOT],
        )

    def test_remote_contract_is_fixed_fast_forward_and_fail_closed(self) -> None:
        source = sync.REMOTE_SYNC
        self.assertIn('/opt/projects/repos/sce-product-odoo', source)
        self.assertIn('expected_old_sha', source)
        self.assertIn('bundle digest differs', source)
        self.assertIn('git("pull", "--ff-only"', source)
        self.assertIn('git("update-ref", "refs/remotes/origin/main"', source)
        self.assertIn('remote worktree is not clean', source)
        self.assertIn('candidate is not a fast-forward descendant', source)
        self.assertNotIn('git config', source)
        self.assertNotIn('reset --hard', source)

    def test_remote_program_fast_forwards_main_and_upstream_from_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            target = root / "target"
            source.mkdir()
            target.mkdir()
            git(source, "init", "-b", "main")
            git(source, "config", "user.name", "Bundle Test")
            git(source, "config", "user.email", "bundle@example.invalid")
            (source / "value.txt").write_text("old\n", encoding="utf-8")
            git(source, "add", "value.txt")
            git(source, "commit", "-m", "old")
            old_sha = git(source, "rev-parse", "HEAD")
            (source / "value.txt").write_text("new\n", encoding="utf-8")
            git(source, "commit", "-am", "new")
            expected_sha = git(source, "rev-parse", "HEAD")

            git(target, "init", "-b", "main")
            git(target, "remote", "add", "origin", str(source))
            git(target, "fetch", "origin", old_sha)
            git(target, "checkout", "-B", "main", "FETCH_HEAD")
            git(target, "update-ref", "refs/remotes/origin/main", old_sha)
            git(target, "branch", "--set-upstream-to=origin/main", "main")

            bundle_path = root / "main.bundle"
            git(source, "update-ref", "refs/remotes/origin/main", expected_sha)
            git(source, "bundle", "create", str(bundle_path), "refs/remotes/origin/main", f"^{old_sha}")
            bundle = bundle_path.read_bytes()
            digest = hashlib.sha256(bundle).hexdigest()
            test_program = sync.REMOTE_SYNC.replace(
                'Path("/opt/projects/repos/sce-product-odoo")',
                f'Path({str(target)!r})',
                1,
            )
            result = subprocess.run(
                ["python3", "-c", test_program, expected_sha, old_sha, digest, str(target)],
                input=bundle,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertEqual(git(target, "rev-parse", "HEAD"), expected_sha)
            self.assertEqual(git(target, "rev-parse", "@{upstream}"), expected_sha)
            self.assertEqual(git(target, "status", "--porcelain"), "")
            self.assertEqual((target / "value.txt").read_text(encoding="utf-8"), "new\n")

            (source / "value.txt").write_text("newer\n", encoding="utf-8")
            git(source, "commit", "-am", "newer")
            newer_sha = git(source, "rev-parse", "HEAD")
            second_bundle_path = root / "second.bundle"
            git(source, "update-ref", "refs/remotes/origin/main", newer_sha, expected_sha)
            git(source, "bundle", "create", str(second_bundle_path), "refs/remotes/origin/main", f"^{expected_sha}")
            second_bundle = second_bundle_path.read_bytes()
            (target / "untracked.txt").write_text("dirty\n", encoding="utf-8")
            dirty_result = subprocess.run(
                [
                    "python3", "-c", test_program, newer_sha, expected_sha,
                    hashlib.sha256(second_bundle).hexdigest(), str(target),
                ],
                input=second_bundle,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertNotEqual(dirty_result.returncode, 0)
            self.assertIn("remote worktree is not clean", dirty_result.stderr.decode())
            self.assertEqual(git(target, "rev-parse", "HEAD"), expected_sha)
            self.assertEqual(git(target, "rev-parse", "@{upstream}"), expected_sha)


if __name__ == "__main__":
    unittest.main()
