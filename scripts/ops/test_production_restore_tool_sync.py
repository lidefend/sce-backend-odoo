#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("production_restore_tool_sync.py")
SPEC = importlib.util.spec_from_file_location("production_restore_tool_sync", SCRIPT)
assert SPEC and SPEC.loader
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)


class RestoreToolSyncTests(unittest.TestCase):
    def test_current_source_contains_fix_and_has_digest(self):
        self.assertRegex(sync.validate_source(), r"^[0-9a-f]{64}$")

    def test_source_without_fix_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "tool.py"
            path.write_text("print('unsafe')\n")
            with self.assertRaises(sync.SyncError):
                sync.validate_source(path)

    def test_remote_contract_is_fixed_scope_and_atomic(self):
        source = sync.REMOTE_INSTALL
        self.assertIn('/opt/ops/production_backup_restore.py', source)
        self.assertIn('os.replace(temporary_path, target)', source)
        self.assertIn('backup-install-history', source)
        self.assertIn('LOCK_EX | fcntl.LOCK_NB', source)
        self.assertNotIn('systemctl', source)

    def test_remote_command_shell_quotes_program_and_identities(self):
        command = sync.remote_command("a" * 64, "b" * 40)
        self.assertTrue(command.startswith("python3 -c "))
        self.assertIn("'", command)
        with self.assertRaises(sync.SyncError):
            sync.remote_command("bad;digest", "b" * 40)


if __name__ == "__main__":
    unittest.main()
