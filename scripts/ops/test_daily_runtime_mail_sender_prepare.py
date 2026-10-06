#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("daily_runtime_mail_sender_prepare.py")
SPEC = importlib.util.spec_from_file_location("daily_runtime_mail_sender_prepare", SCRIPT)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)

SHA = "6c8e07f70c1ce0d501f9f5b56911d74f9321a721"
SENDER = "noreply@sc-daily.local"


class PreflightTests(unittest.TestCase):
    def test_accepts_declared_inputs(self):
        module.preflight(SHA, SENDER, "sc_demo", "sc-root")

    def test_rejects_short_sha(self):
        with self.assertRaises(module.PrepareError):
            module.preflight("6c8e07f", SENDER, "sc_demo", "sc-root")

    def test_rejects_non_address_sender(self):
        with self.assertRaises(module.PrepareError):
            module.preflight(SHA, "noreply", "sc_demo", "sc-root")

    def test_rejects_unsafe_database(self):
        with self.assertRaises(module.PrepareError):
            module.preflight(SHA, SENDER, "sc_demo; rm -rf /", "sc-root")

    def test_rejects_unsafe_ssh_host(self):
        with self.assertRaises(module.PrepareError):
            module.preflight(SHA, SENDER, "sc_demo", "sc-root; rm -rf /")


class ProgramTests(unittest.TestCase):
    def test_program_declares_sender_on_every_carrier(self):
        program = module.odoo_shell_program(SENDER)
        self.assertIn('SENDER = "noreply@sc-daily.local"', program)
        self.assertIn("ir.mail_server", program)
        self.assertIn("mail.default.from", program)
        self.assertIn("res.company", program)
        self.assertIn("env.cr.commit()", program)
        compile(program, "<odoo-shell>", "exec")

    def test_program_declares_author_address_for_unaddressed_accounts(self):
        program = module.odoo_shell_program(SENDER)
        self.assertIn("res.users", program)
        self.assertIn("user_domain = SENDER.split('@', 1)[1]", program)
        self.assertIn("users_still_without_email", program)
        self.assertIn("[('share', '=', False), ('active', '=', True)]", program)
        compile(program, "<odoo-shell>", "exec")

    def test_program_never_destroys_governed_state(self):
        program = module.odoo_shell_program(SENDER).lower()
        for forbidden in ("unlink()", "drop table", "truncate", "cr.execute("):
            self.assertNotIn(forbidden, program)


class CommandTests(unittest.TestCase):
    def test_remote_make_uses_the_governed_shell_entry(self):
        captured: dict[str, object] = {}

        class Result:
            returncode = 0
            stdout = b""
            stderr = b""

        def fake_run(command, input_bytes=None):
            captured["command"] = command
            return Result()

        original = module.run
        module.run = fake_run
        try:
            module.remote_make("sc-root", "sc_demo", "odoo.shell.exec", stdin_path="/tmp/x.py")
        finally:
            module.run = original
        rendered = " ".join(captured["command"])
        self.assertIn("make ENV=dev ENV_FILE=.env.dev DB_NAME=sc_demo odoo.shell.exec", rendered)
        self.assertIn("< /tmp/x.py", rendered)

    def test_confirmation_token_is_stable(self):
        self.assertEqual(module.CONFIRMATION, "PREPARE_DAILY_RUNTIME_OUTGOING_MAIL_SENDER")


if __name__ == "__main__":
    unittest.main()
