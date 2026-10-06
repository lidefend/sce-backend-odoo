#!/usr/bin/env python3
"""Behaviour locks for the daily runtime project-lifecycle fixture entry.

These tests do not treat the presence of a string as proof of correctness. They
execute the readback driver against a stub Odoo env and assert the declared
behaviour: the entry consumes the working-tree fixture builder verbatim, prints
the carrier identity it actually resolved, and fails closed when the carrier is
not in the declared start state or when the served revision does not match.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import types
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("daily_runtime_lifecycle_fixture_prepare.py")
SPEC = importlib.util.spec_from_file_location("daily_runtime_lifecycle_fixture_prepare", SCRIPT)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)

FIXTURE_TOOL = Path(__file__).resolve().parents[2] / "addons" / "smart_construction_acceptance_fixture" / "tools" / "frontend_productization_fixture.py"
SHA = "6c8e07f70c1ce0d501f9f5b56911d74f9321a721"
START_STATE = {"lifecycle_state": "draft", "sc_approval_state": "draft"}


class Result:
    def __init__(self, returncode=0, stdout=b"", stderr=b""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class _Cr:
    dbname = "sc_demo"

    def __init__(self):
        self.committed = 0

    def commit(self):
        self.committed += 1


class _Carrier:
    def __init__(self, state):
        self._state = dict(state)
        self.id = 77
        self.code = "FE-LC"
        self.name = "FE Project Lifecycle"
        self.company_id = types.SimpleNamespace(id=42, name="FE Company A")
        self.company_id.name = "FE Company A"

    def __getitem__(self, key):
        return self._state[key]


class _Env:
    def __init__(self, carrier):
        self._carrier = carrier
        self.cr = _Cr()

    def ref(self, xmlid):
        assert xmlid == "smart_construction_acceptance_fixture.fe_project_lifecycle", xmlid
        return self._carrier


def run_driver(carrier_state, *, declared=None, with_env=True, reset=False):
    """Execute the driver exactly as the deployed runtime would."""
    captured = io.StringIO()
    namespace = {
        "MODULE": "smart_construction_acceptance_fixture",
        "LIFECYCLE_FIXTURE_XMLID": "fe_project_lifecycle",
        "LIFECYCLE_FIXTURE_START_STATE": dict(declared if declared is not None else START_STATE),
    }
    carrier = _Carrier(carrier_state)
    if with_env:
        namespace["env"] = _Env(carrier)
        namespace["ensure_fixture"] = lambda _env: {"lifecycle_carrier": {"reset": reset}}
    program = module.fixture_driver()
    with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(io.StringIO()):
        exec(compile(program, "<driver>", "exec"), namespace)
    return captured.getvalue()


def parse_payload(text):
    line = next(row for row in text.splitlines() if row.startswith(module.EXE_LINE))
    return json.loads(line[len(module.EXE_LINE):])


class PreflightTests(unittest.TestCase):
    def test_accepts_declared_inputs(self):
        module.preflight(SHA, "sc_demo", "sc-root", "123456")

    def test_rejects_short_sha(self):
        with self.assertRaises(module.PrepareError):
            module.preflight("6c8e07f7", "sc_demo", "sc-root", "123456")

    def test_rejects_unsafe_database(self):
        with self.assertRaises(module.PrepareError):
            module.preflight(SHA, "sc_demo; rm -rf /", "sc-root", "123456")

    def test_rejects_unsafe_ssh_host(self):
        with self.assertRaises(module.PrepareError):
            module.preflight(SHA, "sc_demo", "sc-root; rm -rf /", "123456")

    def test_rejects_missing_fixture_password(self):
        with self.assertRaises(module.PrepareError):
            module.preflight(SHA, "sc_demo", "sc-root", "")


class ProgramTests(unittest.TestCase):
    def test_program_prepends_the_working_tree_builder(self):
        source = FIXTURE_TOOL.read_text(encoding="utf-8")
        program = module.fixture_program().decode("utf-8")
        # The deployed runtime must execute this branch's fixture tooling, not the
        # builder that happened to be checked out when the runtime was deployed.
        self.assertTrue(program.startswith(source), "program does not embed the working-tree builder verbatim")
        self.assertTrue(program.endswith(module.fixture_driver()))

    def test_program_compiles(self):
        compile(module.fixture_program().decode("utf-8"), "<fixture-program>", "exec")

    def test_driver_is_a_standalone_program(self):
        compile(module.fixture_driver(), "<driver>", "exec")
        self.assertIn(module.EXE_LINE, module.fixture_driver())


class DriverBehaviourTests(unittest.TestCase):
    def test_driver_emits_the_resolved_carrier_identity(self):
        payload = parse_payload(run_driver(START_STATE))
        self.assertEqual(payload["carrier_id"], 77)
        self.assertEqual(payload["database"], "sc_demo")
        self.assertEqual(payload["company_id"], 42)
        self.assertEqual(payload["xmlid"], "smart_construction_acceptance_fixture.fe_project_lifecycle")
        self.assertEqual(payload["state"], START_STATE)
        self.assertFalse(payload["reset"])

    def test_driver_fails_closed_when_carrier_left_the_start_state(self):
        with self.assertRaises(SystemExit):
            run_driver({"lifecycle_state": "closed", "sc_approval_state": "draft"})

    def test_driver_consumes_the_declared_start_state(self):
        declared = {"lifecycle_state": "done", "sc_approval_state": "draft"}
        payload = parse_payload(run_driver(dict(declared), declared=declared, reset=True))
        self.assertEqual(payload["state"], declared)
        self.assertTrue(payload["reset"])

    def test_driver_requires_an_odoo_env(self):
        with self.assertRaises(SystemExit):
            run_driver(START_STATE, with_env=False)


class PrepareTests(unittest.TestCase):
    def _install(self, *, head_sha, engine_stdout, served):
        calls = []

        def fake_ssh(ssh_host, remote_command, *, input_bytes=None):
            calls.append((ssh_host, remote_command, input_bytes))
            if "git rev-parse HEAD" in remote_command:
                return Result(0, (head_sha + "\n").encode())
            return Result(0, engine_stdout.encode())

        original_ssh = module.ssh
        original_served = module.served_identity
        module.ssh = fake_ssh
        module.served_identity = lambda base_url: served
        self.addCleanup(lambda: (setattr(module, "ssh", original_ssh), setattr(module, "served_identity", original_served)))
        return calls

    def test_fails_closed_before_any_engine_run_on_revision_mismatch(self):
        calls = self._install(head_sha="0" * 40, engine_stdout="", served={})
        with self.assertRaises(module.PrepareError):
            module.prepare(SHA, "sc_demo", "sc-root", "", "123456")
        self.assertEqual(len(calls), 1, "engine ran despite a revision mismatch")

    def test_reports_pass_and_uses_the_governed_shell_entry(self):
        payload = {
            "database": "sc_demo",
            "carrier_id": 123,
            "carrier_code": "FE-LC",
            "carrier_name": "FE Project Lifecycle",
            "company_id": 42,
            "company_name": "FE Company A",
            "state": START_STATE,
            "xmlid": "smart_construction_acceptance_fixture.fe_project_lifecycle",
            "reset": False,
        }
        engine = "engine log\n%s%s\n" % (module.EXE_LINE, json.dumps(payload))
        calls = self._install(
            head_sha=SHA,
            engine_stdout=engine,
            served={"database": "sc_demo", "git_sha": SHA},
        )
        evidence = module.prepare(SHA, "sc_demo", "sc-root", "http://daily", "123456")
        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(evidence["carrier"]["carrier_id"], 123)
        command = next(cmd for _, cmd, _ in calls if "odoo.shell.exec" in cmd)
        self.assertIn("make ENV=dev ENV_FILE=.env.dev DB_NAME=sc_demo odoo.shell.exec", command)
        self.assertIn("SC_ACCEPTANCE_FIXTURE_SCOPE=daily_dev", command)
        self.assertIn("SC_ENVIRONMENT=dev", command)
        self.assertIn("SC_ALLOW_DEMO_DATA=1", command)
        self.assertIn("SC_ACCEPTANCE_FIXTURE_PASSWORD=123456", command)
        uploaded = next(payload_bytes for _, cmd, payload_bytes in calls if payload_bytes is not None)
        self.assertIn(b"def ensure_fixture", uploaded)

    def test_fails_when_carrier_is_not_in_the_declared_start_state(self):
        payload = {
            "database": "sc_demo",
            "carrier_id": 123,
            "carrier_code": "FE-LC",
            "carrier_name": "FE Project Lifecycle",
            "company_id": 42,
            "company_name": "FE Company A",
            "state": {"lifecycle_state": "closed", "sc_approval_state": "draft"},
            "xmlid": "smart_construction_acceptance_fixture.fe_project_lifecycle",
            "reset": False,
        }
        engine = "%s%s\n" % (module.EXE_LINE, json.dumps(payload))
        self._install(head_sha=SHA, engine_stdout=engine, served={"database": "sc_demo", "git_sha": SHA})
        evidence = module.prepare(SHA, "sc_demo", "sc-root", "http://daily", "123456")
        self.assertEqual(evidence["status"], "FAIL")

    def test_fails_when_served_revision_does_not_match(self):
        payload = {
            "database": "sc_demo",
            "carrier_id": 123,
            "carrier_code": "FE-LC",
            "carrier_name": "FE Project Lifecycle",
            "company_id": 42,
            "company_name": "FE Company A",
            "state": START_STATE,
            "xmlid": "smart_construction_acceptance_fixture.fe_project_lifecycle",
            "reset": False,
        }
        engine = "%s%s\n" % (module.EXE_LINE, json.dumps(payload))
        self._install(head_sha=SHA, engine_stdout=engine, served={"database": "sc_demo", "git_sha": "f" * 40})
        evidence = module.prepare(SHA, "sc_demo", "sc-root", "http://daily", "123456")
        self.assertEqual(evidence["status"], "FAIL")


class CommandTests(unittest.TestCase):
    def test_confirmation_token_is_stable(self):
        self.assertEqual(module.CONFIRMATION, "DRIVE_DAILY_SC_DEMO_PROJECT_LIFECYCLE")


if __name__ == "__main__":
    unittest.main()
