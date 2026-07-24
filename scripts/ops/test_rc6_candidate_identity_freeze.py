#!/usr/bin/env python3
"""Regression tests for the fixed RC6 candidate identity contract."""

from __future__ import annotations

import json
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import rc6_candidate_identity_freeze as freeze  # noqa: E402


DIGEST = "sha256:" + "a" * 64


def declaration() -> dict:
    return {
        "schema_version": freeze.DECLARATION_SCHEMA,
        "candidate_name": "RC6",
        "source_sha": freeze.CANDIDATE_SHA,
        "approval_status": "FROZEN",
        "ci_status": "PASS",
        "ci_run_url": (
            "https://github.com/lidefend/sce-backend-odoo/actions/runs/30066968527"
        ),
        "ci_checks": {key: "success" for key in sorted(freeze.REQUIRED_CHECKS)},
        "required_merge_commits": freeze.REQUIRED_MERGES,
        "image_repository": freeze.IMAGE_REPOSITORY,
        "image_manifest_digest": DIGEST,
        "image_ref": f"{freeze.IMAGE_REPOSITORY}@{DIGEST}",
        "image_revision_label": freeze.CANDIDATE_SHA,
        "image_pull_policy": "never",
        "image_locally_available": True,
        "movable_image_reference_used": False,
        "freeze_timestamp": "2026-07-24T05:00:00Z",
        "supersession_policy": freeze.SUPERSESSION_POLICY,
        "build_provenance": {
            "source_tree_sha": "b" * 40,
            "local_daemon_image_id": "sha256:" + "c" * 64,
            "registry_config_digest": "sha256:" + "1" * 64,
            "frontend_build_sha256": "d" * 64,
            "archive_sha256": "e" * 64,
            "build_manifest_sha256": "f" * 64,
        },
    }


class DeclarationTests(unittest.TestCase):
    def test_exact_declaration_passes(self) -> None:
        result = freeze.validate_declaration(declaration())
        self.assertTrue(result["rc6_candidate_identity_frozen"])
        self.assertEqual(result["rc6_candidate_sha"], freeze.CANDIDATE_SHA)

    def test_short_candidate_sha_is_rejected(self) -> None:
        payload = declaration()
        payload["source_sha"] = freeze.CANDIDATE_SHA[:12]
        with self.assertRaises(freeze.FreezeError):
            freeze.validate_declaration(payload)

    def test_main_advancement_cannot_change_candidate(self) -> None:
        payload = declaration()
        payload["source_sha"] = "1" * 40
        payload["image_revision_label"] = "1" * 40
        with self.assertRaises(freeze.FreezeError):
            freeze.validate_declaration(payload)

    def test_movable_image_reference_is_rejected(self) -> None:
        payload = declaration()
        payload["image_ref"] = f"{freeze.IMAGE_REPOSITORY}:rc6"
        payload["movable_image_reference_used"] = True
        with self.assertRaises(freeze.FreezeError):
            freeze.validate_declaration(payload)

    def test_oci_revision_must_equal_candidate(self) -> None:
        payload = declaration()
        payload["image_revision_label"] = "2" * 40
        with self.assertRaises(freeze.FreezeError):
            freeze.validate_declaration(payload)

    def test_required_checks_must_all_pass(self) -> None:
        payload = declaration()
        payload["ci_checks"]["professional_quality_gate"] = "failure"
        with self.assertRaises(freeze.FreezeError):
            freeze.validate_declaration(payload)

    def test_required_merge_commits_are_exact(self) -> None:
        payload = declaration()
        payload["required_merge_commits"] = {"PR_43": freeze.CANDIDATE_SHA}
        with self.assertRaises(freeze.FreezeError):
            freeze.validate_declaration(payload)

    def test_changed_digest_cannot_be_silently_substituted(self) -> None:
        payload = declaration()
        payload["image_manifest_digest"] = "sha256:" + "9" * 64
        with self.assertRaises(freeze.FreezeError):
            freeze.validate_declaration(payload)

    def test_supersession_policy_is_immutable(self) -> None:
        payload = declaration()
        payload["supersession_policy"] = "follow main"
        with self.assertRaises(freeze.FreezeError):
            freeze.validate_declaration(payload)

    def test_provenance_distinguishes_daemon_id_and_config_digest(self) -> None:
        payload = declaration()
        payload["build_provenance"]["registry_config_digest"] = "1" * 64
        with self.assertRaises(freeze.FreezeError):
            freeze.validate_declaration(payload)

    def test_registry_manifest_identity_keeps_manifest_and_config_separate(self) -> None:
        response = {
            "Descriptor": {"digest": "sha256:" + "a" * 64},
            "OCIManifest": {"config": {"digest": "sha256:" + "b" * 64}},
        }
        completed = mock.Mock(returncode=0, stdout=json.dumps(response), stderr="")
        with mock.patch.object(freeze, "run", return_value=completed):
            identity = freeze._manifest_identity(freeze.SOURCE_TAG)
        self.assertEqual(identity["manifest_digest"], "sha256:" + "a" * 64)
        self.assertEqual(identity["config_digest"], "sha256:" + "b" * 64)


class RegistryTests(unittest.TestCase):
    def test_workspace_clone_is_shallow_single_branch_and_tag_free(self) -> None:
        source = (HERE / "rc6_candidate_identity_freeze.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('"--depth=1"', source)
        self.assertIn('"--no-tags"', source)
        self.assertIn('"--single-branch"', source)

    def test_image_revision_checks_label_and_environment(self) -> None:
        image = {
            "Id": "sha256:" + "a" * 64,
            "Config": {
                "Labels": {"org.opencontainers.image.revision": freeze.CANDIDATE_SHA},
                "Env": [f"SC_SOURCE_REVISION={freeze.CANDIDATE_SHA}"],
            },
        }
        revision, config_digest = freeze._image_revision(image)
        self.assertEqual(revision, freeze.CANDIDATE_SHA)
        self.assertEqual(config_digest, image["Id"])
        image["Config"]["Env"] = ["SC_SOURCE_REVISION=wrong"]
        with self.assertRaises(freeze.FreezeError):
            freeze._image_revision(image)

    def test_existing_source_tag_is_never_overwritten(self) -> None:
        artifacts_payload = {
            "source_sha": freeze.CANDIDATE_SHA,
            "image_tags": [
                "ghcr.io/lidefend/sce-product:1.0.0-rc.5",
                freeze.SOURCE_TAG,
            ],
            "publish_status": "not_published",
        }
        with tempfile.TemporaryDirectory() as directory:
            artifacts = Path(directory)
            (artifacts / "image-manifest.json").write_text(
                json.dumps(artifacts_payload), encoding="utf-8"
            )
            with (
                mock.patch.object(freeze, "_docker_config_has_ghcr_auth", return_value=True),
                mock.patch.object(freeze, "_local_image", return_value={
                    "Id": "sha256:" + "a" * 64,
                    "Config": {
                        "Labels": {
                            "org.opencontainers.image.revision": freeze.CANDIDATE_SHA
                        },
                        "Env": [f"SC_SOURCE_REVISION={freeze.CANDIDATE_SHA}"],
                    },
                }),
                mock.patch.object(
                    freeze, "_manifest_digest", return_value="sha256:" + "8" * 64
                ),
            ):
                with self.assertRaisesRegex(
                    freeze.FreezeError, "refusing a silent registry replacement"
                ):
                    freeze.publish_image(
                        artifacts, artifacts / "freeze-evidence.json"
                    )

    def test_evidence_is_atomic_and_mode_0600(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            digest = freeze.atomic_write(path, {"safe": True})
            self.assertRegex(digest, r"^[0-9a-f]{64}$")
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)


if __name__ == "__main__":
    unittest.main()
