#!/usr/bin/env python3
from __future__ import annotations

import json
import unittest

from scripts.ops.quick_suite_fingerprint import build_units, fingerprint_suite


class FingerprintTests(unittest.TestCase):
    def test_same_input_same_fingerprint(self):
        self.assertEqual(
            fingerprint_suite(["make", "x"], ["make/guards.mk"]),
            fingerprint_suite(["make", "x"], ["make/guards.mk"]),
        )

    def test_changed_input_changes_fingerprint(self):
        self.assertNotEqual(
            fingerprint_suite(["make", "x"], ["make/guards.mk"]),
            fingerprint_suite(["make", "x"], ["make/ci.mk"]),
        )

    def test_missing_input_fails_closed(self):
        with self.assertRaises(ValueError):
            fingerprint_suite(["make", "x"], ["does/not/exist.py"])

    def test_manifest_emits_units_document(self):
        manifest = {
            "check": "ci.local.quick.run",
            "suites": [
                {"id": "a", "command": ["make", "a"], "inputs": ["make/guards.mk"]},
            ],
        }
        units = build_units(manifest)
        self.assertEqual(units["schema"], "evidence_scope.units.v1")
        self.assertEqual(units["units"][0]["id"], "a")
        self.assertTrue(units["units"][0]["fingerprint"])


if __name__ == "__main__":
    unittest.main()
