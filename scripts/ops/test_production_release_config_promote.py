#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("production_release_config_promote.py")
SPEC = importlib.util.spec_from_file_location("production_release_config_promote", SCRIPT)
assert SPEC and SPEC.loader
promote = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(promote)


class ProductionReleaseConfigPromoteTests(unittest.TestCase):
    def test_remote_contract_is_fixed_scope_atomic_and_rollback_capable(self):
        source = promote.REMOTE_PROMOTE
        self.assertIn('/opt/sce/config/sc_production/runtime.env', source)
        self.assertIn('/etc/scems/production-promotion.env', source)
        self.assertIn('sc_production-odoo-1', source)
        self.assertIn('shutil.copy2(runtime_backup, runtime_path)', source)
        self.assertIn('os.replace(runtime_temp, runtime_path)', source)
        self.assertIn('"ACCEPTANCE_PACKAGE_DIGEST": acceptance_digest', source)
        self.assertIn('observed_promotion.get("ACCEPTANCE_PACKAGE_DIGEST") != acceptance_digest', source)
        self.assertNotIn('systemctl', source)
        self.assertNotIn('docker compose', source)
        self.assertNotIn('DB_PASSWORD', source)


if __name__ == "__main__":
    unittest.main()
