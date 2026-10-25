#!/usr/bin/env python3
"""Behaviour locks for the governed daily-runtime record identity entry.

These tests do not treat the presence of a string as proof of correctness. They
execute the entry against stub transports and assert the declared behaviour: the
entry consumes the working tree's governed resolver verbatim through the existing
governed shell entry, writes the canonical envelope, and fails closed - without
touching the existing artifact - on any revision, database, transport or payload
disagreement.
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("daily_runtime_record_identity_resolve.py")
SPEC = importlib.util.spec_from_file_location("daily_runtime_record_identity_resolve", SCRIPT)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)

SHA = "6c8e07f70c1ce0d501f9f5b56911d74f9321a721"
BINDING = {
    "duty": "demo",
    "database": "sc_demo",
    "compose_project": "sc-demo-dev",
    "odoo_container": "sc-demo-dev-odoo-1",
}
PAYLOAD = {
    "companies": {"a": 21, "b": 22},
    "payment_request": {
        "menu_id": 550,
        "menu_xmlid": "smart_construction_core.menu_sc_user_payment_apply",
        "action_id": 780,
        "action_xmlid": "smart_construction_core.action_payment_request_user_payment_apply",
        "model": "payment.request",
        "record_id": 36168,
        "record_xmlid": "smart_construction_acceptance_fixture.fe_delivery_hardening_payment_request_a",
        "record_identity": "FE-DELIVERY-HARDENING-001",
    },
}


class Result:
    def __init__(self, returncode=0, stdout=b"", stderr=b""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def payload_output(payload=None, landed="sc_demo"):
    body = PAYLOAD if payload is None else payload
    return (
        "noise\n"
        + module.LANDED_PREFIX + landed + "\n"
        + module.PAYLOAD_PREFIX + json.dumps(body, sort_keys=True) + "\n"
    ).encode()


class PreflightTests(unittest.TestCase):
    def test_accepts_declared_inputs(self):
        module.preflight(SHA, "sc_demo", "sc-root")

    def test_rejects_short_sha(self):
        with self.assertRaises(module.ResolveError):
            module.preflight("6c8e07f7", "sc_demo", "sc-root")

    def test_rejects_unsafe_database(self):
        with self.assertRaises(module.ResolveError):
            module.preflight(SHA, "sc_demo; drop", "sc-root")

    def test_rejects_unsafe_ssh_host(self):
        with self.assertRaises(module.ResolveError):
            module.preflight(SHA, "sc_demo", "sc-root; rm -rf /")

    def test_confirmation_token_is_stable(self):
        self.assertEqual(module.CONFIRMATION, "RESOLVE_DAILY_SC_DEMO_RECORD_IDENTITY")

    def test_artifact_schema_is_the_governed_envelope_schema(self):
        self.assertEqual(module.SCHEMA, "acceptance.record_identity_resolution.v1")


class ProgramTests(unittest.TestCase):
    def test_program_is_the_working_tree_resolver_verbatim(self):
        self.assertEqual(module.resolver_program(), module.RESOLVER.read_bytes())

    def test_remote_shell_runs_in_the_bound_duty_container(self):
        command = module.duty_identity.odoo_shell_command(
            BINDING, program_path="/tmp/x.py", env=module.RESOLVER_ENV
        )
        self.assertIn("sc-demo-dev-odoo-1 odoo shell", command)
        self.assertIn("-d sc_demo", command)
        self.assertIn("SC_ENVIRONMENT=dev", command)
        self.assertIn("SC_ALLOW_DEMO_DATA=1", command)
        self.assertIn("< /tmp/x.py", command)
        self.assertNotIn("ENV_FILE", command)
        self.assertNotIn("sc-backend-odoo-dev", command)

    def test_the_tool_never_routes_through_a_bare_database_name(self):
        source = Path(SCRIPT).read_text(encoding="utf-8")
        # ``make ENV=dev ENV_FILE=.env.dev DB_NAME=x odoo.shell.exec`` resolves its
        # target from a bare name; the bound container comes from the declaration.
        self.assertNotIn("ENV_FILE", source)
        self.assertNotIn("DB_NAME=", source)
        self.assertIn("duty_identity.odoo_shell_command", source)

    def test_the_carrier_program_is_the_resolver_plus_the_landed_probe(self):
        program = module.carrier_program()
        self.assertTrue(program.startswith(module.RESOLVER.read_bytes()))
        self.assertIn(module.LANDED_PREFIX.encode(), program)


class DemoAuthorityTests(unittest.TestCase):
    def test_only_bound_demo_selects_demo_authority(self):
        self.assertEqual(module.resolver_environment(BINDING)["SC_ACCEPTANCE_RECORD_AUTHORITY"], "daily_demo")
        self.assertNotIn("SC_ACCEPTANCE_RECORD_AUTHORITY", module.resolver_environment({"duty": "platform_control"}))
        self.assertNotIn("SC_ACCEPTANCE_RECORD_AUTHORITY", module.resolver_environment({"database": "sc_demo"}))

    def test_demo_resolution_never_loads_fixture_records(self):
        import ast
        from types import SimpleNamespace
        source = ast.parse(module.RESOLVER.read_text())
        func = next(n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == "resolve_targets")
        company = SimpleNamespace(id=1)
        project = SimpleNamespace(_name="project.project", project_code="DEMO-PJ-001", company_id=company)
        calls = []
        def ref(xmlid):
            calls.append(xmlid)
            return {"smart_construction_demo.sc_demo_project_001": project, "base.main_company": company}[xmlid]
        def target(menu, record, **kwargs):
            self.assertEqual(record, "smart_construction_demo.sc_demo_project_001")
            self.assertEqual(kwargs["declared_action_xmlid"], "declared-action")
            return {"company_id": kwargs["expect"]["company_id"](project)}
        ns = {"env": SimpleNamespace(ref=ref), "target": target, "PROJECT_MENU_XMLID": "declared-menu", "PROJECT_ACTION_XMLID": "declared-action"}
        exec(compile(ast.Module(body=[func], type_ignores=[]), str(module.RESOLVER), "exec"), ns)
        self.assertEqual(ns["resolve_targets"]("daily_demo"), {"project": {"company_id": 1}, "companies": {"a": 1}})
        self.assertFalse(any("fixture" in x for x in calls))
        project.project_code = "OTHER"
        with self.assertRaises(AssertionError): ns["resolve_targets"]("daily_demo")
        with self.assertRaises(AssertionError): ns["resolve_targets"]("unknown")


class PayloadTests(unittest.TestCase):
    def test_accepts_the_declared_payload(self):
        self.assertEqual(module.parse_payload(payload_output().decode()), PAYLOAD)

    def test_uses_the_last_payload_line(self):
        first = json.dumps({"companies": {"a": 1}, "old": {}})
        output = (module.PAYLOAD_PREFIX + first + "\n" + module.PAYLOAD_PREFIX
                  + json.dumps(PAYLOAD, sort_keys=True) + "\n")
        self.assertIn("payment_request", module.parse_payload(output))

    def test_rejects_a_missing_payload(self):
        with self.assertRaises(module.ResolveError):
            module.parse_payload("engine noise only")

    def test_rejects_non_json_payload(self):
        with self.assertRaises(module.ResolveError):
            module.parse_payload(module.PAYLOAD_PREFIX + "not-json")

    def test_rejects_a_payload_without_the_companies_map(self):
        with self.assertRaises(module.ResolveError):
            module.parse_payload(payload_output({"payment_request": PAYLOAD["payment_request"]}).decode())

    def test_rejects_a_target_missing_a_required_key(self):
        broken = json.loads(json.dumps(PAYLOAD))
        del broken["payment_request"]["record_xmlid"]
        with self.assertRaises(module.ResolveError):
            module.parse_payload(payload_output(broken).decode())

    def test_rejects_a_non_positive_identity(self):
        broken = json.loads(json.dumps(PAYLOAD))
        broken["payment_request"]["record_id"] = 0
        with self.assertRaises(module.ResolveError):
            module.parse_payload(payload_output(broken).decode())

    def test_rejects_a_non_object_target(self):
        with self.assertRaises(module.ResolveError):
            module.parse_payload(payload_output({"companies": {"a": 21}, "project": "FE Project A"}).decode())

    def test_envelope_carries_the_governed_fields(self):
        envelope = module.envelope(PAYLOAD, SHA)
        self.assertEqual(envelope["schema"], module.SCHEMA)
        self.assertEqual(envelope["producer"], "scripts/verify/frontend_delivery_hardening_runtime_ids.py")
        self.assertEqual(envelope["expected_sha"], SHA)
        self.assertIs(envelope["targets"], PAYLOAD)


class ResolveTests(unittest.TestCase):
    def setUp(self):
        self._ssh = module.ssh
        self._served = module.served_identity
        self.calls = []
        self.served = {"git_sha": SHA, "database": "sc_demo"}
        self.addCleanup(self.restore)

    def restore(self):
        module.ssh = self._ssh
        module.served_identity = self._served

    def stub(self, *, remote_head=SHA, engine=None, served=None):
        def fake_ssh(host, command, *, input_bytes=None):
            self.calls.append({"host": host, "command": command, "program": input_bytes})
            if command.startswith("cd ") and "git rev-parse HEAD" in command:
                return Result(stdout=(remote_head + "\n").encode())
            if "cat > " in command:
                return Result()
            if command.startswith("rm -f "):
                return Result()
            return engine if engine is not None else Result(stdout=payload_output())

        module.ssh = fake_ssh
        module.served_identity = lambda base_url: (self.served if served is None else served)

    def temp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        return Path(directory.name)

    def test_passes_and_writes_the_canonical_artifact_and_report(self):
        self.stub()
        root = self.temp()
        artifact = root / "acceptance_record_identity.json"
        report = root / "resolve.json"
        evidence = module.resolve(SHA, BINDING, "sc-root", "http://daily", artifact, report)

        self.assertEqual(evidence["status"], "PASS")
        documented = json.loads(artifact.read_text())
        self.assertEqual(documented["schema"], module.SCHEMA)
        self.assertEqual(documented["expected_sha"], SHA)
        self.assertEqual(documented["targets"]["payment_request"]["record_id"], 36168)
        self.assertEqual(json.loads(report.read_text())["artifact_schema"], module.SCHEMA)
        self.assertEqual(evidence["targets"], ["payment_request"])

    def test_the_uploaded_program_is_removed_afterwards(self):
        self.stub()
        root = self.temp()
        module.resolve(SHA, BINDING, "sc-root", "", root / "a.json", root / "r.json")
        commands = [call["command"] for call in self.calls]
        self.assertIn("rm -f " + module.REMOTE_TMP, commands[-1])

    def test_a_resolver_that_landed_in_another_database_fails_closed(self):
        self.stub(engine=Result(stdout=payload_output(landed="sc_dev_demo")))
        root = self.temp()
        with self.assertRaisesRegex(module.ResolveError, "not the bound sc_demo"):
            module.resolve(SHA, BINDING, "sc-root", "", root / "a.json", root / "r.json")
        self.assertFalse((root / "a.json").exists())

    def test_engine_receives_the_working_tree_resolver_verbatim(self):
        self.stub()
        root = self.temp()
        module.resolve(SHA, BINDING, "sc-root", "", root / "a.json", root / "r.json")
        uploaded = [call for call in self.calls if call["program"]][-1]
        self.assertTrue(uploaded["program"].startswith(module.RESOLVER.read_bytes()))
        engine = [call for call in self.calls if "docker exec" in call["command"]][0]
        self.assertNotIn("input_bytes", engine)

    def test_fails_closed_before_any_engine_run_on_revision_mismatch(self):
        self.stub(remote_head="0" * 40)
        root = self.temp()
        with self.assertRaises(module.ResolveError):
            module.resolve(SHA, BINDING, "sc-root", "", root / "a.json", root / "r.json")
        self.assertEqual(len(self.calls), 1)
        self.assertFalse((root / "a.json").exists())

    def test_fails_closed_on_served_revision_mismatch(self):
        self.stub(served={"git_sha": "1" * 40, "database": "sc_demo"})
        root = self.temp()
        with self.assertRaises(module.ResolveError):
            module.resolve(SHA, BINDING, "sc-root", "http://daily", root / "a.json", root / "r.json")
        self.assertFalse((root / "a.json").exists())

    def test_fails_closed_on_served_database_mismatch(self):
        self.stub(served={"git_sha": SHA, "database": "sc_dev_demo"})
        root = self.temp()
        with self.assertRaises(module.ResolveError):
            module.resolve(SHA, BINDING, "sc-root", "http://daily", root / "a.json", root / "r.json")

    def test_fails_closed_on_engine_failure(self):
        self.stub(engine=Result(returncode=1, stderr=b"boom"))
        root = self.temp()
        with self.assertRaises(module.ResolveError):
            module.resolve(SHA, BINDING, "sc-root", "", root / "a.json", root / "r.json")

    def test_a_drifted_payload_never_overwrites_the_existing_artifact(self):
        self.stub(engine=Result(stdout=b"engine noise without the payload\n"))
        root = self.temp()
        artifact = root / "a.json"
        artifact.write_text('{"schema": "previous"}\n')
        with self.assertRaises(module.ResolveError):
            module.resolve(SHA, BINDING, "sc-root", "", artifact, root / "r.json")
        self.assertEqual(json.loads(artifact.read_text())["schema"], "previous")


if __name__ == "__main__":
    unittest.main()
