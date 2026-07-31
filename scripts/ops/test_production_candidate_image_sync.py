#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import hashlib
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("production_candidate_image_sync.py")
SPEC = importlib.util.spec_from_file_location("production_candidate_image_sync", SCRIPT)
assert SPEC and SPEC.loader
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)


class CandidateImageSyncTests(unittest.TestCase):
    def test_archive_must_be_inside_candidate_root_and_match_digest(self):
        with tempfile.TemporaryDirectory(dir=sync.CANDIDATE_ROOT) as temporary:
            archive = Path(temporary) / "candidate-image.tar"
            config = b'{"architecture":"amd64"}'
            config_digest = hashlib.sha256(config).hexdigest()
            manifest = json.dumps([{"Config": f"blobs/sha256/{config_digest}", "RepoTags": ["verified"]}]).encode()
            with tarfile.open(archive, "w") as output:
                for name, payload in (("manifest.json", manifest), (f"blobs/sha256/{config_digest}", config)):
                    member = tarfile.TarInfo(name)
                    member.size = len(payload)
                    output.addfile(member, io.BytesIO(payload))
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            self.assertEqual(
                sync.validate_archive(archive, digest),
                (archive.resolve(), "sha256:" + config_digest),
            )
            with self.assertRaises(sync.SyncError):
                sync.validate_archive(archive, "0" * 64)

        with tempfile.TemporaryDirectory() as temporary:
            outside = Path(temporary) / "candidate-image.tar"
            outside.write_bytes(b"outside")
            digest = sync.hashlib.sha256(outside.read_bytes()).hexdigest()
            with self.assertRaises(sync.SyncError):
                sync.validate_archive(outside, digest)

    def test_image_reference_and_local_content_id_are_exact(self):
        content_id = "sha256:" + "a" * 64
        with mock.patch.object(sync, "run", return_value=content_id) as runner:
            sync.validate_image_identity("ghcr.io/lidefend/sce-product:1.0.0-rc.12", content_id)
        runner.assert_called_once_with(
            ["docker", "image", "inspect", "ghcr.io/lidefend/sce-product:1.0.0-rc.12", "--format", "{{.Id}}"]
        )
        for unsafe in ("latest", "1.0.0", "1.0.0-rc.12;id", "../candidate"):
            with self.assertRaises(sync.SyncError):
                sync.validate_image_identity(f"ghcr.io/lidefend/sce-product:{unsafe}", content_id)

    def test_stream_command_has_fixed_remote_and_docker_load_only(self):
        source = SCRIPT.read_text()
        self.assertIn('["ssh", "-o", "BatchMode=yes", SSH_TARGET, "docker", "load"]', source)
        self.assertEqual(sync.SSH_TARGET, "sc-prod")
        self.assertNotIn("scp", source)
        self.assertNotIn("systemctl", source)
        self.assertNotIn("docker compose", source)

    def test_matching_remote_archive_config_id_skips_retransfer(self):
        archive_config = "sha256:" + "b" * 64
        with (
            mock.patch.object(sync, "preflight"),
            mock.patch.object(sync, "validate_archive", return_value=(Path("candidate.tar"), archive_config)),
            mock.patch.object(sync, "validate_image_identity"),
            mock.patch.object(sync, "remote_image_id", return_value=archive_config),
            mock.patch.object(sync, "stream_load") as loader,
            mock.patch.dict(
                sync.os.environ,
                {"ENV": "prod", "PROD_DANGER": "1", "CONFIRM_PRODUCTION_IMAGE_SYNC": sync.CONFIRMATION},
                clear=True,
            ),
        ):
            sync.synchronize("a" * 40, Path("candidate.tar"), "c" * 64, "ghcr.io/lidefend/sce-product:1.0.0-rc.12", "sha256:" + "d" * 64)
        loader.assert_not_called()


if __name__ == "__main__":
    unittest.main()
