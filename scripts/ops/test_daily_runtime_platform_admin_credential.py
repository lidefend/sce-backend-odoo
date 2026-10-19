#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit coverage for the declared platform administrator credential entry.

The entry itself needs a host, a cluster and a rendered stack, so what is tested
here is everything that can be decided without them: the declaration grammar,
the fact assertions the entry refuses on, the receipt parser, and the two
properties that make the step safe -- the credential never becomes an argv
element, and a verification run can never write.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from scripts.ops import daily_runtime_platform_admin_credential as entry


def duty(**overrides) -> dict:
    base = {
        "duty": "platform_control",
        "database": "sc_platform_control",
        "data_purpose": "platform_control",
        "compose_project": "sc-platform-control-dev",
        "odoo_container": "sc-platform-control-dev-odoo-1",
        "admin_credential": {
            "login": "admin",
            "password_env": "SC_PLATFORM_ADMIN_PASSWORD",
            "purpose": "keep the platform administrator able to sign in",
        },
    }
    base.update(overrides)
    return base


class DeclarationGrammarTest(unittest.TestCase):
    def test_a_declared_credential_resolves(self):
        self.assertEqual(entry.declaration_error(duty()), "")
        self.assertEqual(entry.validate_declaration(duty())["login"], "admin")

    def test_a_duty_without_a_declaration_is_refused(self):
        error = entry.declaration_error(duty(admin_credential=None))
        self.assertIn("declares no", error)

    def test_a_non_object_declaration_is_refused(self):
        self.assertIn("non-empty object", entry.declaration_error(duty(admin_credential="admin")))

    def test_every_required_field_is_required(self):
        for field in entry.REQUIRED_FIELDS:
            declaration = {"login": "admin", "password_env": "SC_PLATFORM_ADMIN_PASSWORD",
                           "purpose": "why"}
            declaration.pop(field)
            error = entry.declaration_error(duty(admin_credential=declaration))
            self.assertIn(field, error, field)

    def test_an_unplain_login_is_refused(self):
        declaration = {"login": "admin; rm -rf /", "password_env": "SC_PLATFORM_ADMIN_PASSWORD",
                       "purpose": "why"}
        self.assertIn("plain login", entry.declaration_error(duty(admin_credential=declaration)))

    def test_a_non_governed_credential_key_is_refused(self):
        declaration = {"login": "admin", "password_env": "PASSWORD", "purpose": "why"}
        self.assertIn("governed environment key",
                      entry.declaration_error(duty(admin_credential=declaration)))

    def test_a_business_duty_may_not_carry_the_platform_credential(self):
        error = entry.declaration_error(duty(duty="demo", data_purpose="demo"))
        self.assertIn("not to a demo duty", error)


class ReportParsingTest(unittest.TestCase):
    def test_the_last_marked_receipt_wins(self):
        output = "\n".join([
            entry.MARKER + json.dumps({"login": "first"}),
            "noise",
            entry.MARKER + json.dumps({"login": "second"}),
        ])
        self.assertEqual(entry.marked_report(output)["login"], "second")

    def test_a_missing_receipt_is_refused(self):
        with self.assertRaises(entry.CredentialEntryError):
            entry.marked_report("no receipt here")

    def test_a_non_json_receipt_is_refused(self):
        with self.assertRaises(entry.CredentialEntryError):
            entry.marked_report(entry.MARKER + "{not json")

    def test_a_non_object_receipt_is_refused(self):
        with self.assertRaises(entry.CredentialEntryError):
            entry.marked_report(entry.MARKER + "[]")


class VerdictTest(unittest.TestCase):
    declaration = {"login": "admin", "password_env": "SC_PLATFORM_ADMIN_PASSWORD"}

    def report(self, **overrides) -> dict:
        base = {"login": "admin", "matched": 1, "active": True,
                "authenticated": True, "result": "unchanged", "writes": 0}
        base.update(overrides)
        return base

    def test_an_unchanged_reconcile_passes(self):
        verdict = entry.verdict("ensure", self.report(), self.declaration)
        self.assertEqual(verdict["result"], "unchanged")
        self.assertEqual(verdict["writes"], 0)

    def test_an_applied_reconcile_passes(self):
        verdict = entry.verdict("ensure", self.report(result="applied", writes=1), self.declaration)
        self.assertEqual(verdict["result"], "applied")
        self.assertEqual(verdict["writes"], 1)

    def test_a_verification_run_that_writes_is_refused(self):
        with self.assertRaises(entry.CredentialEntryError):
            entry.verdict("verify", self.report(result="applied", writes=1), self.declaration)

    def test_a_mismatch_is_never_reported_as_success(self):
        with self.assertRaises(entry.CredentialEntryError):
            entry.verdict("ensure", self.report(result="mismatch"), self.declaration)

    def test_a_refused_result_is_never_reported_as_success(self):
        with self.assertRaises(entry.CredentialEntryError):
            entry.verdict("ensure", self.report(result="refused"), self.declaration)

    def test_an_inactive_or_ambiguous_login_is_refused(self):
        with self.assertRaises(entry.CredentialEntryError):
            entry.verdict("ensure", self.report(active=False), self.declaration)
        with self.assertRaises(entry.CredentialEntryError):
            entry.verdict("ensure", self.report(matched=2), self.declaration)

    def test_an_unauthenticated_credential_is_refused(self):
        with self.assertRaises(entry.CredentialEntryError):
            entry.verdict("ensure", self.report(authenticated=False), self.declaration)

    def test_another_login_is_refused(self):
        with self.assertRaises(entry.CredentialEntryError):
            entry.verdict("ensure", self.report(login="somebody"), self.declaration)


class SafetyTest(unittest.TestCase):
    def test_the_credential_never_becomes_an_argument(self):
        declaration = {"login": "admin", "password_env": "SC_PLATFORM_ADMIN_PASSWORD"}
        command = entry.command_for(duty(), Path("/ops"), Path("/ops/sc-platform-control-dev.env"),
                                    Path("/ops/duty-stack.yml"), declaration)
        self.assertIn("SC_PLATFORM_ADMIN_PASSWORD", command)
        self.assertFalse([item for item in command if "=" in item and item.startswith("SC_")],
                         "a credential key must be forwarded by name, never by value")
        self.assertIn(entry.MODE_ENV, command)
        self.assertIn(entry.LOGIN_ENV, command)


class SeedTest(unittest.TestCase):
    """Seeding records the operator's value once; it never mints or rotates it."""

    def path(self, root):
        return Path(root) / "platform_control.env"

    def test_a_first_seed_creates_a_private_file(self):
        with tempfile.TemporaryDirectory() as root:
            result = entry.seed_declaration(duty(), Path(root), "admin", replace=False)
            path = self.path(root)
            text = path.read_text()
            mode = os.stat(path).st_mode & 0o777
        self.assertTrue(result["seeded"])
        self.assertFalse(result["replaced"])
        self.assertEqual(mode, 0o600)
        self.assertIn("SC_PLATFORM_ADMIN_PASSWORD=admin", text)

    def test_the_same_value_is_unchanged(self):
        with tempfile.TemporaryDirectory() as root:
            entry.seed_declaration(duty(), Path(root), "admin", replace=False)
            result = entry.seed_declaration(duty(), Path(root), "admin", replace=False)
        self.assertFalse(result["seeded"])

    def test_a_different_value_needs_the_explicit_replacement(self):
        with tempfile.TemporaryDirectory() as root:
            entry.seed_declaration(duty(), Path(root), "admin", replace=False)
            with self.assertRaises(entry.CredentialEntryError):
                entry.seed_declaration(duty(), Path(root), "changed", replace=False)
            result = entry.seed_declaration(duty(), Path(root), "changed", replace=True)
            text = self.path(root).read_text()
        self.assertTrue(result["replaced"])
        self.assertIn("SC_PLATFORM_ADMIN_PASSWORD=changed", text)
        self.assertNotIn("SC_PLATFORM_ADMIN_PASSWORD=admin", text)

    def test_the_seed_preserves_other_environment_lines(self):
        with tempfile.TemporaryDirectory() as root:
            path = self.path(root)
            path.write_text("DB_NAME=sc_platform_control\nDB_PASSWORD=%s\n" % ("a" * 64,))
            os.chmod(path, 0o600)
            entry.seed_declaration(duty(), Path(root), "admin", replace=False)
            text = path.read_text()
        self.assertIn("DB_NAME=sc_platform_control", text)
        self.assertIn("DB_PASSWORD=%s" % ("a" * 64,), text)

    def test_a_file_with_the_wrong_mode_is_refused(self):
        with tempfile.TemporaryDirectory() as root:
            path = self.path(root)
            path.write_text("DB_NAME=sc_platform_control\n")
            os.chmod(path, 0o644)
            with self.assertRaises(entry.CredentialEntryError):
                entry.seed_declaration(duty(), Path(root), "admin", replace=False)

    def test_an_empty_or_multiline_value_is_refused(self):
        with tempfile.TemporaryDirectory() as root:
            for value in ("", "a\nb"):
                with self.assertRaises(entry.CredentialEntryError):
                    entry.seed_declaration(duty(), Path(root), value, replace=False)

    def test_verification_uses_the_target_users_own_environment(self):
        program = entry.PROGRAM
        self.assertIn("Environment(env.cr, record.id, {})", program)
        self.assertIn('{"interactive": False}', program)

    def test_the_program_checks_before_it_writes(self):
        program = entry.PROGRAM
        check = program.index("_check_credentials")
        write = program.index('user.write({"password": password})')
        self.assertLess(check, write)
        self.assertLess(program.index('mode != "ensure"'), write)

    def test_the_program_never_prints_the_credential(self):
        program = entry.PROGRAM
        for line in program.splitlines():
            if "print(" in line:
                self.assertNotIn("password,", line)
                self.assertNotIn("+ password", line)
                self.assertNotIn("password +", line)

    def test_ensure_requires_an_exact_confirmation(self):
        with self.assertRaises(entry.CredentialEntryError):
            entry.execute("ensure", None)


if __name__ == "__main__":
    unittest.main()
