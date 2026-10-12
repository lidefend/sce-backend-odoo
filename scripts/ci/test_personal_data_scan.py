#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import tempfile
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import parallel_scan
import personal_data_scan


class PersonalDataScanTests(unittest.TestCase):
    def test_rules_report_metadata_without_values(self) -> None:
        samples = (
            ("PD001", "110105" + "19491231" + "002X"),
            ("PD002", "139" + "1234" + "5678"),
            ("PD003", "bank_account=" + "622202" + "1234567890123"),
        )
        for expected_rule, value in samples:
            findings = personal_data_scan.scan_text(value, "fixture.txt", "a" * 40)
            self.assertIn(expected_rule, [item.rule_id for item in findings])
            self.assertNotIn(value, repr(findings))

    def test_clean_placeholders_pass(self) -> None:
        text = "id=DEMO-ID-001 phone=DEMO-PHONE-001 bank_account=DEMO-ACCOUNT-001"
        self.assertEqual(personal_data_scan.scan_text(text, "fixture.txt", "b" * 40), [])

    def test_hash_embedded_phone_shaped_digits_pass(self) -> None:
        text = (
            "candidate_ref=abcdef01234a"
            + "139"
            + "1234"
            + "5678"
            + "babcdef012345"
        )
        self.assertEqual(personal_data_scan.scan_text(text, "fixture.txt", "d" * 40), [])

    def test_main_never_prints_match_values(self) -> None:
        sensitive = "139" + "1234" + "5678"
        finding = personal_data_scan.scan_text(sensitive, "fixture.txt", "c" * 40)[0]
        stderr = io.StringIO()
        with (
            mock.patch.object(personal_data_scan, "worktree_findings", return_value=[finding]),
            mock.patch.object(personal_data_scan, "history_findings", return_value=[]),
            contextlib.redirect_stderr(stderr),
        ):
            self.assertEqual(personal_data_scan.main(["--scope", "all"]), 1)
        self.assertNotIn(sensitive, stderr.getvalue())
        self.assertIn("rule=PD002", stderr.getvalue())

    def test_exact_false_positive_suppresses_only_matching_blob_and_path(self) -> None:
        finding = personal_data_scan.Finding(
            "PD002", "demo.py", "a" * 40, "MOBILE_PHONE_PATTERN"
        )
        registry = {
            "schema_version": 1,
            "entries": [
                {
                    "rule_id": "PD002",
                    "path": "demo.py",
                    "blob_id": "a" * 40,
                    "classification": "MOBILE_PHONE_PATTERN",
                    "reason": "verified_synthetic_fixture",
                }
            ],
        }
        with self.subTest("exact match"), tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "registry.json"
            path.write_text(json.dumps(registry), encoding="utf-8")
            with mock.patch.object(personal_data_scan, "FALSE_POSITIVE_FILE", path):
                allowed = personal_data_scan.load_false_positives()
            self.assertIn((finding.rule_id, finding.path, finding.blob_id, finding.classification), allowed)
            self.assertNotIn((finding.rule_id, "other.py", finding.blob_id, finding.classification), allowed)
            self.assertNotIn((finding.rule_id, finding.path, "b" * 40, finding.classification), allowed)

    def test_false_positive_registry_rejects_short_blob_identity(self) -> None:
        registry = {
            "schema_version": 1,
            "entries": [{
                "rule_id": "PD002",
                "path": "demo.py",
                "blob_id": "a" * 12,
                "classification": "MOBILE_PHONE_PATTERN",
                "reason": "too_broad",
            }],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "registry.json"
            path.write_text(json.dumps(registry), encoding="utf-8")
            with (
                mock.patch.object(personal_data_scan, "FALSE_POSITIVE_FILE", path),
                self.assertRaisesRegex(ValueError, "full SHA-1"),
            ):
                personal_data_scan.load_false_positives()


class PersonalDataHistoryScanTests(unittest.TestCase):
    """The history pass reads blobs in one batch stream, serial or parallel."""

    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name)
        self._git("init", "-q")
        self._git("config", "user.email", "scan@example.invalid")
        self._git("config", "user.name", "scan")
        self._write("notes.txt", "contact " + "139" + "1234" + "5678" + "\n")
        self._write("dup-a.txt", "shared " + "139" + "1234" + "5678" + "\n")
        self._write("dup-b.txt", "shared " + "139" + "1234" + "5678" + "\n")
        self._write("clean.txt", "nothing sensitive here\n")
        self._write("payload.bin", "ignored by suffix " + "139" + "1234" + "5678" + "\n")
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "fixture")

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def _git(self, *args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=self.root, check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        ).stdout

    def _write(self, name: str, text: str) -> None:
        (self.root / name).write_text(text, encoding="utf-8")

    def _history_entries(self) -> list[tuple[str, str, int]]:
        entries = []
        for line in self._git("ls-tree", "-r", "HEAD").splitlines():
            meta, path = line.split("\t")
            entries.append((meta.split()[2], path, len((self.root / path).read_bytes())))
        return sorted(set(entries))

    def _scan(
        self, entries: list[tuple[str, str, int]], env: dict[str, str]
    ) -> list[personal_data_scan.Finding]:
        with (
            mock.patch.object(personal_data_scan, "ROOT", self.root),
            mock.patch.object(personal_data_scan, "history_objects", return_value=entries),
            mock.patch.dict(os.environ, env),
        ):
            return personal_data_scan.history_findings()

    def test_history_scan_reads_every_blob_from_one_batch_process(self) -> None:
        entries = self._history_entries()
        self.assertGreater(len({oid for oid, _, _ in entries}), 1)
        with (
            mock.patch.object(personal_data_scan, "ROOT", self.root),
            mock.patch.object(personal_data_scan, "history_objects", return_value=entries),
            mock.patch.dict(os.environ, {parallel_scan.SERIAL_ENV: "1"}),
            mock.patch.object(subprocess, "Popen", wraps=subprocess.Popen) as popen,
        ):
            findings = personal_data_scan.history_findings()
        self.assertTrue(findings)
        self.assertEqual(popen.call_count, 1)
        self.assertEqual(popen.call_args.args[0], ["git", "cat-file", "--batch"])
        per_blob_spawns = [
            call.args[0]
            for call in popen.call_args_list
            if call.args[0][:3] == ["git", "cat-file", "blob"]
        ]
        self.assertEqual(per_blob_spawns, [])

    def test_serial_and_parallel_history_findings_are_identical(self) -> None:
        entries = self._history_entries()
        oversized = [(self._history_entries()[0][0], "huge.txt",
                      personal_data_scan.MAX_TEXT_BLOB_BYTES + 1)]
        serial = self._scan(entries + oversized, {parallel_scan.SERIAL_ENV: "1"})
        parallel = self._scan(entries + oversized, {parallel_scan.WORKERS_ENV: "4"})
        self.assertTrue(serial)
        self.assertEqual(serial, parallel)
        # The size/path filter keeps only text paths; the reused blob expands to
        # both sorted occurrences and the oversized occurrence is never scanned.
        self.assertEqual({item.path for item in serial},
                         {"notes.txt", "dup-a.txt", "dup-b.txt"})
        self.assertNotIn("payload.bin", {item.path for item in serial})
        self.assertNotIn("huge.txt", {item.path for item in serial})

    def test_missing_history_object_fails_closed(self) -> None:
        entries = [("f" * 40, "missing.txt", 12)]
        with self.assertRaises(parallel_scan.ObjectReadError):
            self._scan(entries, {parallel_scan.SERIAL_ENV: "1"})


if __name__ == "__main__":
    unittest.main()
