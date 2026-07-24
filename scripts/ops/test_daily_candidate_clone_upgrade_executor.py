#!/usr/bin/env python3
"""Regression tests for the fixed RC6 clone executor."""

from __future__ import annotations

import io
import json
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

import daily_candidate_clone_upgrade_executor as executor  # noqa: E402


class IdentityTests(unittest.TestCase):
    def test_candidate_constants_are_immutable(self):
        self.assertEqual(
            executor.CANDIDATE_SHA,
            "fb1f2b5a6e93fb4d7865023e6cda2961848c3cb8",
        )
        self.assertEqual(
            executor.CANDIDATE_IMAGE_REF,
            "ghcr.io/lidefend/sce-product@"
            "sha256:02edec2628b276834abd10ec3cc9ef96517fb499c6b0e8a60b19d59e3694fdeb",
        )
        self.assertNotIn(":latest", executor.CANDIDATE_IMAGE_REF)
        self.assertNotIn(":rc6", executor.CANDIDATE_IMAGE_REF)

    def test_target_daemon_config_and_revision_must_both_match(self):
        image = {
            "Id": executor.CANDIDATE_CONFIG_DIGEST,
            "RepoTags": [],
            "Config": {
                "Labels": {
                    "org.opencontainers.image.revision": executor.CANDIDATE_SHA
                }
            },
        }
        self.assertTrue(executor.validate_local_candidate(image)["oci_revision_match"])
        image["Id"] = "sha256:" + "0" * 64
        with self.assertRaises(executor.ExecutionError):
            executor.validate_local_candidate(image)

    def test_movable_target_tag_is_rejected(self):
        image = {
            "Id": executor.CANDIDATE_CONFIG_DIGEST,
            "RepoTags": ["ghcr.io/lidefend/sce-product:rc6"],
            "Config": {
                "Labels": {
                    "org.opencontainers.image.revision": executor.CANDIDATE_SHA
                }
            },
        }
        with self.assertRaises(executor.ExecutionError):
            executor.validate_local_candidate(image)

    def test_archive_is_tagless_and_config_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "candidate.tar"
            config_name = "blobs/sha256/" + executor.CANDIDATE_CONFIG_DIGEST[7:]
            config = json.dumps(
                {
                    "config": {
                        "Labels": {
                            "org.opencontainers.image.revision": executor.CANDIDATE_SHA
                        }
                    }
                }
            ).encode()
            manifest = json.dumps(
                [{"Config": config_name, "RepoTags": None, "Layers": []}]
            ).encode()
            with tarfile.open(path, "w") as archive:
                for name, content in (
                    ("manifest.json", manifest),
                    (config_name, config),
                ):
                    info = tarfile.TarInfo(name)
                    info.size = len(content)
                    archive.addfile(info, io.BytesIO(content))
            result = executor.validate_offline_archive(path)
            self.assertEqual(result["archive_tag_count"], 0)
            self.assertTrue(result["oci_revision_match"])


class BoundaryTests(unittest.TestCase):
    def test_confirmation_precedes_daily_preflight(self):
        with (
            mock.patch.dict("os.environ", {}, clear=True),
            mock.patch.object(executor, "_daily_preflight") as preflight,
        ):
            with self.assertRaisesRegex(executor.ExecutionError, "confirmation"):
                executor.execute()
        preflight.assert_not_called()

    def test_clone_login_parser_returns_values_without_logging(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "daily.env"
            path.write_text(
                "SC_BOOTSTRAP_LOGIN=approved-user\n"
                "SC_BOOTSTRAP_SECRET=not-emitted\n",
                encoding="utf-8",
            )
            self.assertEqual(
                executor._load_clone_identity(path),
                ("approved-user", "not-emitted"),
            )

    def test_resource_names_are_exactly_scoped(self):
        self.assertEqual(
            executor._resource_name("sc-rc6-rehearsal-deadbeef", "db-volume"),
            "sc-rc6-rehearsal-deadbeef-db-volume",
        )
        with self.assertRaises(executor.ExecutionError):
            executor._resource_name("sc_demo", "db-volume")

    def test_source_mounts_are_copies_not_daily_paths(self):
        source = (HERE / "daily_candidate_clone_upgrade_executor.py").read_text()
        self.assertIn('"archive",', source)
        self.assertIn('"addons/smart_construction_custom"', source)
        self.assertNotIn(
            "/var/lib/docker/volumes/sc_dev_odoo_data/_data:",
            source,
        )
        self.assertNotIn("docker compose down -v", source)
        self.assertNotIn("--init=", source)

    def test_cleanup_only_uses_recorded_resources(self):
        resources = executor.Resources()
        resources.containers = ["sc-rc6-rehearsal-test-odoo"]
        resources.volumes = ["sc-rc6-rehearsal-test-db-volume"]
        resources.networks = ["sc-rc6-rehearsal-test-net"]
        with (
            mock.patch.object(executor, "_run", return_value=b"") as run,
            mock.patch.object(executor, "_no_leftovers", return_value=True),
        ):
            self.assertTrue(resources.cleanup())
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(
            commands,
            [
                ["docker", "rm", "-f", "sc-rc6-rehearsal-test-odoo"],
                [
                    "docker",
                    "volume",
                    "rm",
                    "sc-rc6-rehearsal-test-db-volume",
                ],
                ["docker", "network", "rm", "sc-rc6-rehearsal-test-net"],
            ],
        )

    def test_evidence_contract_rejects_secret_keys(self):
        payload = {
            "rehearsal_set_id": (
                "sc_demo-rc6-rehearsal-20260724T060000Z-deadbeef"
            ),
            "password": "never",
        }
        with self.assertRaises(Exception):
            executor.admission.assert_no_sensitive_output(payload)


if __name__ == "__main__":
    unittest.main(verbosity=2)
