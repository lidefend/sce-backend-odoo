#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("dev_acceptance_release_probe", ROOT / "scripts/ops/dev_acceptance_release_probe.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)
SHA = "a" * 40


class RuntimeIdentityTest(unittest.TestCase):
    def test_exact_identity_passes(self):
        def requester(_url):
            return 200, json.dumps({"git_sha": SHA, "database": "sc_demo", "frontend_build_sha256": "f" * 64}), {}

        result = MODULE.probe_runtime_identity("https://daily.example.test", "sc_demo", SHA, requester)
        self.assertEqual(result["status"], "PASS")

    def test_sha_and_database_drift_fail(self):
        def requester(_url):
            return 200, json.dumps({"git_sha": "b" * 40, "database": "other"}), {}

        result = MODULE.probe_runtime_identity("https://daily.example.test", "sc_demo", SHA, requester)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("runtime_identity_sha_mismatch", result["errors"])
        self.assertIn("runtime_identity_database_mismatch", result["errors"])

    def test_invalid_expected_sha_fails_before_network(self):
        calls = []
        result = MODULE.probe_runtime_identity("https://daily.example.test", "sc_demo", "short", lambda url: calls.append(url))
        self.assertEqual(result["errors"], ["expected_sha_invalid"])
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
