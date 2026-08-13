#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/dev/frontend_acceptance_runtime_profile.py"
SPEC = importlib.util.spec_from_file_location("acceptance_runtime_profile", MODULE_PATH)
assert SPEC and SPEC.loader
PROFILE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROFILE)


class AcceptanceRuntimeProfileTest(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(
            (ROOT / "config/frontend/acceptance_environments_v1.json").read_text(encoding="utf-8")
        )

    def resolve_policy(self, policy):
        with tempfile.TemporaryDirectory() as directory:
            policy_path = Path(directory) / "policy.json"
            policy_path.write_text(json.dumps(policy), encoding="utf-8")
            with mock.patch.object(PROFILE, "POLICY", policy_path), mock.patch.object(
                PROFILE, "_primary_worktree", return_value=ROOT
            ):
                return PROFILE.resolve("local")

    def test_resolves_complete_locked_identity(self):
        values = self.resolve_policy(self.policy)
        self.assertEqual(values["DB_NAME"], "sc_frontend_acceptance")
        self.assertEqual(values["ODOO_DBFILTER"], "^sc_frontend_acceptance$")
        self.assertEqual(values["DB_DATA"], "sc_fe_r2_p1_01_db")
        self.assertEqual(values["SC_ACCEPTANCE_CREDENTIAL_CONTAINER"], "sc-fe-r2-p1-01-odoo-1")
        self.assertEqual(values["BACKEND_ACCEPTANCE_PORT"], "18082")
        self.assertEqual(values["FRONTEND_ACCEPTANCE_PORT"], "5175")

    def test_rejects_database_filter_drift(self):
        self.policy["profiles"]["local"]["managed_runtime"]["database_filter"] = "^sc_demo$"
        with self.assertRaisesRegex(ValueError, "database_filter"):
            self.resolve_policy(self.policy)

    def test_rejects_shared_volume_identity(self):
        runtime = self.policy["profiles"]["local"]["managed_runtime"]
        runtime["volumes"]["redis"] = runtime["volumes"]["database"]
        with self.assertRaisesRegex(ValueError, "three distinct"):
            self.resolve_policy(self.policy)

    def test_rejects_frontend_port_drift(self):
        self.policy["profiles"]["local"]["managed_runtime"]["services"]["frontend_port"] = 5199
        with self.assertRaisesRegex(ValueError, "base_url"):
            self.resolve_policy(self.policy)

    def test_rejects_profile_without_managed_runtime(self):
        with self.assertRaisesRegex(ValueError, "no managed_runtime"):
            PROFILE.resolve("test")


if __name__ == "__main__":
    unittest.main()
