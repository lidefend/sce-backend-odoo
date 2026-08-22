#!/usr/bin/env python3

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "scripts" / "contract" / "snapshot_export.py").read_text(encoding="utf-8")


class SnapshotUserResolutionTest(unittest.TestCase):
    def test_missing_requested_user_fails_closed(self):
        self.assertIn('raise SystemExit(f"user not found: {args.user}")', SOURCE)
        self.assertNotIn('find_user(su_env, "admin")', SOURCE)


if __name__ == "__main__":
    unittest.main()
