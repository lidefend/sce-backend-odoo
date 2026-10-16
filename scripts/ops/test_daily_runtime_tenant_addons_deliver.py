#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import io
import json
import os
import re
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("daily_runtime_tenant_addons_deliver.py")
SPEC = importlib.util.spec_from_file_location("daily_runtime_tenant_addons_deliver", SCRIPT)
assert SPEC and SPEC.loader
deliver = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(deliver)

SHA = "a" * 40
OTHER_SHA = "b" * 40
DIGEST = "c" * 64
CONFIRM = {deliver.CONFIRM_ENV: deliver.CONFIRMATION}


def build_repository(root: Path, modules: dict[str, str]) -> str:
    """One throwaway repository whose addons tree is known by construction."""
    def git(*arguments: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(root), *arguments],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False,
            env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
                 "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"},
        )
        if result.returncode:
            raise AssertionError(result.stderr)
        return result.stdout.strip()

    git("init", "-q")
    for name, body in modules.items():
        target = root / "addons" / name
        target.mkdir(parents=True, exist_ok=True)
        (target / "__manifest__.py").write_text(body, encoding="utf-8")
        (target / "models.py").write_text("x = 1\n", encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "fixture")
    return git("rev-parse", "HEAD")


def delivery(**overrides: object) -> dict:
    payload = {
        "mode": "report",
        "path": deliver.REMOTE_ROOT + "/" + SHA,
        "exists": True,
        "tenant_sha": SHA,
        "digest": DIGEST,
        "files": 4,
        "modules": ["sce_customer_sample"],
        "missing_modules": [],
        "writable_paths": [],
        "error": "",
    }
    payload.update(overrides)
    return payload


def payload_of(**overrides: object) -> dict:
    value = {
        "mode": "apply",
        "tenant_sha": SHA,
        "expected_digest": DIGEST,
        "expected_files": 4,
        "modules": ["sce_customer_sample"],
        "require_modules": ["sce_customer_sample"],
    }
    value.update(overrides)
    return value


def verdict(source: dict, observed: dict, payload: dict) -> dict[str, bool]:
    return {row["id"]: row["passed"] for row in deliver.assertions(source, observed, payload)}


class SourceFactsTest(unittest.TestCase):
    def test_rejects_a_short_identity_before_touching_git(self) -> None:
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            build_repository(root, {"m": "{}\n"})
            with self.assertRaises(deliver.DeliverError):
                deliver.source_facts(root, "abc")

    def test_rejects_a_commit_the_repository_does_not_carry(self) -> None:
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            build_repository(root, {"m": "{}\n"})
            with self.assertRaises(deliver.DeliverError):
                deliver.source_facts(root, SHA)

    def test_reports_a_clean_worktree_as_one_exact_commit(self) -> None:
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            head = build_repository(root, {"m": "{}\n"})
            facts = deliver.source_facts(root, head)
            self.assertEqual(facts["tenant_sha"], head)
            self.assertEqual(facts["head"], head)
            self.assertTrue(facts["clean"])


class ArchiveTest(unittest.TestCase):
    def test_the_archive_is_the_module_set_it_carries(self) -> None:
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            head = build_repository(root, {"alpha": "{}\n", "beta": "{}\n"})
            archive = deliver.archive_bytes(root, head)
            self.assertEqual(deliver.archive_modules(archive), ["alpha", "beta"])

    def test_digest_ignores_bytecode_and_the_delivery_marker(self) -> None:
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            head = build_repository(root, {"alpha": "{}\n"})
            archive = deliver.archive_bytes(root, head)
            baseline = deliver.local_tree_digest(archive)

            with tarfile.open(fileobj=io.BytesIO(archive)) as handle:
                members = {member.name: handle.extractfile(member).read()
                           for member in handle.getmembers() if member.isfile()}
            self.assertIn("addons/alpha/__manifest__.py", members)

            distinct = deliver.local_tree_digest(archive)
            self.assertEqual(baseline, distinct)

            with tempfile.TemporaryDirectory() as tree:
                handle = Path(tree)
                with tarfile.open(fileobj=io.BytesIO(archive)) as source:
                    source.extractall(handle / "extracted", filter="data")
                extracted = handle / "extracted" / "addons"
                (extracted / "alpha" / "__pycache__").mkdir()
                (extracted / "alpha" / "__pycache__" / "x.pyc").write_bytes(b"noise")
                (extracted / "TENANT_SHA").write_text(SHA)
                observed = deliver.tree_digest(extracted)
                self.assertEqual(observed["digest"], baseline["digest"])
                self.assertEqual(observed["files"], baseline["files"])

    def test_a_changed_byte_changes_the_digest(self) -> None:
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            head = build_repository(root, {"alpha": "{}\n"})
            before = deliver.local_tree_digest(deliver.archive_bytes(root, head))
            (root / "addons" / "alpha" / "models.py").write_text("x = 2\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "-A"], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", "second"], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
                                "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"})
            after = deliver.local_tree_digest(deliver.archive_bytes(root, "HEAD"))
            self.assertNotEqual(before["digest"], after["digest"])
            self.assertEqual(before["files"], after["files"])


class RemoteProgramTest(unittest.TestCase):
    def rendered(self) -> str:
        return deliver.render_remote_program(payload_of())

    def test_the_remote_measurement_is_the_local_implementation(self) -> None:
        program = self.rendered()
        self.assertIn(deliver.TREE_DIGEST_SOURCE, program)
        self.assertNotIn("__TREE_DIGEST_SOURCE__", program)
        self.assertNotIn("__PAYLOAD_JSON__", program)
        self.assertIn(repr(deliver.REMOTE_ROOT), program)

        with tempfile.TemporaryDirectory() as tree:
            handle = Path(tree)
            (handle / "m").mkdir()
            (handle / "m" / "__manifest__.py").write_text("{}\n", encoding="utf-8")
            shared: dict[str, object] = {}
            exec(deliver.TREE_DIGEST_SOURCE, shared)  # noqa: S102 - the rendered copy
            self.assertEqual(shared["tree_digest"](handle), deliver.tree_digest(handle))

    def test_the_remote_program_reads_its_mode_from_the_payload(self) -> None:
        self.assertIn('MODE = PAYLOAD["mode"]', self.rendered())
        self.assertNotIn("sys.argv", self.rendered())


class VerdictTest(unittest.TestCase):
    def setUp(self) -> None:
        self.source = {"tenant_sha": SHA, "head": SHA, "clean": True}
        self.payload = payload_of()

    def test_a_matching_delivery_passes_every_assertion(self) -> None:
        self.assertEqual(set(verdict(self.source, delivery(), self.payload).values()), {True})

    def test_content_drift_fails_closed(self) -> None:
        rows = verdict(self.source, delivery(digest="d" * 64), self.payload)
        self.assertFalse(rows["delivered_tree_matches_the_reviewed_archive"])

    def test_an_absent_destination_fails_closed(self) -> None:
        rows = verdict(self.source, delivery(exists=False, digest="", tenant_sha=""), self.payload)
        self.assertFalse(rows["delivered_tree_matches_the_reviewed_archive"])
        self.assertFalse(rows["destination_carries_the_reviewed_commit_marker"])

    def test_another_commit_marker_fails_closed(self) -> None:
        rows = verdict(self.source, delivery(tenant_sha=OTHER_SHA), self.payload)
        self.assertFalse(rows["destination_carries_the_reviewed_commit_marker"])

    def test_a_missing_required_module_fails_closed(self) -> None:
        rows = verdict(self.source, delivery(missing_modules=["sce_customer_sample"]), self.payload)
        self.assertFalse(rows["every_required_module_is_present_in_the_destination"])

    def test_an_extra_delivered_module_fails_closed(self) -> None:
        rows = verdict(self.source, delivery(modules=["sce_customer_sample", "smuggled"]), self.payload)
        self.assertFalse(rows["delivered_module_set_is_exactly_the_archived_one"])

    def test_a_writable_destination_fails_closed(self) -> None:
        rows = verdict(self.source, delivery(writable_paths=["m/__manifest__.py"]), self.payload)
        self.assertFalse(rows["destination_is_read_only"])


class CommandTest(unittest.TestCase):
    def test_a_report_touches_only_the_read_only_remote_call(self) -> None:
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            head = build_repository(root, {"sce_customer_sample": "{}\n"})
            report = root / "report.json"
            calls: list[list[str]] = []

            def fake_run(command, *, input_bytes=None, cwd=None):
                calls.append(list(command))
                return subprocess.CompletedProcess(command, 0, b"", b"")

            archive = deliver.archive_bytes(root, head)
            remote = deliver.MARKER + json.dumps(delivery(
                tenant_sha=head,
                digest=deliver.local_tree_digest(archive)["digest"],
                modules=["sce_customer_sample"],
            ))
            with mock.patch.object(deliver, "ssh", side_effect=lambda host, text, input_bytes=None: (
                calls.append([text]),
                subprocess.CompletedProcess([], 0, remote.encode(), b""),
            )[1]):
                code = deliver.main([
                    "--ssh-host", "sc-root", "--customer-repository", str(root),
                    "--tenant-sha", head, "--require-module", "sce_customer_sample",
                    "--report", str(report),
                ])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(report.read_text())["status"], "PASS")
            self.assertTrue(any(call[0].startswith("cat > ") for call in calls if isinstance(call[0], str)))
            self.assertTrue(any(call[0].startswith("rm -f ") for call in calls if isinstance(call[0], str)))

    def test_an_apply_without_the_confirmation_stops_before_the_host(self) -> None:
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            head = build_repository(root, {"sce_customer_sample": "{}\n"})
            with mock.patch.object(deliver, "ssh", side_effect=AssertionError("the host was contacted")), \
                 mock.patch.dict(os.environ, {deliver.CONFIRM_ENV: ""}, clear=False):
                code = deliver.main([
                    "--ssh-host", "sc-root", "--customer-repository", str(root),
                    "--tenant-sha", head, "--require-module", "sce_customer_sample",
                    "--apply", "--report", str(root / "r.json"),
                ])
            self.assertEqual(code, 2)

    def test_an_apply_from_a_dirty_worktree_stops_before_the_host(self) -> None:
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            head = build_repository(root, {"sce_customer_sample": "{}\n"})
            (root / "addons" / "sce_customer_sample" / "models.py").write_text("y = 1\n")
            with mock.patch.object(deliver, "ssh", side_effect=AssertionError("the host was contacted")), \
                 mock.patch.dict(os.environ, CONFIRM, clear=False):
                code = deliver.main([
                    "--ssh-host", "sc-root", "--customer-repository", str(root),
                    "--tenant-sha", head, "--require-module", "sce_customer_sample",
                    "--apply", "--report", str(root / "r.json"),
                ])
            self.assertEqual(code, 2)

    def test_a_required_module_absent_from_the_commit_stops_before_the_host(self) -> None:
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            head = build_repository(root, {"other_module": "{}\n"})
            with mock.patch.object(deliver, "ssh", side_effect=AssertionError("the host was contacted")), \
                 mock.patch.dict(os.environ, CONFIRM, clear=False):
                code = deliver.main([
                    "--ssh-host", "sc-root", "--customer-repository", str(root),
                    "--tenant-sha", head, "--require-module", "sce_customer_sample",
                    "--apply", "--report", str(root / "r.json"),
                ])
            self.assertEqual(code, 2)

    def test_the_entry_never_defaults_a_customer_module(self) -> None:
        """The tree ships to every customer, so it may not name one of them.

        A caller that names no module would otherwise get whatever module the
        entry happened to hard-code, which is how one customer's identity ends
        up delivered to all of them.
        """
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            head = build_repository(root, {"sce_customer_sample": "{}\n"})
            with mock.patch.object(
                deliver, "ssh", side_effect=AssertionError("the host was contacted")
            ), mock.patch.dict(os.environ, CONFIRM, clear=False):
                code = deliver.main([
                    "--ssh-host", "sc-root", "--customer-repository", str(root),
                    "--tenant-sha", head, "--apply", "--report", str(root / "r.json"),
                ])
            self.assertEqual(code, 2)

    def test_the_confirmation_is_read_from_the_environment(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("CONFIRM_ENV", source)
        self.assertIn("DAILY_TENANT_ADDONS_CONFIRMATION_REQUIRED", source)
        self.assertNotIn("input(", source)

    def test_the_remote_root_is_the_registered_daily_namespace(self) -> None:
        self.assertEqual(deliver.REMOTE_ROOT, "/opt/sce/tenant-addons/daily")
        self.assertNotRegex(deliver.REMOTE_ROOT, re.compile(r"acceptance|production"))


if __name__ == "__main__":
    unittest.main()
