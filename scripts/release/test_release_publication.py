#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from jsonschema import Draft202012Validator, ValidationError


REPO = Path(__file__).resolve().parents[2]


def load_module():
    path = REPO / "scripts" / "release" / "release_publication.py"
    spec = importlib.util.spec_from_file_location("release_publication_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


publication = load_module()

VERSION = (REPO / "VERSION").read_text(encoding="utf-8").strip()
SOURCE = "a" * 40
TREE = "b" * 40
LIVE_MAIN = "1" * 40
LIVE_TREE = "2" * 40
CANDIDATE_ATTEMPT = "20260724T120000Z-" + "1" * 32
IMAGE_ID = "sha256:" + "c" * 64
REMOTE_DIGEST = "sha256:" + "d" * 64
CHECK_HEAD = "e" * 40
TOOL_CONTRACT = "f" * 64


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_fixture(root: Path, *, ready: bool = True) -> Path:
    for relative in (
        "make/release.mk",
        "scripts/release/release_publication.py",
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(relative + "\n", encoding="utf-8")
    schema_root = root / "schemas" / "release"
    schema_root.mkdir(parents=True)
    for name in (
        "release_publication_report.v1.schema.json",
        "release_publication_plan.v1.schema.json",
    ):
        (schema_root / name).write_bytes(
            (REPO / "schemas" / "release" / name).read_bytes()
        )

    attempt = (
        root
        / "artifacts"
        / "release"
        / "candidates"
        / VERSION
        / "attempts"
        / CANDIDATE_ATTEMPT
    )
    attempt.mkdir(parents=True)
    artifacts = {
        "candidate-image.tar": b"immutable archive",
        "sbom.cyclonedx.json": b'{"bomFormat":"CycloneDX"}\n',
        "candidate-contract.sha256": (TOOL_CONTRACT + "\n").encode(),
    }
    for name, value in artifacts.items():
        (attempt / name).write_bytes(value)
    manifest = {
        "schema_version": 2,
        "source_sha": SOURCE,
        "source_tree_sha": TREE,
        "product_version": VERSION,
        "publish_status": "not_published",
        "image_digest": None,
        "registry_repository": publication.REGISTRY_REPOSITORY,
        "image_tags": [
            f"{publication.REGISTRY_REPOSITORY}:{VERSION}",
            f"{publication.REGISTRY_REPOSITORY}:sha-{SOURCE[:12]}",
        ],
        "local_image_id": IMAGE_ID,
    }
    (attempt / "image-manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    hashes = {
        name: sha(attempt / name)
        for name in (
            "candidate-image.tar",
            "sbom.cyclonedx.json",
            "candidate-contract.sha256",
            "image-manifest.json",
        )
    }
    report = {
        "schema_version": "release_candidate_report.v1",
        "attempt_id": CANDIDATE_ATTEMPT,
        "attempt_number": 1,
        "status": "ready" if ready else "failed",
        "CANDIDATE_READY": ready,
        "source": {
            "commit_sha": SOURCE,
            "tree_sha": TREE,
            "product_version": VERSION,
            "pipeline_contract_sha256": TOOL_CONTRACT,
            "remote_main": {"github": SOURCE, "gitee": SOURCE},
            "required_checks": {
                name: "success" for name in publication.REQUIRED_CHECKS
            },
            "required_checks_head_sha": CHECK_HEAD,
        },
        "image": {
            "tags": manifest["image_tags"],
            "local_image_id": IMAGE_ID,
            "publish_status": "not_published",
        },
        "artifacts": {"directory": str(attempt), "sha256": hashes},
        "external_effects": {
            "registry_push": False,
            "git_tag": False,
            "release_publication": False,
            "deployment": False,
        },
    }
    (attempt / "release-report.json").write_text(
        json.dumps(report), encoding="utf-8"
    )
    return attempt


class FakeBackend:
    def __init__(self):
        self.registry: dict[str, str] = {}
        self.tags = {"origin": None, "gitee-mirror": None}
        self.release_payload: dict | None = None
        self.events: list[str] = []
        self.github_main = LIVE_MAIN
        self.gitee_main = LIVE_MAIN
        self.tree = LIVE_TREE
        self.tool_sha = LIVE_MAIN
        self.tool_tree = LIVE_TREE
        self.candidate_reachable = True
        self.checks = {name: "success" for name in publication.REQUIRED_CHECKS}
        self.fail_registry_once = False
        self.fail_registry_partial_once = False
        self.fail_tag_once = False
        self.fail_release_once = False
        self.credentials_ready = True
        self.move_main_after_registry = False
        self.move_main_before_first_write = False

    def remote_main(self, remote):
        return (
            self.github_main if remote == "origin" else self.gitee_main,
            self.tree,
        )

    def publication_tool_identity(self):
        return self.tool_sha, self.tool_tree

    def candidate_is_first_parent_ancestor(self, candidate_source_sha, live_main_sha):
        return (
            self.candidate_reachable
            and candidate_source_sha == SOURCE
            and live_main_sha == self.github_main
        )

    def required_checks(self, head_sha):
        self.events.append("preflight_checks")
        return dict(self.checks)

    def local_image_id(self, reference):
        if self.move_main_before_first_write:
            self.move_main_before_first_write = False
            self.github_main = "8" * 40
        return IMAGE_ID

    def registry_credentials_ready(self):
        return self.credentials_ready

    def registry_digest(self, reference):
        return self.registry.get(reference)

    def push_registry(self, references):
        self.events.append("registry_push")
        if self.fail_registry_partial_once:
            self.fail_registry_partial_once = False
            self.registry[references[0]] = REMOTE_DIGEST
            raise publication.PublicationError(
                "injected partial registry failure", stage="registry_push"
            )
        for reference in references:
            self.registry[reference] = REMOTE_DIGEST
        if self.move_main_after_registry:
            self.github_main = "9" * 40
        if self.fail_registry_once:
            self.fail_registry_once = False
            raise publication.PublicationError(
                "injected registry failure", stage="registry_push"
            )
        return REMOTE_DIGEST

    def verify_registry_content(self, repository, digest, expected_local_image_id):
        return digest == REMOTE_DIGEST and expected_local_image_id == IMAGE_ID

    def tag_commit(self, remote, tag):
        return self.tags[remote]

    def ensure_tags(self, tag, source_sha, message, created_at):
        self.events.append("tag_create")
        self.tags["origin"] = source_sha
        if self.fail_tag_once:
            self.fail_tag_once = False
            raise publication.PublicationError(
                "injected tag failure", stage="tag_create"
            )
        self.tags["gitee-mirror"] = source_sha
        return {"github": source_sha, "gitee": source_sha}

    def release(self, tag):
        return self.release_payload

    def create_release(self, tag, title, notes_path):
        self.events.append("release_create")
        self.release_payload = {
            "tagName": tag,
            "isDraft": False,
            "isPrerelease": True,
            "url": "https://example.invalid/release",
            "targetCommitish": SOURCE,
            "body": notes_path.read_text(encoding="utf-8"),
        }
        if self.fail_release_once:
            self.fail_release_once = False
            raise publication.PublicationError(
                "injected release failure", stage="release_create"
            )
        return dict(self.release_payload)


class PublicationContractTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.candidate = write_fixture(self.root)
        self.backend = FakeBackend()

    def tearDown(self):
        self.temporary.cleanup()

    def pipeline(self, **overrides):
        values = {
            "version": VERSION,
            "candidate_attempt_id": CANDIDATE_ATTEMPT,
            "expected_source_sha": SOURCE,
            "expected_publication_tool_sha": LIVE_MAIN,
            "expected_live_main_sha": LIVE_MAIN,
            "backend": self.backend,
            "root": self.root,
        }
        values.update(overrides)
        return publication.Publication(**values)

    def candidate_snapshot(self):
        return {
            path.relative_to(self.candidate).as_posix(): (
                sha(path),
                path.stat().st_size,
                path.stat().st_mtime_ns,
            )
            for path in self.candidate.iterdir()
            if path.is_file()
        }

    def latest_report(self):
        latest = json.loads(
            (
                self.root
                / "artifacts"
                / "release"
                / "candidates"
                / VERSION
                / "publications"
                / "latest.json"
            ).read_text()
        )
        report = (
            self.root
            / "artifacts"
            / "release"
            / "candidates"
            / VERSION
            / "publications"
            / latest["publication_attempt_id"]
            / "publication-report.json"
        )
        return latest, json.loads(report.read_text()), report

    def test_complete_publication_is_separate_and_candidate_is_immutable(self):
        before = self.candidate_snapshot()
        result = self.pipeline().execute()
        self.assertEqual(result["state"], "PUBLICATION_COMPLETE")
        self.assertTrue(result["PUBLICATION_COMPLETE"])
        self.assertEqual(before, self.candidate_snapshot())
        self.assertEqual(
            self.backend.events,
            ["preflight_checks", "registry_push", "tag_create", "release_create"],
        )
        latest, report, report_path = self.latest_report()
        self.assertEqual(latest["state"], "PUBLICATION_COMPLETE")
        self.assertNotEqual(report_path.parent, self.candidate)
        self.assertEqual(
            report["external"]["registry"]["digest"], REMOTE_DIGEST
        )
        self.assertEqual(report["external"]["tags"]["github"], SOURCE)
        self.assertEqual(report["external"]["tags"]["gitee"], SOURCE)
        self.assertEqual(report["external"]["release"]["tag"], f"v{VERSION}")
        identity = report["identity"]
        self.assertEqual(identity["candidate_source_sha"], SOURCE)
        self.assertEqual(identity["candidate_source_tree"], TREE)
        self.assertEqual(identity["publication_tool_source_sha"], LIVE_MAIN)
        self.assertEqual(identity["live_github_main_sha"], LIVE_MAIN)
        self.assertEqual(identity["live_gitee_main_sha"], LIVE_MAIN)
        self.assertTrue(identity["candidate_reachable_from_live_main"])
        self.assertEqual(
            identity["candidate_required_checks_evidence"],
            {name: "success" for name in publication.REQUIRED_CHECKS},
        )
        manifest_path = report_path.parent / "publication-manifest.json"
        self.assertEqual(
            report["publication_manifest"]["sha256"], sha(manifest_path)
        )
        release_body = self.backend.release_payload["body"]
        self.assertNotIn(str(self.root), release_body)
        self.assertIn(result["publication_attempt_id"], release_body)
        self.assertIn(SOURCE, release_body)
        self.assertIn(LIVE_MAIN, release_body)

    def test_candidate_source_may_equal_or_precede_live_main(self):
        advanced = self.pipeline().execute()
        self.assertEqual(
            advanced["identity"]["candidate_source_sha"], SOURCE
        )
        self.assertEqual(
            advanced["identity"]["expected_live_main_sha"], LIVE_MAIN
        )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_fixture(root)
            backend = FakeBackend()
            backend.github_main = SOURCE
            backend.gitee_main = SOURCE
            backend.tree = TREE
            backend.tool_sha = SOURCE
            backend.tool_tree = TREE
            same = publication.Publication(
                version=VERSION,
                candidate_attempt_id=CANDIDATE_ATTEMPT,
                expected_source_sha=SOURCE,
                expected_publication_tool_sha=SOURCE,
                expected_live_main_sha=SOURCE,
                backend=backend,
                root=root,
            ).execute()
            self.assertEqual(same["state"], "PUBLICATION_COMPLETE")

    def test_candidate_creation_identity_and_check_evidence_are_required(self):
        for mutation in ("remote", "checks", "checks_head", "tree"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                attempt = write_fixture(root)
                report_path = attempt / "release-report.json"
                report = json.loads(report_path.read_text())
                if mutation == "remote":
                    report["source"]["remote_main"]["gitee"] = "9" * 40
                elif mutation == "checks":
                    report["source"]["required_checks"]["public_guard"] = "failure"
                elif mutation == "checks_head":
                    report["source"]["required_checks_head_sha"] = ""
                else:
                    report["source"]["tree_sha"] = "9" * 40
                report_path.write_text(json.dumps(report))
                backend = FakeBackend()
                pipe = publication.Publication(
                    version=VERSION,
                    candidate_attempt_id=CANDIDATE_ATTEMPT,
                    expected_source_sha=SOURCE,
                    expected_publication_tool_sha=LIVE_MAIN,
                    expected_live_main_sha=LIVE_MAIN,
                    backend=backend,
                    root=root,
                )
                with self.assertRaises(publication.PublicationError):
                    pipe.execute()
                self.assertFalse(
                    {"registry_push", "tag_create", "release_create"}
                    & set(backend.events)
                )

    def test_live_main_drift_after_preflight_blocks_before_first_write(self):
        self.backend.move_main_before_first_write = True
        with self.assertRaises(publication.PublicationError):
            self.pipeline().execute()
        self.assertNotIn("registry_push", self.backend.events)
        self.assertNotIn("tag_create", self.backend.events)
        self.assertNotIn("release_create", self.backend.events)

    def test_all_preflight_finishes_before_first_external_write(self):
        self.backend.registry[f"{publication.REGISTRY_REPOSITORY}:{VERSION}"] = (
            REMOTE_DIGEST
        )
        with self.assertRaises(publication.PublicationError):
            self.pipeline().execute()
        self.assertNotIn("registry_push", self.backend.events)
        self.assertNotIn("tag_create", self.backend.events)
        self.assertNotIn("release_create", self.backend.events)
        _, report, _ = self.latest_report()
        self.assertEqual(report["state"], "FAILED_PREFLIGHT")

    def test_candidate_not_ready_and_hash_mismatch_fail_before_writes(self):
        report_path = self.candidate / "release-report.json"
        payload = json.loads(report_path.read_text())
        payload["CANDIDATE_READY"] = False
        payload["status"] = "failed"
        report_path.write_text(json.dumps(payload))
        with self.assertRaises(publication.PublicationError):
            self.pipeline().execute()
        self.assertEqual(self.backend.events, [])

        payload["CANDIDATE_READY"] = True
        payload["status"] = "ready"
        report_path.write_text(json.dumps(payload))
        (self.candidate / "sbom.cyclonedx.json").write_text("changed")
        with self.assertRaises(publication.PublicationError):
            self.pipeline().execute()
        self.assertEqual(self.backend.events, [])

    def test_source_tree_remote_and_check_mismatch_fail_closed(self):
        cases = (
            "source",
            "live_tree",
            "remote",
            "checks",
            "tool_sha",
            "tool_tree",
            "ancestry",
        )
        for case in cases:
            with self.subTest(case=case):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    attempt = write_fixture(root)
                    backend = FakeBackend()
                    if case == "source":
                        kwargs = {"expected_source_sha": "9" * 40}
                    else:
                        kwargs = {}
                    if case == "live_tree":
                        backend.tree = "8" * 40
                    if case == "remote":
                        backend.gitee_main = "7" * 40
                    if case == "checks":
                        backend.checks["public_guard"] = "failure"
                    if case == "tool_sha":
                        backend.tool_sha = "6" * 40
                    if case == "tool_tree":
                        backend.tool_tree = "5" * 40
                    if case == "ancestry":
                        backend.candidate_reachable = False
                    pipe = publication.Publication(
                        version=VERSION,
                        candidate_attempt_id=CANDIDATE_ATTEMPT,
                        expected_source_sha=kwargs.get("expected_source_sha", SOURCE),
                        expected_publication_tool_sha=LIVE_MAIN,
                        expected_live_main_sha=LIVE_MAIN,
                        backend=backend,
                        root=root,
                    )
                    with self.assertRaises(publication.PublicationError):
                        pipe.execute()
                    self.assertFalse(
                        {"registry_push", "tag_create", "release_create"}
                        & set(backend.events)
                    )
                    self.assertTrue(attempt.exists())

    def test_registry_credentials_and_post_push_main_drift_fail_closed(self):
        self.backend.credentials_ready = False
        with self.assertRaises(publication.PublicationError):
            self.pipeline().execute()
        self.assertNotIn("registry_push", self.backend.events)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_fixture(root)
            backend = FakeBackend()
            backend.move_main_after_registry = True
            pipe = publication.Publication(
                version=VERSION,
                candidate_attempt_id=CANDIDATE_ATTEMPT,
                expected_source_sha=SOURCE,
                expected_publication_tool_sha=LIVE_MAIN,
                expected_live_main_sha=LIVE_MAIN,
                backend=backend,
                root=root,
            )
            with self.assertRaises(publication.PublicationError):
                pipe.execute()
            self.assertIn("registry_push", backend.events)
            self.assertNotIn("tag_create", backend.events)
            report = json.loads(pipe.report_path.read_text())
            self.assertEqual(report["state"], "FAILED_TAG_CREATE")

    def test_registry_failure_resumes_without_second_push(self):
        self.backend.fail_registry_once = True
        pipe = self.pipeline()
        with self.assertRaises(publication.PublicationError):
            pipe.execute()
        attempt_id = pipe.attempt_dir.name
        self.assertEqual(self.backend.events.count("registry_push"), 1)
        result = self.pipeline(
            requested_publication_attempt_id=attempt_id
        ).execute()
        self.assertEqual(result["state"], "PUBLICATION_COMPLETE")
        self.assertEqual(self.backend.events.count("registry_push"), 1)

    def test_partial_registry_push_resumes_only_missing_tag(self):
        self.backend.fail_registry_partial_once = True
        pipe = self.pipeline()
        with self.assertRaises(publication.PublicationError):
            pipe.execute()
        self.assertEqual(len(self.backend.registry), 1)
        result = self.pipeline(
            requested_publication_attempt_id=pipe.attempt_dir.name
        ).execute()
        self.assertEqual(result["state"], "PUBLICATION_COMPLETE")
        self.assertEqual(len(self.backend.registry), 2)
        self.assertEqual(set(self.backend.registry.values()), {REMOTE_DIGEST})

    def test_tag_failure_resumes_and_verifies_partial_tag(self):
        self.backend.fail_tag_once = True
        pipe = self.pipeline()
        with self.assertRaises(publication.PublicationError):
            pipe.execute()
        attempt_id = pipe.attempt_dir.name
        self.assertEqual(self.backend.tags["origin"], SOURCE)
        self.assertIsNone(self.backend.tags["gitee-mirror"])
        result = self.pipeline(
            requested_publication_attempt_id=attempt_id
        ).execute()
        self.assertEqual(result["state"], "PUBLICATION_COMPLETE")
        self.assertEqual(self.backend.tags["gitee-mirror"], SOURCE)
        self.assertEqual(self.backend.events.count("registry_push"), 1)

    def test_release_failure_resumes_without_duplicate_release(self):
        self.backend.fail_release_once = True
        pipe = self.pipeline()
        with self.assertRaises(publication.PublicationError):
            pipe.execute()
        attempt_id = pipe.attempt_dir.name
        self.assertIsNotNone(self.backend.release_payload)
        result = self.pipeline(
            requested_publication_attempt_id=attempt_id
        ).execute()
        self.assertEqual(result["state"], "PUBLICATION_COMPLETE")
        self.assertEqual(self.backend.events.count("release_create"), 1)

    def test_resume_identity_mismatch_does_not_modify_old_evidence(self):
        self.backend.fail_tag_once = True
        pipe = self.pipeline()
        with self.assertRaises(publication.PublicationError):
            pipe.execute()
        report = pipe.report_path
        before = report.read_bytes()
        with self.assertRaises(publication.PublicationError):
            self.pipeline(
                expected_source_sha="9" * 40,
                expected_publication_tool_sha=LIVE_MAIN,
                expected_live_main_sha=LIVE_MAIN,
                requested_publication_attempt_id=pipe.attempt_dir.name,
            ).execute()
        self.assertEqual(before, report.read_bytes())

    def test_existing_conflicting_tag_or_release_is_rejected_without_writes(self):
        for conflict in ("tag", "release"):
            with self.subTest(conflict=conflict), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                write_fixture(root)
                backend = FakeBackend()
                if conflict == "tag":
                    backend.tags["origin"] = "9" * 40
                else:
                    backend.release_payload = {
                        "tagName": f"v{VERSION}",
                        "isDraft": False,
                        "isPrerelease": True,
                        "url": "https://example.invalid/existing",
                        "body": "unrelated release",
                    }
                pipe = publication.Publication(
                    version=VERSION,
                    candidate_attempt_id=CANDIDATE_ATTEMPT,
                    expected_source_sha=SOURCE,
                    expected_publication_tool_sha=LIVE_MAIN,
                    expected_live_main_sha=LIVE_MAIN,
                    backend=backend,
                    root=root,
                )
                with self.assertRaises(publication.PublicationError):
                    pipe.execute()
                self.assertNotIn("registry_push", backend.events)

    def test_completed_publication_rejects_duplicate_external_writes(self):
        self.pipeline().execute()
        events = list(self.backend.events)
        with self.assertRaises(publication.PublicationError):
            self.pipeline().execute()
        self.assertEqual(events, self.backend.events)

    def test_same_version_lock_rejects_concurrent_executor(self):
        first = self.pipeline()
        second = self.pipeline()
        first.acquire_lock()
        try:
            with self.assertRaises(publication.PublicationError) as raised:
                second.acquire_lock()
            self.assertEqual(raised.exception.exit_code, 73)
        finally:
            first.release_lock()

    def test_attempt_ids_are_collision_safe_and_paths_are_isolated(self):
        with mock.patch.object(publication.time, "strftime", return_value="20260724T120000Z"):
            values = {publication.publication_id() for _ in range(50)}
        self.assertEqual(len(values), 50)
        self.assertTrue(all(publication.ATTEMPT_ID.fullmatch(value) for value in values))

    def test_version_attempt_sha_and_symlink_inputs_are_rejected(self):
        invalid = (
            {"version": "../rc.5"},
            {"version": f"{VERSION};touch /tmp/x"},
            {"candidate_attempt_id": "../../escape"},
            {"expected_source_sha": "a" * 39},
            {"expected_source_sha": "g" * 40},
            {"expected_publication_tool_sha": "a" * 39},
            {"expected_live_main_sha": "g" * 40},
        )
        for overrides in invalid:
            with self.subTest(overrides=overrides), self.assertRaises(
                publication.PublicationError
            ):
                self.pipeline(**overrides)
        attempts = self.candidate.parent
        replacement = attempts.parent / "unsafe"
        replacement.mkdir()
        self.candidate.rename(replacement / self.candidate.name)
        self.candidate.symlink_to(replacement / self.candidate.name, target_is_directory=True)
        with self.assertRaises(publication.PublicationError):
            self.pipeline().execute()

    def test_report_and_plan_schemas_accept_positive_and_reject_negative(self):
        self.pipeline().execute()
        _, report, report_path = self.latest_report()
        report_schema = json.loads(
            (
                self.root
                / "schemas"
                / "release"
                / "release_publication_report.v1.schema.json"
            ).read_text()
        )
        plan_schema = json.loads(
            (
                self.root
                / "schemas"
                / "release"
                / "release_publication_plan.v1.schema.json"
            ).read_text()
        )
        Draft202012Validator.check_schema(report_schema)
        Draft202012Validator.check_schema(plan_schema)
        Draft202012Validator(report_schema).validate(report)
        plan = json.loads((report_path.parent / "publication-plan.json").read_text())
        Draft202012Validator(plan_schema).validate(plan)
        bad_report = dict(report)
        bad_report.pop("publication_attempt_id")
        with self.assertRaises(ValidationError):
            Draft202012Validator(report_schema).validate(bad_report)
        bad_plan = dict(plan)
        bad_plan["targets"] = dict(plan["targets"])
        bad_plan["targets"]["git_tag"] = "../unsafe"
        with self.assertRaises(ValidationError):
            Draft202012Validator(plan_schema).validate(bad_plan)

    def test_atomic_write_failure_does_not_replace_existing_report(self):
        path = self.root / "atomic.json"
        path.write_text('{"old":true}\n')
        before = path.read_bytes()
        with mock.patch.object(publication.os, "replace", side_effect=OSError("injected")):
            with self.assertRaises(OSError):
                publication.atomic_write_json(path, {"new": True})
        self.assertEqual(before, path.read_bytes())

    def test_plan_report_and_logs_do_not_contain_secret_values(self):
        secret = "ghp_super_secret_value"
        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": secret, "REGISTRY_TOKEN": secret}):
            self.pipeline().execute()
        publications = (
            self.root / "artifacts" / "release" / "candidates" / VERSION / "publications"
        )
        for path in publications.rglob("*"):
            if path.is_file():
                self.assertNotIn(secret, path.read_text(encoding="utf-8"))

    def test_legacy_publish_entry_is_safe_and_make_entry_requires_identity(self):
        makefile = (REPO / "make" / "release.mk").read_text(encoding="utf-8")
        legacy = (
            REPO / "scripts" / "release" / "immutable_candidate_publish.sh"
        ).read_text(encoding="utf-8")
        self.assertIn("release.publish:", makefile)
        self.assertIn("CANDIDATE_ATTEMPT_ID", makefile)
        self.assertIn("EXPECTED_SOURCE_SHA", makefile)
        self.assertIn("EXPECTED_PUBLICATION_TOOL_SHA", makefile)
        self.assertIn("EXPECTED_LIVE_MAIN_SHA", makefile)
        self.assertNotIn("docker push", legacy)
        self.assertIn("release.publish", legacy)


if __name__ == "__main__":
    unittest.main(verbosity=2)
