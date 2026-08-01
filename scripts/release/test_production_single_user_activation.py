#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
HELPER_PATH = ROOT / "scripts/release/production_single_user_activation.py"
SPEC = importlib.util.spec_from_file_location("production_single_user_activation", HELPER_PATH)
assert SPEC and SPEC.loader
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)


class ProductionSingleUserActivationTests(unittest.TestCase):
    def valid_env(self, root: Path, mode: str) -> dict[str, str]:
        deployed = root / ("a" * 40)
        script = deployed / "scripts/release/production_single_user_activation.py"
        script.parent.mkdir(parents=True)
        script.write_bytes(HELPER_PATH.read_bytes())
        (deployed / "DEPLOYMENT_TOOL_SHA").write_text("a" * 40 + "\n")
        active = {
            "ENV": "prod",
            "TARGET_DB": helper.TARGET_DATABASE,
            "TARGET_TAG": helper.TARGET_TAG,
            "TARGET_COMMIT": helper.TARGET_COMMIT,
            "REGISTRY_DIGEST": helper.TARGET_DIGEST,
            "DEPLOYMENT_ID": helper.DEPLOYMENT_ID,
            "TENANT_KEY": "tenantalpha",
            "SINGLE_USER_ACTIVATION_LOGIN": helper.TARGET_LOGIN,
            "ACTIVATION_ADMIN_LOGIN": helper.TARGET_ADMIN_LOGIN,
            "ACTIVATION_PUBLIC_URL": "https://example.invalid/activate-account",
            "SINGLE_USER_ACTIVATION_MODE": mode,
            "SINGLE_USER_ACTIVATION_RUN_ID": "20260801T010203Z-wutao01r",
            "SINGLE_USER_ACTIVATION_OUTPUT": str(root / f"single-user-activation-20260801T010203Z-wutao01r-{mode}.json"),
            "SINGLE_USER_ACTIVATION_TOOL_SOURCE_SHA": "a" * 40,
            "SINGLE_USER_ACTIVATION_DEPLOYED_PATH": str(deployed),
            "SINGLE_USER_ACTIVATION_SCRIPT_SHA256": helper.hashlib.sha256(script.read_bytes()).hexdigest(),
            "PROD_READONLY_VERIFY": "1",
        }
        if mode == "apply":
            active.update({"PROD_DANGER": "1", "CONFIRM_SINGLE_USER_ACTIVATION": helper.CONFIRMATION})
        return active

    def test_exact_control_plane_and_immutable_tool_are_required(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with mock.patch.object(helper, "EVIDENCE_ROOT", root), mock.patch.object(helper, "DEPLOYMENT_ROOT", root):
                mode, output, binding = helper.validate_control_plane(self.valid_env(root, "plan"))
                self.assertEqual((mode, output.parent, binding["source_sha"]), ("plan", root, "a" * 40))

    def test_every_frozen_identity_and_confirmation_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with mock.patch.object(helper, "EVIDENCE_ROOT", root), mock.patch.object(helper, "DEPLOYMENT_ROOT", root):
                active = self.valid_env(root, "apply")
                for key in ("ENV", "TARGET_DB", "TARGET_TAG", "TARGET_COMMIT", "REGISTRY_DIGEST", "DEPLOYMENT_ID", "TENANT_KEY", "SINGLE_USER_ACTIVATION_LOGIN", "ACTIVATION_ADMIN_LOGIN", "ACTIVATION_PUBLIC_URL", "CONFIRM_SINGLE_USER_ACTIVATION"):
                    with self.assertRaises(helper.SingleUserActivationError, msg=key):
                        helper.validate_control_plane({**active, key: "" if key == "TENANT_KEY" else "wrong"})

    def test_source_is_single_user_and_never_outputs_plaintext(self):
        source = HELPER_PATH.read_text()
        self.assertIn('TARGET_LOGIN = "wutao"', source)
        self.assertIn('TTL_HOURS = 24', source)
        self.assertIn('issued.pop("activation_token")', source)
        self.assertNotIn('print(raw_token)', source)
        self.assertNotIn('"activation_token": raw_token', source)
        self.assertNotIn('write({"login"', source)
        self.assertNotIn('write({"password"', source)
        self.assertNotIn('cr.execute("UPDATE', source)

    def test_write_plan_matches_explicit_ceiling(self):
        source = HELPER_PATH.read_text()
        for fragment in (
            '"activation_runtime_parameter_rows": parameter_writes',
            '"activation_admin_group_relation_rows": group_writes',
            '"wutao_active_state_rows": active_writes',
            '"wutao_activation_credential_rows": 1',
            '"other_user_rows": 0',
            '"login_rows": 0',
            '"role_rows": 0',
            '"company_scope_rows": 0',
            '"business_data_rows": 0',
        ):
            self.assertIn(fragment, source)


if __name__ == "__main__":
    unittest.main()
