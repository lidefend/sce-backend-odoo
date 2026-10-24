"""Lock the fixed-demo-credential confirmation used by the daily lane.

The daily acceptance profile refuses known default passwords unless a
short-lived, identity-bound confirmation is presented. The owner fixed the
internal demo credential, so the governed make lane derives that confirmation
from ``config/acceptance/daily_demo_credential.v1.json``. These tests keep the
derivation narrow: only the declared login, tool and read-only operation pass,
and only when the supplied password is exactly the declared fixed one.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "scripts" / "verify" / "daily_demo_credential_confirmation.py"
DECLARATION = ROOT / "config" / "acceptance" / "daily_demo_credential.v1.json"
MAKEFILE = ROOT / "make" / "frontend.mk"


def load_helper():
    spec = importlib.util.spec_from_file_location("daily_demo_credential_confirmation", HELPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FixedDemoCredentialTest(unittest.TestCase):
    def setUp(self):
        self.helper = load_helper()
        self.declaration = json.loads(DECLARATION.read_text(encoding="utf-8"))

    def build(self, **overrides):
        arguments = {
            "base_url": "http://1.95.85.92:18081/t/demo",
            "login": self.declaration["login"],
            "expected_sha": "e" * 40,
            "tool": "geometry-scroll-audit",
            "run_id": "unit-run",
            "password": self.declaration["password"],
        }
        arguments.update(overrides)
        return self.helper.build_confirmation(self.declaration, **arguments)

    def test_declares_one_fixed_demo_identity(self):
        self.assertEqual(self.declaration["schema"], "daily_demo_credential.v1")
        self.assertEqual(self.declaration["profile"], "daily")
        self.assertEqual(self.declaration["operation"], "readonly")
        self.assertEqual(self.declaration["login"], "fixture_role_config_admin")
        self.assertIn("demo_full", self.declaration["additional_logins"])
        self.assertIn("sc_test_admin", self.declaration["additional_logins"])
        self.assertIn("2026-10-19", self.declaration["owner_ruling"]["date"])

    def test_confirmation_is_identity_bound_and_short_lived(self):
        confirmation = self.build()
        self.assertEqual(confirmation["schema"], "daily-readonly-credential-confirmation.v1")
        self.assertEqual(confirmation["profile"], "daily")
        self.assertEqual(confirmation["operation"], "readonly")
        self.assertEqual(confirmation["database"], "sc_demo")
        self.assertEqual(confirmation["runId"], "unit-run")
        expires = confirmation["expiresAt"]
        self.assertTrue(expires.endswith("Z"))
        business_full = self.build(login="demo_full")
        self.assertEqual(business_full["login"], "demo_full")

    def test_refuses_other_login_tool_or_password(self):
        with self.assertRaises(self.helper.ConfirmationError):
            self.build(login="admin")
        with self.assertRaises(self.helper.ConfirmationError):
            self.build(tool="unlisted-readonly-tool")
        with self.assertRaises(self.helper.ConfirmationError):
            self.build(password="another-password")
        with self.assertRaises(self.helper.ConfirmationError):
            self.build(expected_sha="")

    def test_relation_roundtrip_is_explicitly_read_only(self):
        confirmation = self.build(tool="relation-roundtrip", login="demo_full")
        self.assertEqual(confirmation["operation"], "readonly")
        self.assertEqual(confirmation["tool"], "relation-roundtrip")
        self.assertEqual(confirmation["database"], "sc_demo")

    def test_cli_emits_json_only_for_the_declared_credential(self):
        environment = dict(os.environ)
        environment["ACCEPTANCE_PASSWORD"] = self.declaration["password"]
        base = [
            sys.executable,
            str(HELPER),
            "--base-url",
            "http://1.95.85.92:18081/t/demo",
            "--login",
            self.declaration["login"],
            "--expected-sha",
            "e" * 40,
            "--tool",
            "geometry-scroll-audit",
            "--run-id",
            "cli-run",
        ]
        passed = subprocess.run(base, capture_output=True, text=True, env=environment)
        self.assertEqual(passed.returncode, 0, passed.stderr)
        document = json.loads(passed.stdout)
        self.assertEqual(document["runId"], "cli-run")
        environment["ACCEPTANCE_PASSWORD"] = "wrong-password"
        failed = subprocess.run(base, capture_output=True, text=True, env=environment)
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn("not the declared fixed demo password", failed.stderr)

    def test_governed_lane_derives_the_confirmation(self):
        makefile = MAKEFILE.read_text(encoding="utf-8")
        self.assertIn("verify.daily.demo_credential.confirmation", makefile)
        self.assertIn("daily_demo_credential_confirmation.py", makefile)
        self.assertIn("SC_ACCEPTANCE_DAILY_CREDENTIAL_CONFIRMATION", makefile)


if __name__ == "__main__":
    unittest.main()
