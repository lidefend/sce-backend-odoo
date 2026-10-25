#!/usr/bin/env python3

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import parallel_scan
import secret_scan


class SecretScanTest(unittest.TestCase):
    online_password_name = "LEGACY_SOURCE_PASSWORD"

    def test_online_assignment_is_redacted(self) -> None:
        secret = "fixture-value-that-must-not-be-printed"
        findings = secret_scan.scan_line(f"{self.online_password_name}={secret}")
        self.assertEqual([item.rule for item in findings], ["online_credential_assignment"])
        self.assertNotIn(secret, repr(findings))

    def test_placeholders_are_allowed(self) -> None:
        placeholders = ("<redacted>", "<provided-via-secret-environment>", "${" + self.online_password_name + "}", "...")
        for value in placeholders:
            self.assertEqual(secret_scan.scan_line(f"{self.online_password_name}={value}"), [])

    def test_literal_default_is_rejected(self) -> None:
        findings = secret_scan.scan_line(f'os.getenv("{self.online_password_name}", "not-a-placeholder")')
        self.assertEqual(findings[0].rule, "online_credential_literal_default")

    def test_main_output_never_echoes_matching_value(self) -> None:
        secret = "fixture-value-that-must-not-be-printed"
        stderr = io.StringIO()
        fixture_path = secret_scan.ROOT / "fictional-security-fixture.md"
        with (
            mock.patch.object(secret_scan, "worktree_files", return_value=[fixture_path]),
            mock.patch.object(Path, "read_bytes", return_value=f"{self.online_password_name}={secret}".encode()),
            contextlib.redirect_stderr(stderr),
        ):
            self.assertEqual(secret_scan.main([]), 1)
        self.assertNotIn(secret, stderr.getvalue())
        self.assertIn("online_credential_assignment", stderr.getvalue())
        self.assertNotIn("fingerprint=", stderr.getvalue())

    def test_cloud_and_bearer_shapes_are_rejected(self) -> None:
        cloud_value = "AKIA" + "A" * 16
        bearer_value = "Bearer " + "a" * 32
        self.assertIn("aws_access_key", [item.rule for item in secret_scan.scan_line(cloud_value)])
        self.assertIn("bearer_token", [item.rule for item in secret_scan.scan_line(bearer_value)])

    def test_legacy_fingerprint_and_safe_report(self) -> None:
        value = "fictional-credential-for-guard-only"
        digest = hashlib.sha256(value.encode()).hexdigest()[:12]
        findings = secret_scan.scan_legacy_text(f"PASSWORD={value}", "PR#7", {digest: "TEST-LC-001"})
        result = secret_scan.legacy_result(
            findings, {"TEST-LC-001"}, 1, 0, {"risk_status": "TEST_ONLY"}
        )
        self.assertEqual(result["blocking_matches"], 1)
        self.assertNotIn(value, json.dumps(result))
        self.assertNotIn("fingerprint", json.dumps(result))

    def test_legacy_placeholders_are_allowed(self) -> None:
        for placeholder in ("<REVOKED_LEGACY_USERNAME>", "<REVOKED_LEGACY_SECRET>"):
            self.assertEqual(secret_scan.scan_legacy_text(f"PASSWORD={placeholder}", "fixture", {}), [])

    def test_legacy_catalog_missing_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            secret_scan.load_legacy_catalog(Path("/definitely/missing/catalog.json"))

    def test_offline_pr_body_input(self) -> None:
        value = "fictional-credential-for-guard-only"
        digest = hashlib.sha256(value.encode()).hexdigest()[:12]
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "prs.jsonl"
            source.write_text(json.dumps({"number": 7, "body": f"password={value}"}) + "\n")
            with (
                mock.patch.object(secret_scan, "worktree_files", return_value=[]),
                mock.patch.object(secret_scan.subprocess, "run") as run,
            ):
                run.side_effect = [mock.Mock(returncode=0), mock.Mock(stdout="")]
                findings, _, count = secret_scan.legacy_inputs({digest: "TEST-LC-001"}, "origin/main", source)
        self.assertIn("--diff-filter=ACMR", run.call_args_list[1].args[0])
        self.assertEqual(count, 1)
        self.assertEqual(findings[0].location, "PR#7")

    def test_missing_bootstrap_base_scans_worktree_without_diff(self) -> None:
        with (
            mock.patch.object(secret_scan, "worktree_files", return_value=[]),
            mock.patch.object(secret_scan.subprocess, "run") as run,
        ):
            run.return_value.returncode = 1
            findings, file_count, pr_count = secret_scan.legacy_inputs({}, "origin/main", None)
        self.assertEqual((findings, file_count, pr_count), ([], 0, 0))
        self.assertEqual(run.call_count, 1)


class _FakeStdin:
    def __init__(self, process: "_FakeBatchProcess") -> None:
        self._process = process

    def write(self, payload: bytes) -> int:
        self._process.answer(payload.decode("utf-8").strip())
        return len(payload)

    def flush(self) -> None:
        return None

    def close(self) -> None:
        return None


class _FakeStdout:
    def __init__(self, process: "_FakeBatchProcess") -> None:
        self._process = process

    def readline(self) -> bytes:
        return self._process.take_line()

    def read(self, size: int) -> bytes:
        return self._process.take(size)

    def close(self) -> None:
        return None


class _FakeBatchProcess:
    """Minimal ``git cat-file --batch`` protocol double, for spawn assertions."""

    def __init__(self, blobs: dict[str, bytes]) -> None:
        self._blobs = blobs
        self._buffer = b""
        self.stdin = _FakeStdin(self)
        self.stdout = _FakeStdout(self)
        self.waited: float | None = None
        self.killed = False
        self.requests: list[str] = []

    def answer(self, object_id: str) -> None:
        self.requests.append(object_id)
        if object_id not in self._blobs:
            self._buffer += f"{object_id} missing\n".encode("utf-8")
            return
        payload = self._blobs[object_id]
        self._buffer += f"{object_id} blob {len(payload)}\n".encode("utf-8") + payload + b"\n"

    def take_line(self) -> bytes:
        index = self._buffer.find(b"\n")
        if index < 0:
            line, self._buffer = self._buffer, b""
            return line
        line, self._buffer = self._buffer[: index + 1], self._buffer[index + 1 :]
        return line

    def take(self, size: int) -> bytes:
        piece, self._buffer = self._buffer[:size], self._buffer[size:]
        return piece

    def wait(self, timeout: float | None = None) -> int:
        self.waited = timeout
        return 0

    def kill(self) -> None:
        self.killed = True


def _fixture_repo(root: Path, files: dict[str, bytes]) -> None:
    environment = {
        **os.environ,
        "GIT_AUTHOR_NAME": "scan-fixture",
        "GIT_AUTHOR_EMAIL": "scan-fixture@example.invalid",
        "GIT_COMMITTER_NAME": "scan-fixture",
        "GIT_COMMITTER_EMAIL": "scan-fixture@example.invalid",
    }
    quiet = {"cwd": root, "check": True, "env": environment, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    subprocess.run(["git", "init", "-q"], **quiet)
    for name, payload in files.items():
        (root / name).write_bytes(payload)
    subprocess.run(["git", "add", "-A"], **quiet)
    subprocess.run(["git", "-c", "commit.gpgsign=false", "commit", "-q", "-m", "fixture"], **quiet)


def _fixture_oid(root: Path, name: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD:" + name],
        check=True, text=True, stdout=subprocess.PIPE,
    ).stdout.strip()


class HistoryScanTest(unittest.TestCase):
    def test_batch_reader_replaces_per_blob_processes(self) -> None:
        first, second = "1" * 40, "2" * 40
        process = _FakeBatchProcess({first: b"ok\n" + b"ghp_" + b"Z" * 36 + b"\n", second: b"bin\0data"})
        paths = {first: ["zeta.md", "alpha.md"], second: ["binary.md"]}
        with (
            mock.patch.dict(os.environ, {parallel_scan.SERIAL_ENV: "1"}),
            mock.patch.object(secret_scan, "history_blob_paths", return_value=paths),
            mock.patch.object(secret_scan.subprocess, "run") as run,
            mock.patch.object(parallel_scan.subprocess, "Popen", return_value=process) as popen,
        ):
            findings = secret_scan.history_findings()
        self.assertEqual(
            findings,
            [f"alpha.md@{first[:12]}:2: github_ghp", f"zeta.md@{first[:12]}:2: github_ghp"],
        )
        self.assertEqual(process.requests, [first, second])
        self.assertEqual(run.call_count, 0)
        self.assertEqual([call.args[0] for call in popen.call_args_list], [["git", "cat-file", "--batch"]])
        self.assertIsNone(secret_scan._HISTORY_READER)

    def test_serial_and_parallel_history_findings_agree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _fixture_repo(
                root,
                {
                    "alpha.md": b"first line\n" + b"ghp_" + b"Z" * 36 + b"\n",
                    # Split the marker so this fixture does not itself contain
                    # a high-confidence secret for the worktree scan to reject.
                    "beta.md": b"safe = 1\n" + b"-----BEGIN " + b"RSA PRIVATE KEY-----\n",
                    "binary.md": b"bin\0data",
                },
            )
            alpha = _fixture_oid(root, "alpha.md")
            beta = _fixture_oid(root, "beta.md")
            binary = _fixture_oid(root, "binary.md")
            paths = {alpha: ["zeta.md", "alpha.md"], beta: ["beta.md"], binary: ["binary.md"]}
            expected = [
                f"alpha.md@{alpha[:12]}:2: github_ghp",
                f"zeta.md@{alpha[:12]}:2: github_ghp",
                f"beta.md@{beta[:12]}:2: private_key",
            ]
            with (
                mock.patch.object(secret_scan, "ROOT", root),
                mock.patch.object(secret_scan, "history_blob_paths", return_value=paths),
                mock.patch.dict(os.environ, {parallel_scan.SERIAL_ENV: "1"}),
            ):
                serial = secret_scan.history_findings()
            with (
                mock.patch.object(secret_scan, "ROOT", root),
                mock.patch.object(secret_scan, "history_blob_paths", return_value=paths),
                mock.patch.dict(os.environ, {parallel_scan.WORKERS_ENV: "3"}),
            ):
                parallel = secret_scan.history_findings()
        self.assertEqual(serial, expected)
        self.assertEqual(parallel, expected)

    def test_missing_history_object_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _fixture_repo(root, {"alpha.md": b"ghp_" + b"Z" * 36 + b"\n"})
            alpha = _fixture_oid(root, "alpha.md")
            paths = {alpha: ["alpha.md"], "0" * 40: ["missing.md"]}
            for mode in ({parallel_scan.SERIAL_ENV: "1"}, {parallel_scan.WORKERS_ENV: "2"}):
                with (
                    self.subTest(mode=mode),
                    mock.patch.dict(os.environ, mode),
                    mock.patch.object(secret_scan, "ROOT", root),
                    mock.patch.object(secret_scan, "history_blob_paths", return_value=paths),
                ):
                    with self.assertRaises(parallel_scan.ObjectReadError):
                        secret_scan.history_findings()



class SyntheticUrlExceptionTests(unittest.TestCase):
    def setUp(self):
        self.relative = "scripts/verify/business_entry_matrix_reuse_identity.test.mjs"
        self.data = (secret_scan.ROOT / self.relative).read_bytes()
        self.finding = secret_scan.Finding("url_embedded_credentials", secret_scan.fingerprint("user:" + "secret"))

    def test_exact_reviewed_fixture_only(self):
        self.assertTrue(secret_scan.is_false_positive(self.relative, self.data, self.finding))

    def test_changed_bytes_are_not_exempt(self):
        self.assertFalse(secret_scan.is_false_positive(self.relative, self.data + b"\n", self.finding))

    def test_worktree_non_utf8_drift_is_not_normalized_into_exception(self):
        for data, expected in ((self.data, 0), (self.data + b"\xff", 1)):
            with self.subTest(expected=expected), mock.patch.object(secret_scan, "worktree_files", return_value=[secret_scan.ROOT / self.relative]), \
                    mock.patch.object(Path, "read_bytes", return_value=data), \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(secret_scan.main([]), expected)

    def test_same_content_different_path_not_exempt(self):
        self.assertFalse(secret_scan.is_false_positive("another-test.mjs", self.data, self.finding))

    def test_other_rule_and_fingerprint_not_exempt(self):
        for finding in (secret_scan.Finding("github_pat", self.finding.fingerprint),
                        secret_scan.Finding(self.finding.rule, "a" * 12)):
            self.assertFalse(secret_scan.is_false_positive(self.relative, self.data, finding))

    def test_registry_rejects_unbounded_and_unexplained_exceptions(self):
        entry = json.loads(secret_scan.FALSE_POSITIVE_FILE.read_text())["entries"][0]
        for patch in ({"path": "scripts/*"}, {"path": "../outside"}, {"path": "/absolute"},
                      {"blob_id": "HEAD"}, {"finding_fingerprint": ""}, {"reason": ""},
                      {"classification": "real_secret"}, {"rule_id": "github_pat"}):
            with self.subTest(patch=patch), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "exceptions.json"
                path.write_text(json.dumps({"schema_version": 1, "entries": [{**entry, **patch}]}))
                with self.assertRaises(ValueError):
                    secret_scan.load_false_positives(path)

    def test_history_uses_actual_blob_bytes_and_exact_path(self):
        reader = mock.Mock()
        reader.read.return_value = self.data
        with mock.patch.object(secret_scan, "_HISTORY_READER", reader):
            self.assertEqual(secret_scan._history_scan_blobs([("86409737bdb355bab1047e961958645c518c3f81", [self.relative])]), [[]])
            self.assertTrue(secret_scan._history_scan_blobs([("86409737bdb355bab1047e961958645c518c3f81", ["another-test.mjs"])])[0])


if __name__ == "__main__":
    unittest.main()
