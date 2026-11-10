#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("daily_runtime_build_identity.py")
SPEC = importlib.util.spec_from_file_location("daily_runtime_build_identity", SCRIPT)
assert SPEC and SPEC.loader
identity = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(identity)

SHA = "a" * 40
OTHER = "b" * 40
FINGERPRINT = "c" * 64


def carriers() -> tuple[dict, dict, str, dict]:
    receipt = {
        "schema": "b2.deployment_receipt.v1",
        "env": "daily",
        "git_head": SHA,
        "frontend_build_sha256": FINGERPRINT,
        "backend_git_sha": SHA,
        "database": "sc_demo",
        "containers": [{"name": "sc-demo-dev-odoo-1", "running": True}],
        "health_readback": {"healthy": True},
        "operator": "executor",
        "deployed_at": "2026-11-09T16:00:00.000Z",
    }
    build = {
        "schema": "frontend.build_info.v1",
        "sha": SHA,
        "built_at": "2026-11-09T16:00:00.000Z",
        "environment": "daily",
        "version": "9.8.7-rc.20",
    }
    runtime = {
        "demo": {
            "git_sha": SHA,
            "environment": "daily",
            "frontend_build_sha256": FINGERPRINT,
        },
        "platform_control": {
            "git_sha": SHA,
            "environment": "daily",
            "frontend_build_sha256": FINGERPRINT,
        },
    }
    return build, runtime, SHA, receipt


class DailyRuntimeBuildIdentityTest(unittest.TestCase):
    def assert_mismatch(self, key: str, carriers_value: tuple[dict, dict, str, dict]):
        mismatches = identity.identity_mismatches(
            SHA, "daily", *carriers_value
        )
        self.assertIn(key, {row["key"] for row in mismatches})

    def test_all_four_identity_carriers_agree(self):
        self.assertEqual(
            identity.identity_mismatches(SHA, "daily", *carriers()),
            [],
        )

    def test_each_identity_carrier_is_a_negative_case(self):
        build, runtime, head, receipt = carriers()
        build["sha"] = OTHER
        self.assert_mismatch("build_info.sha", (build, runtime, head, receipt))

        build, runtime, head, receipt = carriers()
        runtime["demo"]["git_sha"] = OTHER
        self.assert_mismatch("runtime_demo.git_sha", (build, runtime, head, receipt))

        build, runtime, head, receipt = carriers()
        self.assert_mismatch("git_head", (build, runtime, OTHER, receipt))

        build, runtime, head, receipt = carriers()
        receipt["git_head"] = OTHER
        self.assert_mismatch("receipt.git_head", (build, runtime, head, receipt))

    def test_environment_and_artifact_fingerprint_drift_is_detected(self):
        build, runtime, head, receipt = carriers()
        build["environment"] = "dev"
        self.assert_mismatch("build_info.environment", (build, runtime, head, receipt))

        build, runtime, head, receipt = carriers()
        runtime["platform_control"]["frontend_build_sha256"] = "d" * 64
        self.assert_mismatch("runtime_frontend_fingerprints", (build, runtime, head, receipt))

    def test_receipt_required_fields_are_enforced(self):
        for key in (
            "git_head",
            "env",
            "frontend_build_sha256",
            "backend_git_sha",
            "database",
            "containers",
            "health_readback",
            "operator",
            "deployed_at",
        ):
            build, runtime, head, receipt = carriers()
            receipt.pop(key)
            with self.subTest(key=key):
                self.assertTrue(
                    identity.identity_mismatches(SHA, "daily", build, runtime, head, receipt)
                )

    def test_retention_keeps_newest_thirty_timestamp_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index in range(35):
                path = root / f"20261109T1600{index:02d}000000Z"
                path.mkdir()
                (path / "receipt.json").write_text("{}", encoding="utf-8")
            unrelated = root / "manual"
            unrelated.mkdir()
            removed = identity.retain_recent(root, 30)
            remaining = sorted(path.name for path in root.iterdir() if path.is_dir())
            self.assertEqual(len(remaining), 31)
            self.assertEqual(len(removed), 5)
            self.assertIn("manual", remaining)

    def test_local_receipt_is_timestamped_and_readable(self):
        with tempfile.TemporaryDirectory() as directory:
            _, _, _, receipt = carriers()
            path = identity.write_local_receipt(Path(directory), receipt)
            self.assertTrue(path.is_file())
            self.assertEqual(json.loads(path.read_text()), receipt)

    def test_remote_program_embeds_the_shared_comparison_authority(self):
        self.assertIn("def identity_mismatches(", identity.REMOTE_PROGRAM)
        for token in (
            'http_json("/build-info.json")',
            "runtime-version",
            ".deployed.json",
            "docker",
        ):
            self.assertIn(token, identity.REMOTE_PROGRAM)

    def test_server_receipt_is_ignored_by_the_source_checkout(self):
        ignored = (identity.ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("/.deployed.json", ignored)


if __name__ == "__main__":
    unittest.main()
