#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/ops/production_user_password_reset.py"
SPEC = importlib.util.spec_from_file_location("production_user_password_reset", SCRIPT)
assert SPEC and SPEC.loader
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)


class ProductionUserPasswordResetTests(unittest.TestCase):
    def test_request_is_exactly_production_and_login_is_safe(self):
        helper.validate_request(
            "sc_production", "wutao", {"ENV": "prod", "PROD_DANGER": "1"}
        )
        for database, login, active_env in (
            ("sc_demo", "wutao", {"ENV": "prod", "PROD_DANGER": "1"}),
            ("sc_production", "wutao;drop", {"ENV": "prod", "PROD_DANGER": "1"}),
            ("sc_production", "wutao", {"ENV": "dev", "PROD_DANGER": "1"}),
            ("sc_production", "wutao", {"ENV": "prod", "PROD_DANGER": "0"}),
        ):
            with self.assertRaises(helper.PasswordResetError):
                helper.validate_request(database, login, active_env)

    def test_password_policy_requires_length_letter_digit(self):
        helper.validate_password("safe-password-42", "wutao")
        for password in ("short42", "123456789012", "onlyletterslong", "wutao"):
            with self.assertRaises(helper.PasswordResetError):
                helper.validate_password(password, "wutao")

    def test_prompt_reads_twice_without_stdin_or_environment(self):
        supplied = iter(("safe-password-42", "safe-password-42"))
        calls = []

        def fake_prompt(label):
            calls.append(label)
            return next(supplied)

        value = helper.prompt_password("wutao", prompt=fake_prompt)
        self.assertEqual(value, "safe-password-42")
        self.assertEqual(len(calls), 2)

    def test_prompt_rejects_mismatch(self):
        supplied = iter(("safe-password-42", "safe-password-43"))
        with self.assertRaises(helper.PasswordResetError):
            helper.prompt_password(
                "wutao",
                prompt=lambda _label: next(supplied),
            )

    def test_script_has_no_password_transport_or_direct_sql(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("prompt: Callable[..., str] = getpass.getpass", source)
        self.assertNotIn("stream=", source)
        self.assertIn('target.write({"password": password})', source)
        self.assertNotIn("os.environ.get(\"PASSWORD", source)
        self.assertNotIn("add_argument(\"--password", source)
        self.assertNotIn(".execute(", source)
        self.assertNotIn("UPDATE res_users", source)
        self.assertNotIn("sc.runtime.tenant_key", source)
        self.assertNotIn("sc.tenant.payload.external.identity", source)
        self.assertIn('"model": "res.users"', source)
        self.assertIn('"record_id": target.id', source)
        self.assertIn('"TARGET_USER_RECORD_SHA256"', source)

    def test_unexpected_failures_are_reported_by_non_secret_stage(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for stage in (
            "odoo_bootstrap",
            "target_preflight",
            "password_prompt",
            "orm_password_reset",
            "http_verification",
        ):
            self.assertIn(stage, source)
        self.assertIn('f"{stage} failed ({type(exc).__name__})"', source)


if __name__ == "__main__":
    unittest.main()
