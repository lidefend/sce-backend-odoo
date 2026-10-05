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


def init_repo(path: Path) -> None:
    path.mkdir()
    git(path, "init", "-b", "main")
    git(path, "config", "user.name", "Bundle Test")
    git(path, "config", "user.email", "bundle@example.invalid")


def build_pair(root: Path) -> tuple[Path, Path, str, str]:
    """Return a source repo with old/new main and a target tracking old main."""
    source = root / "source"
    target = root / "target"
    init_repo(source)
    init_repo(target)
    (source / "value.txt").write_text("old\n", encoding="utf-8")
    git(source, "add", "value.txt")
    git(source, "commit", "-m", "old")
    old_sha = git(source, "rev-parse", "HEAD")
    (source / "value.txt").write_text("new\n", encoding="utf-8")
    git(source, "commit", "-am", "new")
    expected_sha = git(source, "rev-parse", "HEAD")

    git(target, "remote", "add", "origin", str(source))
    git(target, "fetch", "origin", old_sha)
    git(target, "checkout", "-B", "main", "FETCH_HEAD")
    git(target, "update-ref", "refs/remotes/origin/main", old_sha)
    git(target, "branch", "--set-upstream-to=origin/main", "main")
    return source, target, old_sha, expected_sha


def make_bundle(root: Path, source: Path, old_sha: str, expected_sha: str) -> tuple[bytes, str]:
    bundle_path = root / "main.bundle"
    git(source, "update-ref", "refs/remotes/origin/main", expected_sha)
    git(source, "bundle", "create", str(bundle_path), "refs/remotes/origin/main", f"^{old_sha}")
    payload = bundle_path.read_bytes()
    return payload, hashlib.sha256(payload).hexdigest()


def detach_candidate(target: Path, record_ref: str | None = "refs/daily-candidates/codex/test-candidate") -> str:
    # Commit while detached so refs/heads/main stays at the expected old SHA.
    git(target, "checkout", "--detach")
    (target / "candidate.txt").write_text("candidate\n", encoding="utf-8")
    git(target, "add", "candidate.txt")
    git(target, "commit", "-m", "candidate")
    candidate_sha = git(target, "rev-parse", "HEAD")
    if record_ref:
        git(target, "update-ref", record_ref, candidate_sha)
    return candidate_sha


def run_remote(target: Path, bundle: bytes, *identities: str) -> subprocess.CompletedProcess:
    program = sync.REMOTE_SYNC.replace(
        'Path("/opt/projects/repos/sce-product-odoo")',
        f'Path({str(target)!r})',
        1,
    )
    return subprocess.run(
        ["python3", "-c", program, *identities, str(target)],
        input=bundle,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


class DailyRuntimeBundleSyncTests(unittest.TestCase):
    def test_remote_command_preserves_multiline_program_as_one_argument(self) -> None:
        expected = "a" * 40
        old = "b" * 40
        digest = "c" * 64
        candidate = "d" * 40
        command = sync.remote_command(expected, old, digest, candidate)
        self.assertEqual(
            shlex.split(command),
            ["python3", "-c", sync.REMOTE_SYNC, expected, old, digest, candidate, sync.REMOTE_ROOT],
        )

    def test_remote_command_omits_candidate_slot_when_absent(self) -> None:
        expected = "a" * 40
        old = "b" * 40
        digest = "c" * 64
        command = sync.remote_command(expected, old, digest, "")
        self.assertEqual(
            shlex.split(command),
            ["python3", "-c", sync.REMOTE_SYNC, expected, old, digest, "", sync.REMOTE_ROOT],
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
        self.assertIn('normalized_from_candidate', source)
        self.assertIn('refs/daily-candidates/', source)
        self.assertIn('BLOCKED detached HEAD is not a recorded daily candidate', source)
        self.assertNotIn('git config', source)
        self.assertNotIn('reset --hard', source)

    def test_remote_program_fast_forwards_main_and_upstream_from_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target, old_sha, expected_sha = build_pair(root)
            bundle, digest = make_bundle(root, source, old_sha, expected_sha)

            result = run_remote(target, bundle, expected_sha, old_sha, digest, "")
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertIn('"normalized_from_candidate": false', result.stdout.decode())
            self.assertEqual(git(target, "rev-parse", "HEAD"), expected_sha)
            self.assertEqual(git(target, "rev-parse", "@{upstream}"), expected_sha)
            self.assertEqual(git(target, "status", "--porcelain"), "")
            self.assertEqual((target / "value.txt").read_text(encoding="utf-8"), "new\n")

            (source / "value.txt").write_text("newer\n", encoding="utf-8")
            git(source, "commit", "-am", "newer")
            newer_sha = git(source, "rev-parse", "HEAD")
            second, second_digest = make_bundle(root, source, expected_sha, newer_sha)
            (target / "untracked.txt").write_text("dirty\n", encoding="utf-8")
            dirty_result = run_remote(target, second, newer_sha, expected_sha, second_digest, "")
            self.assertNotEqual(dirty_result.returncode, 0)
            self.assertIn("remote worktree is not clean", dirty_result.stderr.decode())
            self.assertEqual(git(target, "rev-parse", "HEAD"), expected_sha)
            self.assertEqual(git(target, "rev-parse", "@{upstream}"), expected_sha)

    def test_remote_program_normalizes_recorded_detached_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target, old_sha, expected_sha = build_pair(root)
            candidate_sha = detach_candidate(target)
            self.assertEqual(git(target, "branch", "--show-current"), "")
            bundle, digest = make_bundle(root, source, old_sha, expected_sha)

            result = run_remote(target, bundle, expected_sha, old_sha, digest, candidate_sha)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertIn('"normalized_from_candidate": true', result.stdout.decode())
            self.assertEqual(git(target, "branch", "--show-current"), "main")
            self.assertEqual(git(target, "rev-parse", "HEAD"), expected_sha)
            self.assertEqual(git(target, "rev-parse", "@{upstream}"), expected_sha)
            self.assertEqual(git(target, "status", "--porcelain"), "")
            self.assertEqual((target / "value.txt").read_text(encoding="utf-8"), "new\n")
            self.assertFalse((target / "candidate.txt").exists())

    def test_remote_program_rejects_unrecorded_detached_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target, old_sha, expected_sha = build_pair(root)
            candidate_sha = detach_candidate(target, record_ref=None)
            bundle, digest = make_bundle(root, source, old_sha, expected_sha)

            result = run_remote(target, bundle, expected_sha, old_sha, digest, candidate_sha)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("detached HEAD is not a recorded daily candidate", result.stderr.decode())
            self.assertEqual(git(target, "rev-parse", "HEAD"), candidate_sha)
            self.assertEqual(git(target, "rev-parse", "refs/heads/main"), old_sha)

    def test_remote_program_rejects_dirty_detached_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target, old_sha, expected_sha = build_pair(root)
            candidate_sha = detach_candidate(target)
            (target / "untracked.txt").write_text("dirty\n", encoding="utf-8")
            bundle, digest = make_bundle(root, source, old_sha, expected_sha)

            result = run_remote(target, bundle, expected_sha, old_sha, digest, candidate_sha)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("remote worktree is not clean", result.stderr.decode())
            self.assertEqual(git(target, "rev-parse", "HEAD"), candidate_sha)

    def test_remote_program_rejects_mismatched_main_ref_for_detached_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target, old_sha, expected_sha = build_pair(root)
            candidate_sha = detach_candidate(target)
            git(target, "update-ref", "refs/heads/main", candidate_sha, old_sha)
            bundle, digest = make_bundle(root, source, old_sha, expected_sha)

            result = run_remote(target, bundle, expected_sha, old_sha, digest, candidate_sha)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("remote main ref differs from the expected old SHA", result.stderr.decode())
            self.assertEqual(git(target, "rev-parse", "HEAD"), candidate_sha)

    def test_remote_program_rejects_detached_candidate_without_declared_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target, old_sha, expected_sha = build_pair(root)
            candidate_sha = detach_candidate(target)
            bundle, digest = make_bundle(root, source, old_sha, expected_sha)

            result = run_remote(target, bundle, expected_sha, old_sha, digest, "")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("remote branch or old SHA differs", result.stderr.decode())
            self.assertEqual(git(target, "rev-parse", "HEAD"), candidate_sha)


if __name__ == "__main__":
    unittest.main()
