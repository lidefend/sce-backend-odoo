#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "release_source_identity", ROOT / "scripts/release/release_source_identity.py"
)
assert SPEC and SPEC.loader
identity = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(identity)

SHA = "a" * 40
DIGEST = "sha256:" + "b" * 64
FRONTEND_DIGEST = "sha256:" + "9" * 64


def repository_runner(
    *,
    remote: str = identity.EXPECTED_REMOTE_URL,
    status: str = "",
    head: str = SHA,
    main: str = SHA,
):
    outputs = {
        ("git", "remote", "get-url", "origin"): remote,
        ("git", "status", "--porcelain", "--untracked-files=all"): status,
        ("git", "rev-parse", "HEAD"): head,
        ("git", "ls-remote", "origin", "refs/heads/main"): f"{main}\trefs/heads/main",
    }

    def run(command: list[str], _cwd: Path) -> str:
        return outputs[tuple(command)]

    return run


def image_manifest() -> dict:
    return {
        "source_sha": SHA,
        "oci_revision": SHA,
        "container_source_revision": SHA,
        "image_digest": DIGEST,
        "frontend_image_digest": FRONTEND_DIGEST,
    }


def release_manifest() -> dict:
    return {
        "schema_version": "product_release_manifest.v4",
        "repository": "lidefend/sce-backend-odoo",
        "branch": "main",
        "source_sha": SHA,
        "oci_revision": SHA,
        "container_source_revision": SHA,
        "image_digest": DIGEST,
        "frontend_image_digest": FRONTEND_DIGEST,
        "registry_repository": "ghcr.io/lidefend/sce-product",
        "registry_refs": [f"ghcr.io/lidefend/sce-product@{DIGEST}"] * 2,
        "frontend_registry_repository": "ghcr.io/lidefend/sce-frontend",
        "frontend_registry_refs": [
            f"ghcr.io/lidefend/sce-frontend@{FRONTEND_DIGEST}"
        ]
        * 2,
        "local_image_id": "sha256:" + "1" * 64,
        "archive_config_digest": "sha256:" + "2" * 64,
        "archive_reload_image_id": "sha256:" + "3" * 64,
        "archive_sha256": "c" * 64,
        "frontend_local_image_id": "sha256:" + "4" * 64,
        "frontend_archive_config_digest": "sha256:" + "5" * 64,
        "frontend_archive_reload_image_id": "sha256:" + "6" * 64,
        "frontend_archive_sha256": "7" * 64,
        "frontend_sha256": "8" * 64,
        "baseline_checksum": "d" * 64,
        "base_image_digests": {
            "frontend_builder": "sha256:" + "e" * 64,
            "frontend_runtime": "sha256:" + "a" * 64,
            "odoo_runtime": "sha256:" + "f" * 64,
        },
        "scan": {
            "status": "completed",
            "source_sha": SHA,
            "image_digest": DIGEST,
            "counts": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 1, "LOW": 2, "SECRET": 0},
            "policy": {"result": "pass"},
            "frontend": {
                "image_digest": FRONTEND_DIGEST,
                "counts": {
                    "CRITICAL": 0,
                    "HIGH": 0,
                    "MEDIUM": 0,
                    "LOW": 0,
                    "SECRET": 0,
                },
                "policy": {"result": "pass"},
            },
        },
        "candidate_status": "rc",
        "deployment_status": "not_deployed",
    }


def validate_artifact(**overrides):
    values = {
        "expected_sha": SHA,
        "expected_image_digest": DIGEST,
        "expected_frontend_image_digest": FRONTEND_DIGEST,
        "image_manifest": image_manifest(),
        "release_manifest": release_manifest(),
        "oci_revision": SHA,
        "container_revision": SHA,
        "actual_registry_digests": [f"ghcr.io/lidefend/sce-product@{DIGEST}"],
        "frontend_oci_revision": SHA,
        "frontend_actual_registry_digests": [
            f"ghcr.io/lidefend/sce-frontend@{FRONTEND_DIGEST}"
        ],
    }
    values.update(overrides)
    return identity.validate_artifact_identity(**values)


class RepositoryIdentityTests(unittest.TestCase):
    def test_matching_repository_head_remote_and_explicit_sha_pass(self):
        result = identity.validate_repository_identity(Path("."), SHA, runner=repository_runner())
        self.assertEqual(result["repository"], "lidefend/sce-backend-odoo")
        self.assertEqual(result["source_sha"], SHA)

    def test_source_sha_is_required_and_must_be_full(self):
        for value in ("", "abc", "A" * 40):
            with self.subTest(value=value), self.assertRaises(identity.ReleaseIdentityError):
                identity.validate_repository_identity(Path("."), value, runner=repository_runner())

    def test_wrong_repository_is_rejected(self):
        with self.assertRaisesRegex(identity.ReleaseIdentityError, "origin must be"):
            identity.validate_repository_identity(
                Path("."),
                SHA,
                runner=repository_runner(remote="https://github.com/Leedefend/sce-backend-odoo.git"),
            )

    def test_dirty_worktree_is_rejected(self):
        with self.assertRaisesRegex(identity.ReleaseIdentityError, "worktree must be clean"):
            identity.validate_repository_identity(
                Path("."), SHA, runner=repository_runner(status=" M make/release.mk")
            )

    def test_old_or_mismatched_sha_is_rejected(self):
        with self.assertRaisesRegex(identity.ReleaseIdentityError, "release identity mismatch"):
            identity.validate_repository_identity(
                Path("."), "c" * 40, runner=repository_runner()
            )

    def test_remote_main_mismatch_is_rejected(self):
        with self.assertRaisesRegex(identity.ReleaseIdentityError, "release identity mismatch"):
            identity.validate_repository_identity(
                Path("."), SHA, runner=repository_runner(main="d" * 40)
            )

    def test_explicit_boundary_head_accepts_remote_main_difference(self):
        result = identity.validate_repository_identity(
            Path("."),
            SHA,
            allow_boundary_head=True,
            runner=repository_runner(main="d" * 40),
        )
        self.assertEqual(result["source_authority"], "boundary_head")
        self.assertEqual(result["head_sha"], SHA)
        self.assertEqual(result["remote_main_sha"], "d" * 40)

    def test_boundary_head_still_rejects_source_head_difference(self):
        with self.assertRaisesRegex(identity.ReleaseIdentityError, "release identity mismatch"):
            identity.validate_repository_identity(
                Path("."),
                SHA,
                allow_boundary_head=True,
                runner=repository_runner(head="c" * 40, main="d" * 40),
            )


class ArtifactIdentityTests(unittest.TestCase):
    def test_all_artifact_identities_match(self):
        result = validate_artifact()
        self.assertEqual(
            result,
            {
                "source_sha": SHA,
                "image_digest": DIGEST,
                "frontend_image_digest": FRONTEND_DIGEST,
            },
        )

    def test_each_revision_mismatch_is_rejected(self):
        fields = (
            "source_sha",
            "oci_revision",
            "container_source_revision",
        )
        for field in fields:
            with self.subTest(field=field):
                candidate = image_manifest()
                candidate[field] = "c" * 40
                with self.assertRaises(identity.ReleaseIdentityError):
                    validate_artifact(image_manifest=candidate)

    def test_release_manifest_mismatch_is_rejected(self):
        candidate = release_manifest()
        candidate["source_sha"] = "c" * 40
        with self.assertRaises(identity.ReleaseIdentityError):
            validate_artifact(release_manifest=candidate)

    def test_incomplete_manifest_or_scan_fails_closed(self):
        for mutation in (
            "missing_medium",
            "wrong_repository",
            "missing_archive",
            "v3_schema",
            "missing_frontend_archive",
            "missing_frontend_scan",
            "frontend_scan_digest",
            "bad_base_images",
            "bad_frontend_registry_refs",
        ):
            candidate = release_manifest()
            if mutation == "missing_medium":
                del candidate["scan"]["counts"]["MEDIUM"]
            elif mutation == "wrong_repository":
                candidate["repository"] = "Leedefend/sce-backend-odoo"
            elif mutation == "missing_archive":
                candidate.pop("archive_sha256")
            elif mutation == "v3_schema":
                candidate["schema_version"] = "product_release_manifest.v3"
            elif mutation == "missing_frontend_archive":
                candidate.pop("frontend_archive_sha256")
            elif mutation == "missing_frontend_scan":
                candidate["scan"].pop("frontend")
            elif mutation == "frontend_scan_digest":
                candidate["scan"]["frontend"]["image_digest"] = DIGEST
            elif mutation == "bad_base_images":
                candidate["base_image_digests"].pop("frontend_runtime")
            else:
                candidate["frontend_registry_refs"] = []
            with self.subTest(mutation=mutation), self.assertRaises(
                identity.ReleaseIdentityError
            ):
                validate_artifact(release_manifest=candidate)

    def test_image_digest_mismatch_is_rejected(self):
        with self.assertRaisesRegex(identity.ReleaseIdentityError, "registry digest"):
            validate_artifact(
                actual_registry_digests=[
                    "ghcr.io/lidefend/sce-product@sha256:" + "c" * 64
                ]
            )

    def test_frontend_identity_mismatches_are_rejected(self):
        candidate = image_manifest()
        candidate["frontend_image_digest"] = DIGEST
        with self.assertRaisesRegex(
            identity.ReleaseIdentityError, "EXPECTED_FRONTEND_IMAGE_DIGEST"
        ):
            validate_artifact(image_manifest=candidate)

        candidate = release_manifest()
        candidate["frontend_image_digest"] = DIGEST
        with self.assertRaisesRegex(
            identity.ReleaseIdentityError, "EXPECTED_FRONTEND_IMAGE_DIGEST"
        ):
            validate_artifact(release_manifest=candidate)

        with self.assertRaisesRegex(
            identity.ReleaseIdentityError, "frontend image is not bound"
        ):
            validate_artifact(frontend_actual_registry_digests=[])

        with self.assertRaisesRegex(
            identity.ReleaseIdentityError, "frontend OCI revision"
        ):
            validate_artifact(frontend_oci_revision="c" * 40)

        with self.assertRaisesRegex(
            identity.ReleaseIdentityError, "EXPECTED_FRONTEND_IMAGE_DIGEST"
        ):
            validate_artifact(expected_frontend_image_digest=DIGEST * 2)

    def test_release_manifest_checksum_is_required(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / "product-release-manifest.json"
            checksum = root / "product-release-manifest.sha256"
            manifest.write_text(json.dumps(release_manifest()) + "\n", encoding="utf-8")
            checksum.write_text(
                f"{hashlib.sha256(manifest.read_bytes()).hexdigest()}  {manifest.name}\n",
                encoding="utf-8",
            )
            identity.validate_manifest_checksum(manifest, checksum)
            checksum.write_text(f"{'0' * 64}  {manifest.name}\n", encoding="utf-8")
            with self.assertRaisesRegex(identity.ReleaseIdentityError, "checksum mismatch"):
                identity.validate_manifest_checksum(manifest, checksum)


if __name__ == "__main__":
    unittest.main(verbosity=2)
