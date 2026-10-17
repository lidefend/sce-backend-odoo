#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("daily_runtime_mail_sender_prepare.py")
SPEC = importlib.util.spec_from_file_location("daily_runtime_mail_sender_prepare", SCRIPT)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)

SHA = "6c8e07f70c1ce0d501f9f5b56911d74f9321a721"
SENDER = "noreply@sc-daily.local"
DEMO_BINDING = {
    "duty": "demo",
    "database": "sc_demo",
    "compose_project": "sc-demo-dev",
    "odoo_container": "sc-demo-dev-odoo-1",
}


class Result:
    def __init__(self, returncode=0, stdout=b"", stderr=b""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


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


class DutyBindingTests(unittest.TestCase):
    """A database *name* stops being a target identity once two carriers share it.

    The refusal is read from the shipped declaration, not from a stub: it now
    names the rebuilt demo duty and the preserved pre-governance source with the
    same ``sc_demo``, so an entry that received only ``--database`` would
    otherwise configure whichever cluster happened to serve that name.
    """

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
        with self.assertRaisesRegex(module.PrepareError, "DUTY_IDENTITY_DATABASE_AMBIGUOUS:sc_demo"):
            module.bind_target(self.options(), instances_reader=self.reader)

    def test_naming_the_duty_binds_the_rebuilt_demo_carrier(self) -> None:
        binding = module.bind_target(self.options(duty="demo"), instances_reader=self.reader)
        self.assertEqual(binding["database"], "sc_demo")
        self.assertEqual(binding["compose_project"], "sc-demo-dev")
        self.assertEqual(binding["odoo_container"], "sc-demo-dev-odoo-1")

    def test_the_shell_runs_in_the_bound_duty_container(self) -> None:
        # A remembered project or environment file is how this entry used to
        # reach the pre-governance cluster that shares the database name.
        binding = module.bind_target(self.options(duty="demo"), instances_reader=self.reader)
        command = module.duty_identity.odoo_shell_command(binding, program_path="/tmp/x.py")
        self.assertIn("docker exec -i sc-demo-dev-odoo-1", command)
        self.assertIn("-d sc_demo", command)
        self.assertIn("< /tmp/x.py", command)
        self.assertNotIn("sc-backend-odoo-dev", command)
        self.assertNotIn("ENV_FILE", command)


class GuardTests(unittest.TestCase):
    """The read-only guard must prove the carrier the entry actually wrote.

    It used to be reached through the deployed checkout's
    ``make prod.guard.mail_from``, which resolves its target from a bare
    ``DB_NAME``.  A grep is not proof of correctness, so this drives the entry's
    own guard runner against stub transports and asserts what is sent.
    """

    def setUp(self):
        self._ssh = module.ssh
        self.calls = []
        self.addCleanup(self.restore)

    def restore(self):
        module.ssh = self._ssh

    def stub(self, *, guard_rc=0, guard_stderr=b""):
        def fake_ssh(host, command, *, input_bytes=None):
            self.calls.append({"host": host, "command": command, "program": input_bytes})
            if "docker exec" in command:
                return Result(returncode=guard_rc, stderr=guard_stderr)
            return Result()

        module.ssh = fake_ssh

    def test_guard_program_is_the_repository_guard_verbatim(self):
        self.stub()
        module.remote_guard("sc-root", DEMO_BINDING, remote_tmp="/tmp/guard.py")
        uploaded = [call for call in self.calls if call["program"]][0]
        self.assertEqual(uploaded["program"], module.GUARD_PROGRAM.read_bytes())

    def test_guard_runs_inside_the_bound_duty_container(self):
        self.stub()
        module.remote_guard("sc-root", DEMO_BINDING, remote_tmp="/tmp/guard.py")
        engine = [call for call in self.calls if "docker exec" in call["command"]][0]
        self.assertIn("docker exec -i sc-demo-dev-odoo-1", engine["command"])
        self.assertIn("-d sc_demo", engine["command"])
        self.assertIn("< /tmp/guard.py", engine["command"])
        self.assertNotIn("ENV_FILE", engine["command"])
        self.assertNotIn("make ", engine["command"])

    def test_the_uploaded_program_is_removed_afterwards(self):
        self.stub()
        module.remote_guard("sc-root", DEMO_BINDING, remote_tmp="/tmp/guard.py")
        self.assertIn("rm -f /tmp/guard.py", [call["command"] for call in self.calls][-1])

    def test_a_failing_guard_result_is_returned_not_swallowed(self):
        self.stub(guard_rc=2, guard_stderr=b"GUARD: FAIL\n")
        result = module.remote_guard("sc-root", DEMO_BINDING, remote_tmp="/tmp/guard.py")
        self.assertEqual(result.returncode, 2)
        self.assertIn("GUARD: FAIL", module.decode(result))

    def test_a_missing_guard_program_stops_the_run(self):
        with self.assertRaises(module.PrepareError):
            module.remote_guard("sc-root", DEMO_BINDING,
                                guard_program=Path("/nonexistent/guard.py"))

    def test_the_tool_never_routes_a_write_through_a_bare_database_name(self):
        source = Path(SCRIPT).read_text(encoding="utf-8")
        self.assertNotIn("remote_make", source)


class PrepareLandingTests(unittest.TestCase):
    """The entry must fail when the shell landed in the other carrier.

    The rebuilt demo duty and the preserved historic source both answer to
    ``sc_demo``; a preparation that silently ran against the historic cluster
    would be a write to a protected source.  A missing readback is treated the
    same as a wrong one.
    """

    def setUp(self):
        self._ssh = module.ssh
        self._served = module.served_identity
        self.calls = []
        self.engines = 0
        module.served_identity = lambda base_url: {}
        self.addCleanup(self.restore)

    def restore(self):
        module.ssh = self._ssh
        module.served_identity = self._served

    def stub(self, *, shell_stdout=b"", guard_rc=0, guard_stderr=b"GUARD: PASS\n"):
        def fake_ssh(host, command, *, input_bytes=None):
            self.calls.append({"host": host, "command": command, "program": input_bytes})
            if "git rev-parse HEAD" in command:
                return Result(stdout=(SHA + "\n").encode())
            if command.startswith("rm -f "):
                return Result()
            if "cat > " in command:
                return Result()
            if "docker exec" in command:
                # Both the preparation and the read-only guard run through the
                # bound container's odoo shell, so they are told apart by the
                # order the entry issues them.
                self.engines += 1
                if self.engines == 1:
                    return Result(stdout=shell_stdout)
                return Result(returncode=guard_rc, stderr=guard_stderr)
            return Result()

        module.ssh = fake_ssh

    def test_a_preparation_that_landed_in_the_bound_database_passes(self):
        self.stub(shell_stdout=b"PREPARE_MAIL_SENDER database=sc_demo\n")
        evidence = module.prepare(SHA, SENDER, DEMO_BINDING, "sc-root", "")
        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(evidence["landed_database"], "sc_demo")

    def test_a_preparation_that_landed_elsewhere_fails_closed(self):
        self.stub(shell_stdout=b"PREPARE_MAIL_SENDER database=sc_dev_demo\n")
        evidence = module.prepare(SHA, SENDER, DEMO_BINDING, "sc-root", "")
        self.assertEqual(evidence["status"], "FAIL")
        self.assertEqual(evidence["landed_database"], "sc_dev_demo")

    def test_a_preparation_without_a_readback_fails_closed(self):
        self.stub(shell_stdout=b"no marker here\n")
        evidence = module.prepare(SHA, SENDER, DEMO_BINDING, "sc-root", "")
        self.assertEqual(evidence["status"], "FAIL")
        self.assertEqual(evidence["landed_database"], "")

    def test_a_failing_guard_result_fails_even_when_the_landing_is_right(self):
        self.stub(shell_stdout=b"PREPARE_MAIL_SENDER database=sc_demo\n",
                  guard_rc=2, guard_stderr=b"GUARD: FAIL\n")
        evidence = module.prepare(SHA, SENDER, DEMO_BINDING, "sc-root", "")
        self.assertEqual(evidence["status"], "FAIL")


class CommandTests(unittest.TestCase):
    def test_confirmation_token_is_stable(self):
        self.assertEqual(module.CONFIRMATION, "PREPARE_DAILY_RUNTIME_OUTGOING_MAIL_SENDER")


if __name__ == "__main__":
    unittest.main()
