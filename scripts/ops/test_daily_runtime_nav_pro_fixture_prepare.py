#!/usr/bin/env python3
"""Behaviour locks for the daily runtime nav_pro fixture entry.

These tests do not treat the presence of a string as proof of correctness. They
execute the readback driver against a stub Odoo env and assert the declared
behaviour: the entry consumes the working-tree nav_pro fixture builder verbatim,
prints the user/carrier identity it actually resolved, and fails closed on a
missing user, a missing carrier, a revision mismatch or a served-revision drift.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import types
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("daily_runtime_nav_pro_fixture_prepare.py")
SPEC = importlib.util.spec_from_file_location("daily_runtime_nav_pro_fixture_prepare", SCRIPT)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)

FIXTURE_TOOL = Path(__file__).resolve().parents[2] / "scripts" / "verify" / "nav_pro_01_prepare_runtime.py"
SHA = "51e7cdc0853b9d8e4732ae9c11b9869a0959b030"
ROLES = {
    "finance": ["smart_construction_core.group_sc_role_finance_manager"],
    "project_member": [
        "smart_construction_core.group_sc_cap_project_read",
        "smart_construction_core.group_sc_cap_business_initiator",
    ],
    "pm": ["smart_construction_core.group_sc_role_project_manager"],
    "owner": ["smart_construction_core.group_sc_role_owner"],
    "config_admin": ["smart_construction_core.group_sc_cap_business_config_admin"],
    "system_admin": ["smart_core.group_smart_core_admin"],
}


class Result:
    def __init__(self, returncode=0, stdout=b"", stderr=b""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class _Cr:
    dbname = "sc_demo"


class _User:
    def __init__(self, uid, login, *, active=True, company_id=42):
        self.id = uid
        self.login = login
        self.active = active
        self.company_id = types.SimpleNamespace(id=company_id)


class _UsersModel:
    def __init__(self, users):
        self._users = list(users)

    def sudo(self):
        return self

    def with_context(self, **_kwargs):
        return self

    def search(self, domain):
        wanted = set(domain[0][2])
        return [user for user in self._users if user.login in wanted]


class _Env:
    def __init__(self, users):
        self.cr = _Cr()
        self.company = types.SimpleNamespace(id=42)
        self._users = _UsersModel(users)

    def __getitem__(self, name):
        assert name == "res.users", name
        return self._users


class _Carrier:
    def __init__(self, rid):
        self.id = rid


def run_driver(users, *, with_env=True):
    captured = io.StringIO()
    namespace = {
        "roles": dict(ROLES),
        "project": _Carrier(501),
        "partner": _Carrier(502),
        "contract": _Carrier(503),
    }
    if with_env:
        namespace["env"] = _Env(users)
    program = module.DRIVER_TEMPLATE.replace("__EXE_LINE__", module.EXE_LINE)
    with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(io.StringIO()):
        exec(compile(program, "<driver>", "exec"), namespace)
    return captured.getvalue()


def full_users():
    return [_User(600 + index, "nav_pro_%s" % role) for index, role in enumerate(ROLES)]


def parse_payload(text):
    line = next(row for row in text.splitlines() if row.startswith(module.EXE_LINE))
    return json.loads(line[len(module.EXE_LINE):])


class PreflightTests(unittest.TestCase):
    def test_accepts_declared_inputs(self):
        module.preflight(SHA, "sc_demo", "sc-root", "123456")

    def test_rejects_short_sha(self):
        with self.assertRaises(module.PrepareError):
            module.preflight("51e7cdc0", "sc_demo", "sc-root", "123456")

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
        self.assertTrue(program.rstrip("\n").endswith(module.DRIVER_TEMPLATE.replace("__EXE_LINE__", module.EXE_LINE).rstrip("\n")))

    def test_program_compiles(self):
        compile(module.fixture_program().decode("utf-8"), "<fixture-program>", "exec")


class DriverBehaviourTests(unittest.TestCase):
    def test_driver_emits_the_resolved_user_and_carrier_identity(self):
        payload = parse_payload(run_driver(full_users()))
        self.assertEqual(payload["database"], "sc_demo")
        self.assertEqual(payload["company_id"], 42)
        self.assertEqual(payload["missing_users"], [])
        self.assertEqual(sorted(payload["users"]), sorted("nav_pro_%s" % role for role in ROLES))
        self.assertEqual(payload["users"]["nav_pro_finance"]["id"], 600)
        self.assertTrue(payload["users"]["nav_pro_finance"]["active"])
        self.assertEqual(payload["project_id"], 501)
        self.assertEqual(payload["partner_id"], 502)
        self.assertEqual(payload["contract_id"], 503)

    def test_driver_reports_missing_users_instead_of_assuming_them(self):
        users = [user for user in full_users() if user.login != "nav_pro_pm"]
        payload = parse_payload(run_driver(users))
        self.assertEqual(payload["missing_users"], ["nav_pro_pm"])

    def test_driver_requires_an_odoo_env(self):
        with self.assertRaises(SystemExit):
            run_driver(full_users(), with_env=False)


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
        self.addCleanup(
            lambda: (
                setattr(module, "ssh", original_ssh),
                setattr(module, "served_identity", original_served),
            )
        )
        return calls

    def _payload(self, *, missing=None, project_id=501):
        users = {
            "nav_pro_%s" % role: {"id": 600 + index, "active": True, "company_id": 42}
            for index, role in enumerate(ROLES)
            if "nav_pro_%s" % role not in (missing or [])
        }
        return {
            "database": "sc_demo",
            "company_id": 42,
            "users": users,
            "missing_users": list(missing or []),
            "project_id": project_id,
            "partner_id": 502,
            "contract_id": 503,
        }

    def test_fails_closed_before_any_engine_run_on_revision_mismatch(self):
        calls = self._install(head_sha="0" * 40, engine_stdout="", served={})
        with self.assertRaises(module.PrepareError):
            module.prepare(SHA, "sc_demo", "sc-root", "", "123456")
        self.assertEqual(len(calls), 1, "engine ran despite a revision mismatch")

    def test_reports_pass_and_uses_the_governed_shell_entry(self):
        engine = "engine log\n%s%s\n%s\n" % (
            module.EXE_LINE,
            json.dumps(self._payload()),
            module.SENTINEL,
        )
        calls = self._install(head_sha=SHA, engine_stdout=engine, served={"database": "sc_demo", "git_sha": SHA})
        evidence = module.prepare(SHA, "sc_demo", "sc-root", "http://daily", "123456")
        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(evidence["readback"]["project_id"], 501)
        command = next(cmd for _, cmd, _ in calls if "odoo.shell.exec" in cmd)
        self.assertIn("make ENV=dev ENV_FILE=.env.dev DB_NAME=sc_demo odoo.shell.exec", command)
        self.assertIn("NAV_PRO_PASSWORD=123456", command)
        self.assertIn("SC_ENVIRONMENT=dev", command)
        self.assertIn("SC_ALLOW_DEMO_DATA=1", command)
        uploaded = next(payload_bytes for _, _, payload_bytes in calls if payload_bytes is not None)
        self.assertIn(b"NAV_PRO_01_RUNTIME_PREPARE=PASS", uploaded)
        self.assertIn(b"nav_pro_", uploaded)

    def test_fails_when_the_success_sentinel_is_absent(self):
        engine = "%s%s\n" % (module.EXE_LINE, json.dumps(self._payload()))
        self._install(head_sha=SHA, engine_stdout=engine, served={"database": "sc_demo", "git_sha": SHA})
        with self.assertRaises(module.PrepareError):
            module.prepare(SHA, "sc_demo", "sc-root", "http://daily", "123456")

    def test_fails_when_a_declared_user_is_missing(self):
        engine = "%s%s\n%s\n" % (
            module.EXE_LINE,
            json.dumps(self._payload(missing=["nav_pro_pm"])),
            module.SENTINEL,
        )
        self._install(head_sha=SHA, engine_stdout=engine, served={"database": "sc_demo", "git_sha": SHA})
        evidence = module.prepare(SHA, "sc_demo", "sc-root", "http://daily", "123456")
        self.assertEqual(evidence["status"], "FAIL")

    def test_fails_when_the_carrier_did_not_read_back(self):
        engine = "%s%s\n%s\n" % (
            module.EXE_LINE,
            json.dumps(self._payload(project_id=0)),
            module.SENTINEL,
        )
        self._install(head_sha=SHA, engine_stdout=engine, served={"database": "sc_demo", "git_sha": SHA})
        evidence = module.prepare(SHA, "sc_demo", "sc-root", "http://daily", "123456")
        self.assertEqual(evidence["status"], "FAIL")

    def test_fails_when_served_revision_does_not_match(self):
        engine = "%s%s\n%s\n" % (module.EXE_LINE, json.dumps(self._payload()), module.SENTINEL)
        self._install(head_sha=SHA, engine_stdout=engine, served={"database": "sc_demo", "git_sha": "f" * 40})
        evidence = module.prepare(SHA, "sc_demo", "sc-root", "http://daily", "123456")
        self.assertEqual(evidence["status"], "FAIL")

    def test_fails_when_served_database_does_not_match(self):
        engine = "%s%s\n%s\n" % (module.EXE_LINE, json.dumps(self._payload()), module.SENTINEL)
        self._install(head_sha=SHA, engine_stdout=engine, served={"database": "sc_other", "git_sha": SHA})
        evidence = module.prepare(SHA, "sc_demo", "sc-root", "http://daily", "123456")
        self.assertEqual(evidence["status"], "FAIL")


class CommandTests(unittest.TestCase):
    def test_confirmation_token_is_stable(self):
        self.assertEqual(module.CONFIRMATION, "PROVISION_DAILY_SC_DEMO_NAV_PRO_FIXTURE")


if __name__ == "__main__":
    unittest.main()
