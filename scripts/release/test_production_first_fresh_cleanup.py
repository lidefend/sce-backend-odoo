#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "production_first_fresh_cleanup",
    ROOT / "scripts/release/production_first_fresh_cleanup.py",
)
assert SPEC and SPEC.loader
cleanup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cleanup)


def snapshot():
    containers = []
    for name, project in cleanup.OLD_CONTAINERS.items():
        mounts = []
        containers.append(
            {
                "Name": f"/{name}",
                "Config": {"Labels": {"com.docker.compose.project": project}},
                "Mounts": mounts,
            }
        )
    by_name = {item["Name"].lstrip("/"): item for item in containers}
    owners = list(cleanup.OLD_CONTAINERS)
    for index, volume in enumerate(sorted(cleanup.OLD_VOLUMES)):
        owner = owners[index % len(owners)]
        by_name[owner]["Mounts"].append(
            {
                "Type": "volume",
                "Name": volume,
                "Destination": f"/data/{index}",
            }
        )
    by_name[owners[0]]["Mounts"].append(
        {
            "Type": "bind",
            "Source": "/data/odoo/legacy_attachments/raw_files",
            "Destination": "/mnt/legacy-files",
        }
    )
    networks = []
    for name, project in cleanup.OLD_NETWORKS.items():
        members = {
            str(index): {"Name": container}
            for index, container in enumerate(
                item
                for item, expected_project in cleanup.OLD_CONTAINERS.items()
                if expected_project == project
            )
        }
        networks.append(
            {
                "Name": name,
                "Labels": {"com.docker.compose.project": project},
                "Containers": members,
            }
        )
    return {
        "containers": containers,
        "networks": networks,
        "volumes": [{"Name": name} for name in cleanup.OLD_VOLUMES],
    }


class FirstFreshCleanupTests(unittest.TestCase):
    def test_exact_inventory_passes(self):
        plan = cleanup.validate_snapshot(snapshot())
        self.assertEqual(set(plan["containers"]), set(cleanup.OLD_CONTAINERS))
        self.assertEqual(set(plan["volumes"]), cleanup.OLD_VOLUMES)
        self.assertEqual(set(plan["networks"]), set(cleanup.OLD_NETWORKS))

    def test_new_production_container_blocks_cleanup(self):
        value = snapshot()
        value["containers"].append(
            {
                "Name": "/sc_production-db-1",
                "Config": {
                    "Labels": {"com.docker.compose.project": "sc_production"}
                },
                "Mounts": [],
            }
        )
        with self.assertRaises(cleanup.CleanupError):
            cleanup.validate_snapshot(value)

    def test_unrelated_volume_user_blocks_cleanup(self):
        value = snapshot()
        volume = sorted(cleanup.OLD_VOLUMES)[0]
        value["containers"].append(
            {
                "Name": "/unrelated-db-1",
                "Config": {
                    "Labels": {"com.docker.compose.project": "unrelated"}
                },
                "Mounts": [
                    {
                        "Type": "volume",
                        "Name": volume,
                        "Destination": "/var/lib/postgresql/data",
                    }
                ],
            }
        )
        with self.assertRaises(cleanup.CleanupError):
            cleanup.validate_snapshot(value)

    def test_unrelated_network_member_blocks_cleanup(self):
        value = snapshot()
        value["networks"][0]["Containers"]["foreign"] = {
            "Name": "unrelated-app-1"
        }
        with self.assertRaises(cleanup.CleanupError):
            cleanup.validate_snapshot(value)

    def test_missing_whitelisted_resource_blocks_cleanup(self):
        value = snapshot()
        value["volumes"].pop()
        with self.assertRaises(cleanup.CleanupError):
            cleanup.validate_snapshot(value)

    def test_apply_requires_exact_confirmation(self):
        env = {
            "ENV": "prod",
            "PRODUCTION_COMPOSE_PROJECT": "sc_production",
            "TARGET_DB": "sc_production",
            "PROD_DANGER": "1",
        }
        with mock.patch.dict(cleanup.os.environ, env, clear=True):
            with self.assertRaises(cleanup.CleanupError):
                cleanup._validate_environment(True)
        env["CONFIRM_FRESH_PRODUCTION_DEPLOY"] = cleanup.CONFIRMATION
        with mock.patch.dict(cleanup.os.environ, env, clear=True):
            cleanup._validate_environment(True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
