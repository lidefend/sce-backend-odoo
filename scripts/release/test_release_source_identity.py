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
    }


def release_manifest() -> dict:
    return {"source_sha": SHA, "oci_revision": SHA, "image_digest": DIGEST}


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


class ArtifactIdentityTests(unittest.TestCase):
    def test_all_artifact_identities_match(self):
        result = identity.validate_artifact_identity(
            expected_sha=SHA,
            expected_image_digest=DIGEST,
            image_manifest=image_manifest(),
            release_manifest=release_manifest(),
            oci_revision=SHA,
            container_revision=SHA,
            actual_image_digest=DIGEST,
        )
        self.assertEqual(result, {"source_sha": SHA, "image_digest": DIGEST})

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
                    identity.validate_artifact_identity(
                        expected_sha=SHA,
                        expected_image_digest=DIGEST,
                        image_manifest=candidate,
                        release_manifest=release_manifest(),
                        oci_revision=SHA,
                        container_revision=SHA,
                        actual_image_digest=DIGEST,
                    )

    def test_release_manifest_mismatch_is_rejected(self):
        candidate = release_manifest()
        candidate["source_sha"] = "c" * 40
        with self.assertRaises(identity.ReleaseIdentityError):
            identity.validate_artifact_identity(
                expected_sha=SHA,
                expected_image_digest=DIGEST,
                image_manifest=image_manifest(),
                release_manifest=candidate,
                oci_revision=SHA,
                container_revision=SHA,
                actual_image_digest=DIGEST,
            )

    def test_image_digest_mismatch_is_rejected(self):
        with self.assertRaisesRegex(identity.ReleaseIdentityError, "actual image digest"):
            identity.validate_artifact_identity(
                expected_sha=SHA,
                expected_image_digest=DIGEST,
                image_manifest=image_manifest(),
                release_manifest=release_manifest(),
                oci_revision=SHA,
                container_revision=SHA,
                actual_image_digest="sha256:" + "c" * 64,
            )

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
