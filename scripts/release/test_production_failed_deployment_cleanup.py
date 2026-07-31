#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "production_failed_deployment_cleanup",
    ROOT / "scripts/release/production_failed_deployment_cleanup.py",
)
assert SPEC and SPEC.loader
cleanup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cleanup)


IMAGE_ID = "sha256:" + "a" * 64
TOOL_SHA = "b" * 40


def snapshot(root: Path):
    containers = []
    anonymous = iter(
        (
            "1" * 64,
            "2" * 64,
            "3" * 64,
            "4" * 64,
        )
    )
    destinations = {
        "sc_production-db-1": [("/var/lib/postgresql/data", "sce-sc_production-postgres")],
        "sc_production-redis-1": [("/data", "sce-sc_production-redis")],
        "sc_production-odoo-1": [
            ("/opt/sce-runtime/filestore", "sce-sc_production-filestore"),
            ("/opt/sce-runtime/logs", "sce-sc_production-logs"),
            ("/opt/sce-runtime/sessions", "sce-sc_production-sessions"),
            ("/opt/sce-runtime/tmp", "sce-sc_production-tmp"),
            ("/var/lib/odoo", next(anonymous)),
            ("/mnt/extra-addons", next(anonymous)),
        ],
        "sc_production-nginx-1": [
            ("/var/lib/odoo", next(anonymous)),
            ("/mnt/extra-addons", next(anonymous)),
        ],
    }
    tool_root = root / TOOL_SHA
    tool_root.mkdir()
    (tool_root / "DEPLOYMENT_TOOL_SHA").write_text(TOOL_SHA)
    for name in sorted(cleanup.CONTAINERS):
        containers.append(
            {
                "Name": f"/{name}",
                "Image": IMAGE_ID if name in {"sc_production-odoo-1", "sc_production-nginx-1"} else "other",
                "Config": {
                    "Labels": {
                        "com.docker.compose.project": cleanup.TARGET_PROJECT,
                        "com.docker.compose.project.working_dir": str(tool_root),
                    }
                },
                "Mounts": [
                    {"Type": "volume", "Name": volume, "Destination": destination}
                    for destination, volume in destinations[name]
                ],
            }
        )
    volume_names = {
        mount["Name"] for item in containers for mount in item["Mounts"]
    }
    volumes = []
    for name in sorted(volume_names):
        mountpoint = root / "volumes" / name / "_data"
        mountpoint.mkdir(parents=True)
        volumes.append(
            {
                "Name": name,
                "Mountpoint": str(mountpoint),
                "Labels": {"com.docker.compose.project": cleanup.TARGET_PROJECT},
            }
        )
    return {
        "containers": containers,
        "all_containers": list(containers),
        "project_container_rows": [{"Names": name} for name in cleanup.CONTAINERS],
        "network": {
            "Name": cleanup.NETWORK,
            "Labels": {"com.docker.compose.project": cleanup.TARGET_PROJECT},
            "Containers": {
                str(index): {"Name": name}
                for index, name in enumerate(cleanup.CONTAINERS)
            },
        },
        "volumes": volumes,
    }


class FailedDeploymentCleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.preserved = []
        for name in ("legacy", "tls", "nginx", "config"):
            path = self.root / name
            path.mkdir()
            self.preserved.append(str(path))
        self.paths = mock.patch.object(
            cleanup, "PRESERVED_PATHS", tuple(self.preserved)
        )
        self.legacy = mock.patch.object(
            cleanup, "LEGACY_ATTACHMENTS", Path(self.preserved[0])
        )
        self.paths.start()
        self.legacy.start()

    def tearDown(self):
        self.legacy.stop()
        self.paths.stop()
        self.temp.cleanup()

    def test_exact_inventory_passes_and_is_digest_locked(self):
        plan = cleanup.validate_snapshot(
            snapshot(self.root), expected_image_id=IMAGE_ID, expected_tool_sha=TOOL_SHA
        )
        self.assertEqual(plan["containers"], sorted(cleanup.CONTAINERS))
        self.assertEqual(set(plan["named_volumes"]), cleanup.NAMED_VOLUMES)
        self.assertEqual(len(plan["anonymous_volumes"]), 4)
        self.assertEqual(len(plan["plan_sha256"]), 64)

    def test_foreign_project_volume_is_rejected(self):
        value = snapshot(self.root)
        named = next(
            item for item in value["volumes"] if item["Name"] in cleanup.NAMED_VOLUMES
        )
        named["Labels"]["com.docker.compose.project"] = "other"
        with self.assertRaises(cleanup.CleanupError):
            cleanup.validate_snapshot(
                value, expected_image_id=IMAGE_ID, expected_tool_sha=TOOL_SHA
            )

    def test_anonymous_volume_external_user_is_rejected(self):
        value = snapshot(self.root)
        anonymous = next(
            item for item in value["volumes"] if item["Name"] not in cleanup.NAMED_VOLUMES
        )
        value["all_containers"].append(
            {
                "Name": "/foreign",
                "Mounts": [
                    {
                        "Type": "volume",
                        "Name": anonymous["Name"],
                        "Destination": "/data",
                    }
                ],
            }
        )
        with self.assertRaises(cleanup.CleanupError):
            cleanup.validate_snapshot(
                value, expected_image_id=IMAGE_ID, expected_tool_sha=TOOL_SHA
            )

    def test_preserved_path_overlap_is_rejected(self):
        value = snapshot(self.root)
        value["volumes"][0]["Mountpoint"] = self.preserved[0]
        with self.assertRaises(cleanup.CleanupError):
            cleanup.validate_snapshot(
                value, expected_image_id=IMAGE_ID, expected_tool_sha=TOOL_SHA
            )

    def test_unexpected_container_is_rejected(self):
        value = snapshot(self.root)
        value["project_container_rows"].append({"Names": "sc_production-worker-1"})
        with self.assertRaises(cleanup.CleanupError):
            cleanup.validate_snapshot(
                value, expected_image_id=IMAGE_ID, expected_tool_sha=TOOL_SHA
            )

    def test_oversized_filestore_is_rejected(self):
        value = snapshot(self.root)
        filestore = next(
            Path(item["Mountpoint"])
            for item in value["volumes"]
            if item["Name"] == "sce-sc_production-filestore"
        )
        with (filestore / "too-large").open("wb") as handle:
            handle.truncate(cleanup.MAX_FAILED_FILESTORE_BYTES + 1)
        with self.assertRaises(cleanup.CleanupError):
            cleanup.validate_snapshot(
                value, expected_image_id=IMAGE_ID, expected_tool_sha=TOOL_SHA
            )

    def test_apply_requires_confirmation_and_plan_digest(self):
        with tempfile.TemporaryDirectory() as output:
            base = {
                "ENV": "prod",
                "PRODUCTION_COMPOSE_PROJECT": cleanup.TARGET_PROJECT,
                "TARGET_DB": cleanup.TARGET_DATABASE,
                "EXPECTED_FAILED_IMAGE_ID": IMAGE_ID,
                "EXPECTED_FAILED_DEPLOYMENT_TOOL_SHA": TOOL_SHA,
                "FAILED_CLEANUP_EVIDENCE": str(Path(output) / "evidence.json"),
                "PROD_DANGER": "1",
            }
            with mock.patch.dict(cleanup.os.environ, base, clear=True):
                with self.assertRaises(cleanup.CleanupError):
                    cleanup._validate_environment(True)
            base.update(
                {
                    "CONFIRM_FAILED_DEPLOYMENT_CLEANUP": cleanup.CONFIRMATION,
                    "EXPECTED_CLEANUP_PLAN_SHA256": "c" * 64,
                }
            )
            with mock.patch.dict(cleanup.os.environ, base, clear=True):
                cleanup._validate_environment(True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
