#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("production_restore_cancel.py")
SPEC = importlib.util.spec_from_file_location("production_restore_cancel", SCRIPT)
assert SPEC and SPEC.loader
cancel = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cancel)


class RestoreCancelTests(unittest.TestCase):
    def test_remote_contract_is_exact_report_and_process_scoped(self):
        source = cancel.REMOTE_CANCEL
        self.assertIn('/data/backups/sc_production/restore-rehearsals', source)
        self.assertIn('/opt/ops/production_backup_restore.py', source)
        self.assertIn('report.get("status") != "PLANNED"', source)
        self.assertIn('os.kill(pid, signal.SIGTERM)', source)
        self.assertNotIn('SIGKILL', source)
        self.assertNotIn('docker rm', source)
        self.assertNotIn('systemctl', source)

    def test_report_path_is_fixed_scope(self):
        valid = "/data/backups/sc_production/restore-rehearsals/sc_restore_20260731t192200z_a0c706ba.json"
        original = cancel.git
        try:
            cancel.git = lambda *args: "a" * 40 if args[:2] in (("rev-parse", "HEAD"), ("ls-remote", "origin"), ("ls-remote", "gitee-mirror")) else ("main" if args == ("branch", "--show-current") else "")
            cancel.preflight("a" * 40, valid)
            with self.assertRaises(cancel.CancelError):
                cancel.preflight("a" * 40, "/tmp/sc_restore_20260731t192200z_a0c706ba.json")
        finally:
            cancel.git = original


if __name__ == "__main__":
    unittest.main()
