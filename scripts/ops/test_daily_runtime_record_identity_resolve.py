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


def payload_output(payload=None):
    body = PAYLOAD if payload is None else payload
    return ("noise\n" + module.PAYLOAD_PREFIX + json.dumps(body, sort_keys=True) + "\n").encode()


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

    def test_remote_command_uses_the_governed_shell_entry(self):
        command = module.remote_command("sc_demo")
        self.assertIn("make ENV=dev ENV_FILE=.env.dev DB_NAME=sc_demo odoo.shell.exec", command)
        self.assertIn(module.REMOTE_ROOT, command)

    def test_remote_command_binds_the_declared_database(self):
        self.assertIn("DB_NAME=sc_demo odoo.shell.exec", module.remote_command("sc_demo"))

    def test_remote_command_quotes_an_unsafe_database_value(self):
        # preflight rejects such a value earlier; this locks that the command
        # builder itself can never splice an unquoted token into the remote shell.
        self.assertIn("DB_NAME='sc demo'", module.remote_command("sc demo"))


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
        evidence = module.resolve(SHA, "sc_demo", "sc-root", "http://daily", artifact, report)

        self.assertEqual(evidence["status"], "PASS")
        documented = json.loads(artifact.read_text())
        self.assertEqual(documented["schema"], module.SCHEMA)
        self.assertEqual(documented["expected_sha"], SHA)
        self.assertEqual(documented["targets"]["payment_request"]["record_id"], 36168)
        self.assertEqual(json.loads(report.read_text())["artifact_schema"], module.SCHEMA)
        self.assertEqual(evidence["targets"], ["payment_request"])

    def test_engine_receives_the_working_tree_resolver_verbatim(self):
        self.stub()
        root = self.temp()
        module.resolve(SHA, "sc_demo", "sc-root", "", root / "a.json", root / "r.json")
        engine = [call for call in self.calls if call["program"]][-1]
        self.assertEqual(engine["program"], module.RESOLVER.read_bytes())

    def test_fails_closed_before_any_engine_run_on_revision_mismatch(self):
        self.stub(remote_head="0" * 40)
        root = self.temp()
        with self.assertRaises(module.ResolveError):
            module.resolve(SHA, "sc_demo", "sc-root", "", root / "a.json", root / "r.json")
        self.assertEqual(len(self.calls), 1)
        self.assertFalse((root / "a.json").exists())

    def test_fails_closed_on_served_revision_mismatch(self):
        self.stub(served={"git_sha": "1" * 40, "database": "sc_demo"})
        root = self.temp()
        with self.assertRaises(module.ResolveError):
            module.resolve(SHA, "sc_demo", "sc-root", "http://daily", root / "a.json", root / "r.json")
        self.assertFalse((root / "a.json").exists())

    def test_fails_closed_on_served_database_mismatch(self):
        self.stub(served={"git_sha": SHA, "database": "sc_dev_demo"})
        root = self.temp()
        with self.assertRaises(module.ResolveError):
            module.resolve(SHA, "sc_demo", "sc-root", "http://daily", root / "a.json", root / "r.json")

    def test_fails_closed_on_engine_failure(self):
        self.stub(engine=Result(returncode=1, stderr=b"boom"))
        root = self.temp()
        with self.assertRaises(module.ResolveError):
            module.resolve(SHA, "sc_demo", "sc-root", "", root / "a.json", root / "r.json")

    def test_a_drifted_payload_never_overwrites_the_existing_artifact(self):
        self.stub(engine=Result(stdout=b"engine noise without the payload\n"))
        root = self.temp()
        artifact = root / "a.json"
        artifact.write_text('{"schema": "previous"}\n')
        with self.assertRaises(module.ResolveError):
            module.resolve(SHA, "sc_demo", "sc-root", "", artifact, root / "r.json")
        self.assertEqual(json.loads(artifact.read_text())["schema"], "previous")


if __name__ == "__main__":
    unittest.main()
