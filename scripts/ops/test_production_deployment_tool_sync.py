#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("production_deployment_tool_sync.py")
SPEC = importlib.util.spec_from_file_location("production_deployment_tool_sync", SCRIPT)
assert SPEC and SPEC.loader
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)


class DeploymentToolSyncTests(unittest.TestCase):
    def test_remote_contract_is_atomic_immutable_and_fixed_root(self):
        source = sync.REMOTE_INSTALL
        self.assertIn('/opt/sce/deployment-tools', source)
        self.assertIn('os.replace(staging, target)', source)
        self.assertIn('DEPLOYMENT_TOOL_SHA', source)
        self.assertIn('immutable target differs', source)
        self.assertNotIn('systemctl', source)
        self.assertNotIn('docker', source)


if __name__ == "__main__":
    unittest.main()
