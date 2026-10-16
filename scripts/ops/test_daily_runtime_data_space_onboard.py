#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("daily_runtime_data_space_onboard.py")
SPEC = importlib.util.spec_from_file_location("daily_runtime_data_space_onboard", SCRIPT)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)

SHA = "91a220ab76f3f581b4a233b2774979b2023205da"


class PreflightTests(unittest.TestCase):
    def test_accepts_declared_inputs(self):
        module.preflight(SHA, "sc_demo", "sc-root", "platform_internal_demo", "sc-demo-main")

    def test_rejects_short_sha(self):
        with self.assertRaises(module.OnboardError):
            module.preflight("91a220ab", "sc_demo", "sc-root", "platform_internal_demo", "k")

    def test_rejects_unsafe_database(self):
        with self.assertRaises(module.OnboardError):
            module.preflight(SHA, "sc_demo; rm -rf /", "sc-root", "platform_internal_demo", "k")

    def test_rejects_unsafe_ssh_host(self):
        with self.assertRaises(module.OnboardError):
            module.preflight(SHA, "sc_demo", "sc-root; rm -rf /", "platform_internal_demo", "k")

    def test_rejects_unregistered_role_shape(self):
        with self.assertRaises(module.OnboardError):
            module.preflight(SHA, "sc_demo", "sc-root", "Platform Internal Demo", "k")


class ProgramTests(unittest.TestCase):
    def program(self, apply=True):
        return module.odoo_shell_program(
            role="platform_internal_demo", tenant_key="sc-demo-main", apply=apply)

    def test_program_uses_only_the_governed_onboarding_entries(self):
        program = self.program()
        for token in (
            "declare_environment_role",
            "onboard_environment_business_company",
            "enroll_data_space_identities",
        ):
            self.assertIn(token, program)
        compile(program, "<odoo-shell>", "exec")

    def test_program_never_writes_business_rows_or_bypasses_the_gate(self):
        lowered = self.program().lower()
        for forbidden in ("unlink()", "drop table", "truncate", "sudo().write", "access_rights",
                          "_sql_constraints", "token"):
            self.assertNotIn(forbidden, lowered)
        self.assertNotIn("cr.execute(", self.program())

    def test_plan_mode_never_applies(self):
        program = self.program(apply=False)
        self.assertIn('APPLY = False', program)
        self.assertIn("env.cr.rollback()", program)

    def test_apply_mode_declares_post_conditions(self):
        program = self.program(apply=True)
        for token in ("env.cr.commit()", "post_conditions", "operators_pending_enrollment_is_empty"):
            self.assertIn(token, program)


class MarkerTests(unittest.TestCase):
    def test_marker_payload_is_read_from_the_last_marker_line(self):
        text = "noise\n" + module.MARKER + json.dumps({"passed": True}) + "\ntail\n"
        self.assertEqual(module.marker_payload(text), {"passed": True})

    def test_marker_payload_is_none_without_a_marker(self):
        self.assertIsNone(module.marker_payload("nothing here"))

    def test_unreadable_payload_is_refused(self):
        with self.assertRaises(module.OnboardError):
            module.marker_payload(module.MARKER + "{not json}")

class DutyBindingTests(unittest.TestCase):
    """A database *name* stops being a target identity once two carriers share it."""

    instances = Path(__file__).with_name("synthetic_duty_instances.sample.json")

    def reader(self, _path: str) -> str:
        return self.instances.read_text(encoding="utf-8")

    def options(self, **overrides):
        options = mock.Mock()
        options.duty = ""
        options.database = "sc_demo"
        options.ssh_host = "sc-root"
        for key, value in overrides.items():
            setattr(options, key, value)
        return options

    def test_a_bare_database_name_no_longer_binds_a_carrier(self) -> None:
        with self.assertRaisesRegex(
            module.OnboardError, "DUTY_IDENTITY_DATABASE_AMBIGUOUS:sc_demo"
        ):
            module.bind_target(self.options(), instances_reader=self.reader)

    def test_naming_the_duty_binds_the_rebuilt_demo_carrier(self) -> None:
        binding = module.bind_target(self.options(duty="demo"), instances_reader=self.reader)
        self.assertEqual(binding["database"], "sc_demo")
        self.assertEqual(binding["compose_project"], "sc-demo-dev")
        self.assertEqual(binding["odoo_container"], "sc-demo-dev-odoo-1")

    def test_the_shell_runs_in_the_bound_duty_container(self) -> None:
        captured = {}

        def fake_run(command, **kwargs):
            captured["command"] = command
            import subprocess
            return subprocess.CompletedProcess(command, 0, b"", b"")

        binding = module.bind_target(self.options(duty="demo"), instances_reader=self.reader)
        original = module.run
        module.run = fake_run
        try:
            module.remote_shell("sc-root", binding, stdin_path="/tmp/x.py")
        finally:
            module.run = original
        command = captured["command"]
        self.assertEqual(command[0], "ssh")
        self.assertIn("sc-root", command)
        self.assertIn("docker exec -i sc-demo-dev-odoo-1", command[-1])
        self.assertIn("-d sc_demo", command[-1])
        self.assertNotIn("ENV_FILE", command[-1])


if __name__ == "__main__":
    unittest.main()
