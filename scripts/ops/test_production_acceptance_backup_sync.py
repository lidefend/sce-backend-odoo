#!/usr/bin/env python3
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("production_acceptance_backup_sync.py")
SPEC = importlib.util.spec_from_file_location("production_acceptance_backup_sync", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class BackupSyncTest(unittest.TestCase):
    def test_rejects_missing_confirmation_before_state_change(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(MODULE.SyncError, "exact production"):
                MODULE.sync("sc_production-20260807T183712Z-b11d0f4d")

    def test_rejects_unsafe_identity(self):
        with mock.patch.dict(os.environ, {
            "CONFIRM_PRODUCTION_ACCEPTANCE_BACKUP_SYNC": MODULE.CONFIRMATION,
        }, clear=True):
            with self.assertRaisesRegex(MODULE.SyncError, "invalid"):
                MODULE.sync("../sc_production")

    def test_contract_uses_exact_private_source_and_inventory(self):
        self.assertEqual(MODULE.SOURCE_HOST, "172.31.4.192")
        self.assertEqual(MODULE.SOURCE_ROOT, Path("/data/backups/sc_production"))
        self.assertNotIn("*", "".join(MODULE.FILES))


if __name__ == "__main__":
    unittest.main()
