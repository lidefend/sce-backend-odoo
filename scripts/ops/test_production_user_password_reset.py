#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import io
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

        def fake_prompt(label, *, stream):
            calls.append((label, stream))
            return next(supplied)

        tty = io.StringIO()
        value = helper.prompt_password("wutao", tty=tty, prompt=fake_prompt)
        self.assertEqual(value, "safe-password-42")
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(stream is tty for _label, stream in calls))

    def test_prompt_rejects_mismatch(self):
        supplied = iter(("safe-password-42", "safe-password-43"))
        with self.assertRaises(helper.PasswordResetError):
            helper.prompt_password(
                "wutao",
                tty=io.StringIO(),
                prompt=lambda _label, *, stream: next(supplied),
            )

    def test_script_has_no_password_transport_or_direct_sql(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('open("/dev/tty", "r+"', source)
        self.assertIn('target.write({"password": password})', source)
        self.assertNotIn("os.environ.get(\"PASSWORD", source)
        self.assertNotIn("add_argument(\"--password", source)
        self.assertNotIn(".execute(", source)
        self.assertNotIn("UPDATE res_users", source)


if __name__ == "__main__":
    unittest.main()
