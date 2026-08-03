from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "scripts" / "verify" / "user_formal_field_module_boundary_audit.py"


class UserFormalFieldModuleBoundaryAuditTest(unittest.TestCase):
    def test_daily_source_mount_is_an_addon_root_candidate(self) -> None:
        tree = ast.parse(AUDIT.read_text(encoding="utf-8"))
        assignments = {
            node.targets[0].id: node.value
            for node in tree.body
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        }
        candidates = ast.unparse(assignments["ADDON_ROOT_CANDIDATES"])
        self.assertIn("/mnt/source-addons", candidates)
        self.assertIn("/mnt/customer-addons", candidates)


if __name__ == "__main__":
    unittest.main()
