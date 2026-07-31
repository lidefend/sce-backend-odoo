#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
HELPER_PATH = ROOT / "scripts/release/production_user_activation_readiness.py"
SPEC = importlib.util.spec_from_file_location("production_user_activation_readiness", HELPER_PATH)
assert SPEC and SPEC.loader
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)


class ProductionUserActivationReadinessTests(unittest.TestCase):
    def valid_env(self, root: Path) -> dict[str, str]:
        return {
            "ENV": "prod",
            "TARGET_DB": "sc_production",
            "PROD_READONLY_VERIFY": "1",
            "USER_ACTIVATION_READINESS_RUN_ID": "20260801T010203Z-a1b2c3",
            "USER_ACTIVATION_READINESS_OUTPUT": str(
                root / "user-activation-readiness-20260801T010203Z-a1b2c3.json"
            ),
        }

    def ready_snapshot(self) -> dict:
        return {
            "database": "sc_production",
            "transaction": {"verification": "PASS"},
            "smart_core_state": "installed",
            "runtime_environment": "production",
            "runtime_tenant_configured": True,
            "runtime_tenant_fingerprint": "a" * 64,
            "activation_admin_count": 1,
            "eligible_internal_user_count": 7,
            "active_batch_count": 0,
            "pending_credential_count": 0,
            "used_credential_count": 0,
            "delivery_audit_count": 0,
        }

    def test_control_plane_requires_exact_prod_readonly_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with mock.patch.object(helper, "EVIDENCE_ROOT", root):
                active_env = self.valid_env(root)
                self.assertEqual(helper.validate_control_plane(active_env), Path(active_env["USER_ACTIVATION_READINESS_OUTPUT"]))
                for key, value in (("ENV", "dev"), ("TARGET_DB", "other"), ("PROD_READONLY_VERIFY", "0")):
                    invalid = {**active_env, key: value}
                    with self.assertRaises(helper.ActivationReadinessError):
                        helper.validate_control_plane(invalid)

    def test_output_is_new_direct_child_bound_to_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with mock.patch.object(helper, "EVIDENCE_ROOT", root):
                active_env = self.valid_env(root)
                Path(active_env["USER_ACTIVATION_READINESS_OUTPUT"]).write_text("existing")
                with self.assertRaises(helper.ActivationReadinessError):
                    helper.validate_control_plane(active_env)
                invalid = {**active_env, "USER_ACTIVATION_READINESS_OUTPUT": str(root / "nested" / "report.json")}
                with self.assertRaises(helper.ActivationReadinessError):
                    helper.validate_control_plane(invalid)

    def test_ready_decision_contains_only_aggregates(self):
        report = helper.evaluate(self.ready_snapshot(), run_id="20260801T010203Z-a1b2c3")
        self.assertEqual(report["status"], "READY_FOR_PILOT_SELECTION")
        self.assertEqual(report["blockers"], [])
        self.assertFalse(report["privacy"]["identity_values_recorded"])
        self.assertEqual(report["write_audit"]["database_write_statement_count"], 0)
        serialized = str(report).lower()
        for forbidden in ("login", "password", "activation_token", "email", "phone"):
            self.assertNotIn(forbidden, serialized)

    def test_missing_admin_blocks_pilot(self):
        snapshot = self.ready_snapshot()
        snapshot["activation_admin_count"] = 0
        report = helper.evaluate(snapshot, run_id="20260801T010203Z-a1b2c3")
        self.assertEqual(report["status"], "NOT_READY")
        self.assertEqual(report["blockers"], ["activation_admin_available"])

    def test_source_sets_readonly_before_database_queries_and_has_no_mutator(self):
        source = HELPER_PATH.read_text(encoding="utf-8")
        self.assertLess(source.index('execute("SET TRANSACTION READ ONLY")'), source.index('search([("name", "=", "smart_core")'))
        for forbidden in (
            ".sudo().create(",
            ".sudo().write(",
            ".sudo().unlink(",
            "odoo_env.cr.commit(",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
