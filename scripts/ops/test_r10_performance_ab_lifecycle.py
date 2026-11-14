#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = Path(__file__).with_name("r10_performance_ab_lifecycle.py")
SPEC = importlib.util.spec_from_file_location("r10_performance_ab_lifecycle", SCRIPT)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class R10PerformanceLifecycleTest(unittest.TestCase):
    def test_profile_stack_names_each_arm_without_shared_runtime_resources(self):
        profile = module._profile(module.DEFAULT_PROFILE)
        self.assertTrue(module.STACK_TEMPLATE.is_file())
        stack = module.STACK_TEMPLATE.read_text(encoding="utf-8")
        nginx = stack.split("  nginx:", 1)[1].split("\nvolumes:\n", 1)[0]
        self.assertIn("- ingress", nginx)
        self.assertEqual(stack.count("- ingress"), 1)
        self.assertNotEqual(
            profile["arms"]["a"]["database"], profile["arms"]["b"]["database"]
        )
        self.assertTrue(profile["arms"]["a"]["database"].startswith("sc_demo_"))
        self.assertTrue(profile["arms"]["b"]["database"].startswith("sc_demo_"))
        self.assertNotEqual(
            profile["arms"]["a"]["database_volume"],
            profile["arms"]["b"]["database_volume"],
        )
        self.assertNotEqual(
            profile["arms"]["a"]["internal_network"],
            profile["arms"]["b"]["internal_network"],
        )

    def test_prepare_refuses_without_exact_confirmation(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(module.LifecycleError, "confirmation"):
                module.prepare(
                    module.DEFAULT_PROFILE,
                    candidate_sha="a" * 40,
                    snapshot="/data/backups/daily-demo-dev/sc_demo-20261114T000000Z-deadbeef",
                    evidence=Path("/tmp/unused.json"),
                    a_sha="b" * 40,
                )

    def test_snapshot_identity_is_fail_closed(self):
        for value in (
            "/tmp/snapshot",
            "/data/backups/perf-r10/sc_demo-20261114T000000Z-deadbeef",
            "/data/backups/daily-demo-dev/not-a-snapshot",
        ):
            with self.subTest(value=value):
                with self.assertRaisesRegex(module.LifecycleError, "snapshot"):
                    module._remote_snapshot("sc-root", value)

    def test_compose_commands_name_only_the_declared_arm(self):
        command = module._compose(
            "/opt/projects/secure/r10-performance-ab/sc-perf-b-r10.env",
            "/opt/projects/perf-r10/runtime/stack.yml",
            "sc-perf-b-r10",
            "up -d db",
        )
        self.assertIn("--project-name sc-perf-b-r10", command)
        self.assertIn("sc-perf-b-r10.env", command)
        self.assertNotIn("sc-demo-dev", command)

    def test_candidate_build_passes_output_and_identity_as_make_overrides(self):
        sha = "a" * 40
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            def build(command, *, env=None):
                if command[0] == "make":
                    output = Path(command[-3].split("=", 1)[1])
                    output.mkdir(parents=True, exist_ok=True)
                    (output / ".build-sha256").write_text("b" * 64 + "\n")
                return b""

            with mock.patch.object(module, "_run", side_effect=build) as run:
                bundle, digest = module._build_candidate_bundle(sha, root)
        command = run.call_args.args[0]
        make_command = run.call_args_list[0].args[0]
        self.assertEqual(bundle.name, sha)
        self.assertEqual(digest, "b" * 64)
        self.assertEqual(command[0], "bash")
        self.assertIn(f"FRONTEND_DIST_DIR={bundle}", make_command)
        self.assertIn(f"SC_SOURCE_REVISION={sha}", make_command)

    def test_readback_reports_arm_scoped_containers_and_http(self):
        arm = module._profile(module.DEFAULT_PROFILE)["arms"]["a"]
        output = (
            f"CONTAINERS={arm['odoo_container']},{arm['db_container']}\n"
            f"NETWORKS={arm['internal_network']}\n"
            f"VOLUMES={arm['database_volume']},{arm['odoo_volume']}\n"
            "DATABASE=sc_perf_a_r10|d7c7f68c-d280-11f1-a914-0a0d1da8b8b8|德阳智能制造产教融合项目\n"
            "HTTP=PASS\n"
        ).encode()
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            module, "_ssh", return_value=output
        ) as ssh:
            evidence = Path(temporary) / "readback.json"
            result = module.readback(module.DEFAULT_PROFILE, evidence=evidence)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(ssh.call_count, 2)
        self.assertIn(arm["odoo_container"], result["arms"]["a"]["containers"])
        self.assertEqual(result["arms"]["a"]["http_login"], "PASS")

    def test_destroy_refuses_without_exact_confirmation(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(module.LifecycleError, "confirmation"):
                module.destroy(
                    module.DEFAULT_PROFILE,
                    evidence=Path("/tmp/unused-destroy.json"),
                )


if __name__ == "__main__":
    unittest.main()
