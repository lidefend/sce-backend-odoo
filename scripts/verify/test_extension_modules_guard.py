from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GUARD = ROOT / "scripts" / "verify" / "extension_modules_guard.sh"


class ExtensionModulesGuardTests(unittest.TestCase):
    def test_guard_checks_installed_module_authority(self):
        source = GUARD.read_text(encoding="utf-8")
        self.assertIn("LEFT JOIN ir_module_module", source)
        self.assertIn("module.state", source)
        self.assertIn('"${state}" != "installed"', source)
        self.assertIn("configured modules without installed authority", source)

    def test_guard_remains_fail_closed(self):
        source = GUARD.read_text(encoding="utf-8")
        self.assertIn("set -euo pipefail", source)
        self.assertIn("exit 1", source)


if __name__ == "__main__":
    unittest.main()
