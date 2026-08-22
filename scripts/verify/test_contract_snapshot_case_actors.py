#!/usr/bin/env python3

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CASES = (ROOT / "docs" / "contract" / "cases.yml").read_text(encoding="utf-8")


class SnapshotCaseActorsTest(unittest.TestCase):
    def test_pm_cases_use_governed_fixture_login(self):
        self.assertNotIn('"user": "pm"', CASES)
        self.assertIn('"user": "demo_role_pm"', CASES)


if __name__ == "__main__":
    unittest.main()
