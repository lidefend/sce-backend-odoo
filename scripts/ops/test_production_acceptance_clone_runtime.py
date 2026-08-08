#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import stat
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("production_acceptance_clone_runtime.py")
SPEC = importlib.util.spec_from_file_location("production_acceptance_clone_runtime", SCRIPT)
assert SPEC and SPEC.loader
RUNTIME = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNTIME)


class ProductionAcceptanceCloneRuntimeTests(unittest.TestCase):
    def test_accepts_generic_tenant_module_identity(self) -> None:
        RUNTIME.validate_identity(
            "sc_restore_20260808t102000z_4d7e91a2",
            "1" * 40,
            "sce_customer_sample",
            "sha256:" + "2" * 64,
            18095,
        )

    def test_rejects_module_path_escape(self) -> None:
        with self.assertRaisesRegex(RUNTIME.CloneRuntimeError, "tenant module"):
            RUNTIME.validate_identity(
                "sc_restore_20260808t102000z_4d7e91a2",
                "1" * 40,
                "../private_addon",
                "sha256:" + "2" * 64,
                18095,
            )

    def test_rejects_non_loopback_acceptance_port_range(self) -> None:
        with self.assertRaisesRegex(RUNTIME.CloneRuntimeError, "loopback port"):
            RUNTIME.validate_identity(
                "sc_restore_20260808t102000z_4d7e91a2",
                "1" * 40,
                "sce_customer_sample",
                "sha256:" + "2" * 64,
                8069,
            )

    def test_tenant_refresh_has_a_distinct_confirmation(self) -> None:
        self.assertNotEqual(RUNTIME.CONFIRMATION, RUNTIME.REFRESH_CONFIRMATION)
        self.assertEqual(
            RUNTIME.REFRESH_CONFIRMATION,
            "REFRESH_ISOLATED_PRODUCTION_ACCEPTANCE_TENANT_RUNTIME",
        )

    def test_image_refresh_has_a_distinct_confirmation(self) -> None:
        self.assertNotIn(
            RUNTIME.IMAGE_REFRESH_CONFIRMATION,
            {RUNTIME.CONFIRMATION, RUNTIME.REFRESH_CONFIRMATION},
        )

    def test_module_upgrade_is_narrow_and_stop_after_init(self) -> None:
        self.assertEqual(RUNTIME.UPGRADE_MODULES, frozenset({"sc_norm_engine"}))
        self.assertNotIn(
            RUNTIME.MODULE_UPGRADE_CONFIRMATION,
            {RUNTIME.CONFIRMATION, RUNTIME.REFRESH_CONFIRMATION, RUNTIME.IMAGE_REFRESH_CONFIRMATION},
        )
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"-u", module, "--without-demo=all", "--stop-after-init"', source)
        self.assertIn('["docker", "stop", "--time", "30", odoo]', source)
        self.assertIn("not 18080 <= port <= 18120", source)
        self.assertEqual(
            RUNTIME.IMAGE_REFRESH_CONFIRMATION,
            "REFRESH_ISOLATED_PRODUCTION_ACCEPTANCE_IMAGE_RUNTIME",
        )

    def test_edge_starts_on_internal_network_before_public_connect(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"--network", internal, "--publish"', source)
        self.assertIn('"--user", "root"', source)
        self.assertIn('["docker", "network", "connect", public, web]', source)

    def test_runtime_secret_is_strong_private_and_stable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = RUNTIME.ensure_runtime_secret(Path(directory))
            first = path.read_text(encoding="utf-8")
            self.assertGreaterEqual(len(first.split("=", 1)[1].strip()), 48)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(RUNTIME.ensure_runtime_secret(Path(directory)), path)
            self.assertEqual(path.read_text(encoding="utf-8"), first)


if __name__ == "__main__":
    unittest.main()
