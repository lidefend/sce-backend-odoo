#!/usr/bin/env python3
from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import production_promotion_config_preflight as preflight


class ProductionPromotionConfigPreflightTest(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = preflight.load_contract(preflight.DEFAULT_CONTRACT)
        self.config = {
            "PROMOTION_ENVIRONMENT": "production",
            "SC_BOOTSTRAP_LOGIN": "formal-readonly-operator",
            "ACCEPTANCE_BASE_URL": "http://127.0.0.1:18088",
            "DB_NAME": "sc_production",
            "ACCEPTANCE_CONTRACT_PATH": (
                "scripts/ops/production_acceptance_contract_v1.json"
            ),
            "ACCEPTANCE_PACKAGE_DIGEST": self.contract[
                "acceptance_package_digest"
            ],
            "ACCEPTANCE_HTTP_TIMEOUT": "30",
            "ACCEPTANCE_TLS_VERIFY": "false",
            "ACCEPTANCE_PRODUCT_KEY": "sce-product",
            "ACCEPTANCE_EXPECTED_ROLE_CODE": "business_config_admin",
            "DEPLOYMENT_IMAGE_REF": self.contract["fixed_deployment_image_id"],
        }
        self.secrets = {"FORMAL_ACCEPTANCE_PASSWORD": "not-serialized"}
        self.http_pass = {
            "status": "PASS",
            "run_count": 2,
            "runs": [
                {
                    "login_pass": True,
                    "system_init_pass": True,
                    "core_read_acceptance_pass": True,
                }
            ],
        }

    def evaluate(self, config: dict[str, str], secrets: dict[str, str]):
        with mock.patch.object(
            preflight.acceptance, "run_acceptance", return_value=self.http_pass
        ):
            return preflight.evaluate(
                contract=self.contract,
                config_values=config,
                secret_values=secrets,
                run_http=True,
                run_count=2,
                check_image=False,
                expected_environment="production",
            )

    def test_missing_undefined_empty_and_whitespace_login_fail_closed(self) -> None:
        for value in (None, "", "   "):
            with self.subTest(value=value):
                config = copy.deepcopy(self.config)
                if value is None:
                    config.pop("SC_BOOTSTRAP_LOGIN")
                else:
                    config["SC_BOOTSTRAP_LOGIN"] = value
                report = self.evaluate(config, self.secrets)
                self.assertEqual(report["status"], "PREDEPLOY_CONFIG_NOT_READY")
                self.assertIn("SC_BOOTSTRAP_LOGIN", report["missing_config_fields"])
                self.assertFalse(report["safe_to_replace_production_container"])
                self.assertFalse(report["production_container_replaced"])

    def test_placeholder_and_forbidden_login_fail_closed(self) -> None:
        for value in ("<SET_LOGIN>", "changeme", "admin", "demo", "bootstrap"):
            with self.subTest(value=value):
                config = copy.deepcopy(self.config)
                config["SC_BOOTSTRAP_LOGIN"] = value
                report = self.evaluate(config, self.secrets)
                fields = (
                    report["missing_config_fields"] + report["invalid_config_fields"]
                )
                self.assertIn("SC_BOOTSTRAP_LOGIN", fields)
                self.assertFalse(report["safe_to_replace_production_container"])

    def test_missing_secret_fails_without_serializing_secret(self) -> None:
        report = self.evaluate(self.config, {})
        self.assertIn("FORMAL_ACCEPTANCE_PASSWORD", report["missing_config_fields"])
        self.assertNotIn("not-serialized", str(report))
        self.assertFalse(report["secret_values_exposed"])

    def test_wrong_url_database_digest_and_role_fail_closed(self) -> None:
        mutations = {
            "PROMOTION_ENVIRONMENT": "daily",
            "ACCEPTANCE_BASE_URL": "http://127.0.0.1:18081",
            "DB_NAME": "sc_demo",
            "ACCEPTANCE_PACKAGE_DIGEST": "0" * 64,
            "ACCEPTANCE_EXPECTED_ROLE_CODE": "system_admin",
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                config = copy.deepcopy(self.config)
                config[field] = value
                report = self.evaluate(config, self.secrets)
                self.assertIn(field, report["invalid_config_fields"])
                self.assertFalse(report["safe_to_replace_production_container"])

    def test_complete_configuration_and_http_acceptance_pass(self) -> None:
        report = self.evaluate(self.config, self.secrets)
        self.assertEqual(report["status"], "PASS")
        self.assertTrue(report["promotion_config_contract_pass"])
        self.assertTrue(report["formal_login_current_production_pass"])
        self.assertTrue(report["production_system_init_preflight_pass"])
        self.assertTrue(report["production_core_read_preflight_pass"])
        self.assertEqual(report["repeated_clean_session_run_count"], 2)
        self.assertTrue(report["safe_to_replace_production_container"])
        self.assertFalse(report["production_container_replaced"])
        self.assertFalse(report["production_write_performed"])

    def test_http_failure_is_redacted_and_fail_closed(self) -> None:
        with mock.patch.object(
            preflight.acceptance,
            "run_acceptance",
            side_effect=preflight.acceptance.AcceptanceError(
                "credential and token details must not escape"
            ),
        ):
            report = preflight.evaluate(
                contract=self.contract,
                config_values=self.config,
                secret_values=self.secrets,
                run_http=True,
                run_count=1,
                check_image=False,
                expected_environment="production",
            )
        self.assertEqual(report["status"], "PREDEPLOY_CONFIG_NOT_READY")
        self.assertEqual(
            report["failed_readiness_checks"], ["HTTP_ACCEPTANCE_FAILED"]
        )
        self.assertNotIn("credential", str(report))
        self.assertFalse(report["safe_to_replace_production_container"])

    def test_daily_uses_same_fields_with_environment_specific_values(self) -> None:
        config = copy.deepcopy(self.config)
        config.update(
            {
                "PROMOTION_ENVIRONMENT": "daily",
                "ACCEPTANCE_BASE_URL": "http://127.0.0.1:18081",
                "DB_NAME": "sc_demo",
            }
        )
        with mock.patch.object(
            preflight.acceptance, "run_acceptance", return_value=self.http_pass
        ):
            report = preflight.evaluate(
                contract=self.contract,
                config_values=config,
                secret_values=self.secrets,
                run_http=True,
                run_count=2,
                check_image=False,
                expected_environment="daily",
            )
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(
            set(report["required_config_fields"]),
            set(self.config) | set(self.secrets),
        )
        self.assertEqual(report["repeated_clean_session_run_count"], 2)

    def test_atomic_evidence_is_0600_and_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "evidence.json"
            preflight.atomic_json(output, {"status": "PASS"})
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(preflight.ReadinessError):
                preflight.atomic_json(output, {"status": "PASS"})


if __name__ == "__main__":
    unittest.main()
