#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
HELPER_PATH = ROOT / "scripts/release/production_public_signup_close.py"
SPEC = importlib.util.spec_from_file_location("production_public_signup_close", HELPER_PATH)
assert SPEC and SPEC.loader
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)


class ProductionPublicSignupCloseTests(unittest.TestCase):
    def valid_env(self, root: Path, mode: str) -> dict[str, str]:
        deployed = root / ("a" * 40)
        script = deployed / "scripts/release/production_public_signup_close.py"
        script.parent.mkdir(parents=True)
        script.write_bytes(HELPER_PATH.read_bytes())
        (deployed / "DEPLOYMENT_TOOL_SHA").write_text("a" * 40 + "\n")
        active = {
            "ENV": "prod", "TARGET_DB": helper.TARGET_DATABASE, "TARGET_TAG": helper.TARGET_TAG,
            "TARGET_COMMIT": helper.TARGET_COMMIT, "REGISTRY_DIGEST": helper.TARGET_DIGEST,
            "DEPLOYMENT_ID": helper.DEPLOYMENT_ID, "PUBLIC_SIGNUP_CLOSE_MODE": mode,
            "PUBLIC_SIGNUP_CLOSE_RUN_ID": "20260801T010203Z-a1b2c3",
            "PUBLIC_SIGNUP_CLOSE_OUTPUT": str(root / f"public-signup-close-20260801T010203Z-a1b2c3-{mode}.json"),
            "PUBLIC_SIGNUP_CLOSE_TOOL_SOURCE_SHA": "a" * 40,
            "PUBLIC_SIGNUP_CLOSE_DEPLOYED_PATH": str(deployed),
            "PUBLIC_SIGNUP_CLOSE_SCRIPT_SHA256": helper.hashlib.sha256(script.read_bytes()).hexdigest(),
            "PROD_READONLY_VERIFY": "1",
        }
        if mode == "apply":
            active.update({"PROD_DANGER": "1", "CONFIRM_PUBLIC_SIGNUP_CLOSE": helper.CONFIRMATION})
        return active

    def test_exact_control_plane_and_immutable_tool_are_required(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with mock.patch.object(helper, "EVIDENCE_ROOT", root), mock.patch.object(helper, "DEPLOYMENT_ROOT", root):
                mode, output, binding = helper.validate_control_plane(self.valid_env(root, "plan"))
                self.assertEqual((mode, output.parent, binding["source_sha"]), ("plan", root, "a" * 40))

    def test_all_frozen_values_and_confirmation_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with mock.patch.object(helper, "EVIDENCE_ROOT", root), mock.patch.object(helper, "DEPLOYMENT_ROOT", root):
                active = self.valid_env(root, "apply")
                for key in ("ENV", "TARGET_DB", "TARGET_TAG", "TARGET_COMMIT", "REGISTRY_DIGEST", "DEPLOYMENT_ID", "CONFIRM_PUBLIC_SIGNUP_CLOSE"):
                    with self.assertRaises(helper.PublicSignupCloseError, msg=key):
                        helper.validate_control_plane({**active, key: "wrong"})

    def test_source_has_exactly_one_allowlisted_mutation(self):
        source = HELPER_PATH.read_text()
        self.assertEqual(source.count("params.set_param(PARAMETER, TARGET_VALUE)"), 1)
        for forbidden in (".sudo().create(", ".sudo().unlink(", 'write({"login"', 'write({"password"', 'cr.execute("UPDATE', 'cr.execute("INSERT', 'cr.execute("DELETE'):
            self.assertNotIn(forbidden, source)

    def test_plan_is_one_parameter_and_zero_everything_else(self):
        source = HELPER_PATH.read_text()
        self.assertIn('PARAMETER = "auth_signup.invitation_scope"', source)
        self.assertIn('CURRENT_VALUE = "b2c"', source)
        self.assertIn('TARGET_VALUE = "b2b"', source)
        self.assertIn('"parameter_rows": 1', source)
        for key in ("activation_credential_rows", "normal_user_rows", "password_rows", "login_rows", "user_group_rows", "company_scope_rows", "business_data_rows", "other_rows"):
            self.assertIn(f'"{key}": 0', source)

    def test_negative_probe_is_get_only_and_requires_denial(self):
        source = HELPER_PATH.read_text()
        self.assertIn('method="GET"', source)
        self.assertIn("status not in {403, 404}", source)
        self.assertNotIn('method="POST"', source)


if __name__ == "__main__":
    unittest.main()
