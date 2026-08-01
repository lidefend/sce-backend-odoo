#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
HELPER_PATH = ROOT / "scripts/release/production_user_activation_predeploy.py"
SPEC = importlib.util.spec_from_file_location(
    "production_user_activation_predeploy", HELPER_PATH
)
assert SPEC and SPEC.loader
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)


class ProductionUserActivationPredeployTests(unittest.TestCase):
    def valid_env(self, root: Path, mode: str = "plan") -> dict[str, str]:
        deployed = root / ("a" * 40)
        script = deployed / "scripts/release/production_user_activation_predeploy.py"
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_bytes(HELPER_PATH.read_bytes())
        (deployed / "DEPLOYMENT_TOOL_SHA").write_text("a" * 40 + "\n")
        active = {
            "ENV": "prod",
            "TARGET_DB": helper.TARGET_DATABASE,
            "TARGET_TAG": helper.TARGET_TAG,
            "TARGET_COMMIT": helper.TARGET_COMMIT,
            "REGISTRY_DIGEST": helper.TARGET_DIGEST,
            "DEPLOYMENT_ID": helper.DEPLOYMENT_ID,
            "ACTIVATION_ADMIN_LOGIN": helper.TARGET_ADMIN_LOGIN,
            "TENANT_KEY": "tenant_prod",
            "USER_ACTIVATION_PREDEPLOY_MODE": mode,
            "USER_ACTIVATION_PREDEPLOY_RUN_ID": "20260801T010203Z-a1b2c3",
            "USER_ACTIVATION_PREDEPLOY_OUTPUT": str(
                root / f"user-activation-predeploy-20260801T010203Z-a1b2c3-{mode}.json"
            ),
            "USER_ACTIVATION_PREDEPLOY_TOOL_SOURCE_SHA": "a" * 40,
            "USER_ACTIVATION_PREDEPLOY_DEPLOYED_PATH": str(deployed),
            "USER_ACTIVATION_PREDEPLOY_SCRIPT_SHA256": helper.hashlib.sha256(
                script.read_bytes()
            ).hexdigest(),
            "PROD_READONLY_VERIFY": "1",
        }
        if mode == "apply":
            active.update(
                {
                    "PROD_DANGER": "1",
                    "CONFIRM_USER_ACTIVATION_PREDEPLOY": helper.CONFIRMATION,
                }
            )
        return active

    def test_control_plane_binds_exact_release_database_and_tool(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with mock.patch.object(helper, "EVIDENCE_ROOT", root), mock.patch.object(
                helper, "DEPLOYMENT_ROOT", root
            ):
                mode, output, binding = helper.validate_control_plane(
                    self.valid_env(root)
                )
                self.assertEqual(mode, "plan")
                self.assertEqual(output.parent, root)
                self.assertEqual(binding["source_sha"], "a" * 40)

    def test_every_frozen_identity_and_apply_confirmation_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with mock.patch.object(helper, "EVIDENCE_ROOT", root), mock.patch.object(
                helper, "DEPLOYMENT_ROOT", root
            ):
                active = self.valid_env(root, "apply")
                for key in (
                    "ENV",
                    "TARGET_DB",
                    "TARGET_TAG",
                    "TARGET_COMMIT",
                    "REGISTRY_DIGEST",
                    "DEPLOYMENT_ID",
                    "ACTIVATION_ADMIN_LOGIN",
                    "CONFIRM_USER_ACTIVATION_PREDEPLOY",
                ):
                    invalid = {**active, key: "wrong"}
                    with self.assertRaises(helper.ActivationPredeployError, msg=key):
                        helper.validate_control_plane(invalid)

    def test_plan_digest_excludes_transaction_mode_but_not_target_state(self):
        plan = {
            "transaction": {"verification": "PASS"},
            "parameters": [{"name": helper.TENANT_PARAMETER, "target": "tenant_prod"}],
        }
        first = helper._plan_digest(plan)
        plan["transaction"] = {"verification": "APPLY_AUTHORIZED"}
        self.assertEqual(helper._plan_digest(plan), first)
        plan["parameters"][0]["target"] = "other"
        self.assertNotEqual(helper._plan_digest(plan), first)

    def test_source_contains_only_three_allowlisted_mutation_calls(self):
        source = HELPER_PATH.read_text(encoding="utf-8")
        self.assertEqual(source.count("config.set_param("), 2)
        self.assertEqual(source.count('target.write({"groups_id"'), 1)
        for forbidden in (
            ".create(",
            ".sudo().unlink(",
            'write({"login"',
            'write({"password"',
            "odoo_env.cr.execute(\"UPDATE",
            "odoo_env.cr.execute(\"INSERT",
            "odoo_env.cr.execute(\"DELETE",
        ):
            self.assertNotIn(forbidden, source)

    def test_readonly_is_established_before_any_orm_query(self):
        source = HELPER_PATH.read_text(encoding="utf-8")
        self.assertLess(
            source.index("_enable_read_only(odoo_env)"),
            source.index("_plan(odoo_env, tenant_key, transaction)"),
        )

    def test_capability_failure_diagnostics_are_complete_and_non_secret(self):
        source = HELPER_PATH.read_text(encoding="utf-8")
        for key in (
            "ACTIVATION_CREDENTIAL_MODEL_PRESENT",
            "ENTERPRISE_ACTIVATION_PURPOSE_PRESENT",
            "DIGEST_ONLY_TOKEN_STORAGE_PRESENT",
            "TOKEN_SINGLE_USE_ENFORCED",
            "TOKEN_TTL_HOURS",
            "TENANT_BINDING_SUPPORTED",
            "ENVIRONMENT_BINDING_SUPPORTED",
            "ACTIVATION_ADMIN_GROUP_XMLID",
            "ACTIVATION_RUNTIME_PARAMETER_NAMES",
            "SIGNUP_RESET_POLICY_ISOLATION_PRESENT",
            "PUBLIC_SIGNUP_ENABLED",
            "PRODUCTION_DATABASE_PUBLIC_REGISTRATION",
        ):
            self.assertIn(f'"{key}"', source)
        diagnostic = source.split("public_checks =", 1)[1].split(
            "raise ActivationPredeployError", 1
        )[0].lower()
        for forbidden in ("login", "password", "token_digest", "tenant_key"):
            self.assertNotIn(forbidden, diagnostic)

    def test_roster_drift_diagnostics_report_only_aggregate_counts(self):
        source = HELPER_PATH.read_text(encoding="utf-8")
        diagnostic = source.split('"62/76 approved-roster assertion differs "', 1)[1].split(
            '"identity_values_recorded": False', 1
        )[0]
        for key in (
            "APPROVED_FORMAL_USERS_EXPECTED",
            "APPROVED_FORMAL_USERS_OBSERVED",
            "TECHNICALLY_ELIGIBLE_USERS_TOTAL_EXPECTED",
            "TECHNICALLY_ELIGIBLE_USERS_TOTAL_OBSERVED",
            "ADDITIONAL_ELIGIBLE_USERS_EXPECTED",
            "ADDITIONAL_ELIGIBLE_USERS_OBSERVED",
        ):
            self.assertIn(key, diagnostic)
        for forbidden in ("name", "login", "password", "token", "tenant_key"):
            self.assertNotIn(forbidden, diagnostic.lower())


if __name__ == "__main__":
    unittest.main()
