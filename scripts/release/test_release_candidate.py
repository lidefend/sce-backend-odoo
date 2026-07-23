#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "release"))


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


report = load(
    ROOT / "scripts/release/release_candidate_report.py",
    "release_candidate_report_test",
)
pipeline = load(
    ROOT / "scripts/release/release_candidate.py",
    "release_candidate_test",
)

SHA = "a" * 40
TREE = "b" * 40
VERSION = "1.0.0-rc.5"
IMAGE_ID = "sha256:" + "c" * 64
CONTRACT = "f" * 64


def write_candidate(root: Path) -> None:
    (root / "candidate-contract.sha256").write_text(CONTRACT + "\n", encoding="utf-8")
    archive = root / "candidate-image.tar"
    config_digest = "e" * 64
    archive_rows = [
        {
            "Config": f"blobs/sha256/{config_digest}",
            "RepoTags": [
                f"ghcr.io/lidefend/sce-product:{VERSION}",
                f"ghcr.io/lidefend/sce-product:sha-{SHA[:12]}",
            ],
            "Layers": [],
        }
    ]
    manifest_bytes = json.dumps(archive_rows).encode()
    with tarfile.open(archive, "w") as handle:
        member = tarfile.TarInfo("manifest.json")
        member.size = len(manifest_bytes)
        handle.addfile(member, io.BytesIO(manifest_bytes))
    frontend = "d" * 64
    (root / "frontend-build.sha256").write_text(frontend + "\n", encoding="utf-8")
    (root / "reloaded-image-id.txt").write_text(IMAGE_ID + "\n", encoding="utf-8")
    image = {
        "schema_version": 2,
        "source_sha": SHA,
        "oci_revision": SHA,
        "container_source_revision": SHA,
        "source_tree_sha": TREE,
        "product_version": VERSION,
        "image": f"ghcr.io/lidefend/sce-product:{VERSION}",
        "image_tags": [
            f"ghcr.io/lidefend/sce-product:{VERSION}",
            f"ghcr.io/lidefend/sce-product:sha-{SHA[:12]}",
        ],
        "registry_repository": "ghcr.io/lidefend/sce-product",
        "local_image_id": IMAGE_ID,
        "image_digest": None,
        "publish_status": "not_published",
        "archive_config_digest": "sha256:" + config_digest,
        "frontend_build_sha256": frontend,
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
    }
    (root / "image-manifest.json").write_text(json.dumps(image), encoding="utf-8")
    scan = {
        "schema_version": "candidate_scan.v2",
        "status": "completed",
        "source_sha": SHA,
        "image_digest": None,
        "local_image_id": IMAGE_ID,
        "identity_kind": "local_image_id",
        "publish_status": "not_published",
        "counts": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 2, "LOW": 4, "SECRET": 0},
        "policy": {"result": "pass"},
    }
    (root / "security-summary.json").write_text(json.dumps(scan), encoding="utf-8")
    (root / "sbom.cyclonedx.json").write_text(
        json.dumps({"bomFormat": "CycloneDX", "specVersion": "1.6"}),
        encoding="utf-8",
    )
    for name in (
        "syft-version.json",
        "trivy-db-metadata.json",
        "trivy-version.json",
        "trivy.json",
    ):
        (root / name).write_text("{}\n", encoding="utf-8")


class ReleaseCandidateReportTests(unittest.TestCase):
    def build(self, root: Path, **overrides):
        values = {
            "artifacts": root,
            "expected_source_sha": SHA,
            "expected_source_tree": TREE,
            "expected_version": VERSION,
            "expected_pipeline_contract": CONTRACT,
            "remote_main": {"github": SHA, "gitee": SHA},
            "required_checks": {
                "public_guard": "success",
                "professional_authorization": "success",
                "professional_quality_gate": "success",
            },
            "required_checks_head_sha": "e" * 40,
            "image_architecture": "amd64",
        }
        values.update(overrides)
        return report.build_ready_report(**values)

    def test_ready_report_binds_local_build_scan_sbom_and_dual_remote(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_candidate(root)
            payload = self.build(root)
            schema = json.loads(
                (
                    ROOT
                    / "schemas"
                    / "release"
                    / "release_candidate_report.v1.schema.json"
                ).read_text()
            )
            Draft202012Validator.check_schema(schema)
            Draft202012Validator(schema).validate(payload)
            self.assertTrue(payload["CANDIDATE_READY"])
            self.assertEqual(payload["status"], "ready")
            self.assertEqual(payload["source"]["commit_sha"], SHA)
            self.assertEqual(payload["source"]["tree_sha"], TREE)
            self.assertEqual(payload["source"]["pipeline_contract_sha256"], CONTRACT)
            self.assertEqual(payload["image"]["local_image_id"], IMAGE_ID)
            self.assertEqual(payload["image"]["publish_status"], "not_published")
            self.assertFalse(payload["external_effects"]["registry_push"])
            self.assertFalse(payload["external_effects"]["deployment"])
            self.assertIn("sbom.cyclonedx.json", payload["artifacts"]["sha256"])
            self.assertIn("candidate-contract.sha256", payload["artifacts"]["sha256"])

    def test_report_fails_closed_on_remote_scan_or_architecture_drift(self):
        cases = (
            {"remote_main": {"github": SHA, "gitee": "e" * 40}},
            {"image_architecture": "arm64"},
        )
        for overrides in cases:
            with self.subTest(overrides=overrides), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                write_candidate(root)
                with self.assertRaises(report.CandidateReportError):
                    self.build(root, **overrides)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_candidate(root)
            scan = json.loads((root / "security-summary.json").read_text())
            scan["counts"]["HIGH"] = 1
            (root / "security-summary.json").write_text(json.dumps(scan))
            with self.assertRaises(report.CandidateReportError):
                self.build(root)

    def test_ready_outputs_are_atomic_and_summary_is_short(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_candidate(root)
            payload = self.build(root)
            output = root / "release-report.json"
            report.write_ready_outputs(output, payload)
            persisted = json.loads(output.read_text())
            self.assertTrue(persisted["CANDIDATE_READY"])
            summary = (root / "release-summary.txt").read_text()
            self.assertIn("CANDIDATE_READY=true", summary)
            self.assertIn(f"SOURCE_SHA={SHA}", summary)
            self.assertIn("PUBLISHED=false", summary)
            self.assertLessEqual(len(summary.splitlines()), 9)

    def test_pipeline_has_one_entry_and_preserves_external_effect_boundary(self):
        makefile = (ROOT / "make/release.mk").read_text(encoding="utf-8")
        entry = (ROOT / "scripts/release/release_candidate.py").read_text(encoding="utf-8")
        self.assertIn("release.candidate: guard.prod.forbid", makefile)
        self.assertIn('python3 scripts/release/release_candidate.py --version "$(VERSION)"', makefile)
        self.assertIn('"main.sync"', entry)
        self.assertIn('"release.candidate.build"', entry)
        self.assertIn('"release.candidate.scan"', entry)
        self.assertNotIn("docker push", entry)
        self.assertNotIn("git tag", entry)
        self.assertNotIn("release.candidate.publish", entry)
        self.assertIn('"--single-branch"', entry)
        self.assertIn('"--no-local"', entry)
        self.assertIn('"history_hygiene"', entry)

    def test_resume_state_names_only_failed_stage_and_evidence(self):
        payload = pipeline.state_payload(
            version=VERSION,
            status="failed",
            stage="scan_sbom",
            source_sha=SHA,
            source_tree=TREE,
            pipeline_contract=CONTRACT,
            error="scanner unavailable",
            exit_code=17,
        )
        self.assertFalse(payload["CANDIDATE_READY"])
        self.assertEqual(payload["failed_stage"], "scan_sbom")
        self.assertEqual(payload["evidence"]["log"], "logs/scan_sbom.log")
        self.assertEqual(payload["exit_code"], 17)
        self.assertFalse(payload["external_effects"]["registry_push"])
        schema = json.loads(
            (
                ROOT / "schemas" / "release" / "release_candidate_report.v1.schema.json"
            ).read_text()
        )
        Draft202012Validator(schema).validate(payload)

    def test_version_and_artifact_path_are_deterministic(self):
        self.assertEqual(pipeline.validate_version(VERSION), VERSION)
        self.assertEqual(pipeline.artifact_directory(VERSION).name, VERSION)
        with self.assertRaises(pipeline.CandidatePipelineError):
            pipeline.validate_version("rc.5")

    def test_merge_main_uses_preserved_pr_head_for_required_checks(self):
        pr_head = "f" * 40
        check_rows = {
            "check_runs": [
                {
                    "name": name,
                    "status": "completed",
                    "conclusion": "success",
                    "head_sha": pr_head,
                    "completed_at": "2026-07-23T00:00:00Z",
                }
                for name in pipeline.REQUIRED_CHECKS
            ]
        }
        with mock.patch.object(
            pipeline,
            "command_output",
            side_effect=[f"{'1' * 40} {pr_head}", json.dumps(check_rows)],
        ):
            checks_head, checks = pipeline.required_check_results(SHA)
        self.assertEqual(checks_head, pr_head)
        self.assertEqual(set(checks), set(pipeline.REQUIRED_CHECKS))
        self.assertEqual(set(checks.values()), {"success"})

    def test_schema_rejects_ready_report_without_contract_binding(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_candidate(root)
            payload = self.build(root)
            del payload["source"]["pipeline_contract_sha256"]
            schema = json.loads(
                (
                    ROOT / "schemas" / "release" / "release_candidate_report.v1.schema.json"
                ).read_text()
            )
            errors = list(Draft202012Validator(schema).iter_errors(payload))
            self.assertTrue(errors)

    def test_resume_identity_rejects_source_tree_and_contract_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "release-report.json"
            payload = pipeline.state_payload(
                version=VERSION,
                status="failed",
                stage="build",
                source_sha=SHA,
                source_tree=TREE,
                pipeline_contract=CONTRACT,
                error="injected",
                exit_code=1,
            )
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(
                pipeline.CandidatePipelineError, "source tree differs"
            ):
                pipeline.report_matches_identity(
                    path,
                    VERSION,
                    SHA,
                    "1" * 40,
                    CONTRACT,
                )
            with self.assertRaisesRegex(
                pipeline.CandidatePipelineError, "tool contract differs"
            ):
                pipeline.report_matches_identity(
                    path,
                    VERSION,
                    SHA,
                    TREE,
                    "2" * 64,
                )

    def test_build_resume_rejects_tool_contract_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_candidate(root)
            with self.assertRaisesRegex(
                report.CandidateReportError, "tool contract binding differs"
            ):
                report.validate_build_artifacts(
                    root,
                    expected_source_sha=SHA,
                    expected_source_tree=TREE,
                    expected_version=VERSION,
                    expected_pipeline_contract="2" * 64,
                )

    def test_failure_injection_writes_failed_report_and_exit_code(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / VERSION
            injected = pipeline.CandidatePipelineError(
                "injected main sync failure",
                exit_code=19,
            )
            with (
                mock.patch.object(pipeline, "artifact_directory", return_value=root),
                mock.patch.object(pipeline, "command_output", return_value=""),
                mock.patch.object(pipeline, "run_logged", side_effect=injected),
                mock.patch.object(sys, "argv", ["release_candidate.py", "--version", VERSION]),
                mock.patch.dict(os.environ, {"ENV": "test"}, clear=False),
            ):
                result = pipeline.main()
            self.assertEqual(result, 1)
            payload = json.loads((root / "release-report.json").read_text())
            self.assertEqual(payload["status"], "failed")
            self.assertFalse(payload["CANDIDATE_READY"])
            self.assertEqual(payload["failed_stage"], "main_sync")
            self.assertEqual(payload["exit_code"], 19)
            self.assertEqual(payload["evidence"]["log"], "logs/main_sync.log")

    def test_failed_report_is_archived_before_retry_state_replaces_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "release-report.json"
            payload = pipeline.state_payload(
                version=VERSION,
                status="failed",
                stage="scan_sbom",
                source_sha=SHA,
                source_tree=TREE,
                pipeline_contract=CONTRACT,
                error="scanner unavailable",
                exit_code=2,
            )
            path.write_text(json.dumps(payload), encoding="utf-8")
            archived = pipeline.archive_failed_report(path)
            self.assertIsNotNone(archived)
            assert archived is not None
            self.assertEqual(json.loads(archived.read_text()), payload)
            self.assertEqual(json.loads(path.read_text()), payload)

    def test_candidate_lock_blocks_concurrent_process_and_releases(self):
        with tempfile.TemporaryDirectory() as temporary:
            artifacts = Path(temporary) / VERSION
            descriptor = pipeline.acquire_candidate_lock(artifacts)
            child = (
                "import sys; from pathlib import Path; "
                f"sys.path.insert(0, {str(ROOT / 'scripts' / 'release')!r}); "
                "import release_candidate as candidate; "
                "candidate.acquire_candidate_lock(Path(sys.argv[1]))"
            )
            blocked = subprocess.run(
                [sys.executable, "-c", child, str(artifacts)],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("candidate already running", blocked.stderr)
            os.close(descriptor)
            released = subprocess.run(
                [sys.executable, "-c", child, str(artifacts)],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(released.returncode, 0, released.stderr)

    def test_clean_source_clone_is_independent_and_identity_bound(self):
        with tempfile.TemporaryDirectory() as temporary:
            artifacts = Path(temporary) / VERSION
            artifacts.mkdir()

            def fake_logged(stage, command, log_path, *, env, cwd=pipeline.ROOT):
                self.assertEqual(stage, "source_repository_prepare")
                self.assertIn("--no-local", command)
                self.assertIn("--single-branch", command)
                self.assertIn("--no-tags", command)
                self.assertEqual(command[-2], pipeline.APPROVED_ORIGIN)
                destination = Path(command[-1])
                (destination / ".git" / "objects" / "info").mkdir(parents=True)

            with (
                mock.patch.object(pipeline, "run_logged", side_effect=fake_logged),
                mock.patch.object(
                    pipeline, "source_repository_identity", return_value=(SHA, TREE)
                ),
            ):
                source = pipeline.prepare_source_repository(
                    artifacts, SHA, TREE, SHA, env={}
                )
            self.assertEqual(source, artifacts / "source-repository")
            self.assertFalse((source / ".git" / "objects" / "info" / "alternates").exists())

    def test_clean_source_rejects_sha_tree_and_main_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            artifacts = Path(temporary)
            source = artifacts / "source-repository"
            source.mkdir()
            cases = (
                (("1" * 40, TREE), SHA, "SHA/tree differs"),
                ((SHA, "2" * 40), SHA, "SHA/tree differs"),
                ((SHA, TREE), "3" * 40, "approved GitHub main"),
            )
            for identity, github_main, message in cases:
                with (
                    self.subTest(identity=identity, github_main=github_main),
                    mock.patch.object(
                        pipeline, "source_repository_identity", return_value=identity
                    ),
                ):
                    with self.assertRaisesRegex(pipeline.CandidatePipelineError, message):
                        pipeline.prepare_source_repository(
                            artifacts, SHA, TREE, github_main, env={}
                        )

    def test_history_hygiene_runs_inside_clean_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            artifacts = Path(temporary) / "artifacts"
            source = Path(temporary) / "source"
            artifacts.mkdir()
            source.mkdir()
            with mock.patch.object(pipeline, "run_logged") as logged:
                pipeline.validate_source_history(source, artifacts, env={"ENV": "test"})
            args, kwargs = logged.call_args
            self.assertEqual(args[0], "history_hygiene")
            self.assertEqual(kwargs["cwd"], source)
            self.assertIn("--local-hygiene", args[1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
