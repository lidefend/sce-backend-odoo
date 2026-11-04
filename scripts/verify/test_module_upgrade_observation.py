#!/usr/bin/env python3
"""Offline tests for module_upgrade_observation upgrade delegation.

The upgrade step must delegate to the governed ``make mod.upgrade`` lane and
must never assemble ``docker exec ... odoo -u ...`` by hand.
"""
from __future__ import annotations

import subprocess
import unittest

from scripts.verify import module_upgrade_observation as wrapper


class _FakeCompleted(subprocess.CompletedProcess):
    def __init__(self, args, returncode):
        super().__init__(args, returncode)


class UpgradeDelegationTests(unittest.TestCase):
    def setUp(self):
        self.orig_run = wrapper.subprocess.run
        self.calls = []

    def tearDown(self):
        wrapper.subprocess.run = self.orig_run

    def _patch_run(self, fn):
        def fake_run(cmd, **kwargs):
            self.calls.append(cmd)
            return fn(cmd, **kwargs)
        wrapper.subprocess.run = fake_run

    def test_delegates_to_governed_make_mod_upgrade(self):
        self._patch_run(lambda cmd, **kw: _FakeCompleted(cmd, 0))
        code, cmd = wrapper._upgrade("sc_dev_demo", ["smart_construction_core"])
        self.assertEqual(code, 0)
        self.assertEqual(cmd[:2], ["make", "--no-print-directory"])
        self.assertIn("mod.upgrade", cmd)
        self.assertIn("CODEX_NEED_UPGRADE=1", cmd)
        self.assertIn("MODULE=smart_construction_core", cmd)
        self.assertIn("DB_NAME=sc_dev_demo", cmd)
        self.assertIn("ENV=dev", cmd)
        joined = " ".join(cmd)
        self.assertNotIn("docker exec", joined)
        self.assertNotIn("--stop-after-init", joined)
        self.assertNotIn("odoo -d", joined)

    def test_passes_env_file_when_supplied(self):
        self._patch_run(lambda cmd, **kw: _FakeCompleted(cmd, 0))
        _, cmd = wrapper._upgrade("sc_dev_demo", ["smart_construction_core"],
                                  env_file="/registered/.env.dev")
        self.assertIn("ENV_FILE=/registered/.env.dev", cmd)

    def test_returns_command_on_timeout(self):
        def timeout(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd, kwargs.get("timeout", 1800))
        self._patch_run(timeout)
        code, cmd = wrapper._upgrade("sc_dev_demo", ["smart_construction_core"])
        self.assertEqual(code, 124)
        self.assertIn("mod.upgrade", cmd)

    def test_returns_command_on_oserror(self):
        def oserror(cmd, **kwargs):
            raise OSError("spawn failed")
        self._patch_run(oserror)
        code, cmd = wrapper._upgrade("sc_dev_demo", ["smart_construction_core"])
        self.assertEqual(code, 125)
        self.assertIn("mod.upgrade", cmd)

    def test_preserves_nonzero_upgrade_exit_code(self):
        self._patch_run(lambda cmd, **kw: _FakeCompleted(cmd, 255))
        code, cmd = wrapper._upgrade("sc_dev_demo", ["smart_construction_core"])
        self.assertEqual(code, 255)
        self.assertIn("mod.upgrade", cmd)


if __name__ == "__main__":
    unittest.main()
