#!/usr/bin/env python3
"""Focused tests for the daily-duty narrow payload import grant entry.

The real declaration deliberately carries no payload operator identity yet, so
these tests drive the entry against a fixture declaration.  That is the point:
the entry must fail closed when the identity is undecided, and it must never
carry a default operator of its own.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "daily_runtime_duty_operator_grant",
    ROOT / "scripts/ops/daily_runtime_duty_operator_grant.py",
)
assert SPEC and SPEC.loader
ENTRY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ENTRY)

DECLARATION = ROOT / "config/ops/daily_runtime_database_duties.v1.json"
CUSTOMER_DUTY = "customer_tenant_dev"
DEMO_DUTY = "demo"
OPERATOR_IDENTITY = "base.user_admin"

READBACK = {
    "mode": "read_only",
    "writes": 0,
    "database": "sc_tenant_baosheng_dev",
    "bound_tenant_key": "baosheng",
    "identity_key": OPERATOR_IDENTITY,
    "importer_group_id": 19,
    "importer_group_member_count": 0,
    "importer_implied_xmlids": [],
    "data_operator_group_id": 20,
    "released_editions": [{"product_key": "construction.standard", "version": "v"}],
    "import_batch_count": 0,
    "operator": {
        "id": 2,
        "login": "admin",
        "active": True,
        "company_count": 1,
        "company_ids": [1],
        "group_xmlids": ["base.group_user"],
        "is_importer": False,
        "is_data_operator": False,
    },
}


def operator_block(**overrides) -> dict:
    block = {
        "carrier": ENTRY.OPERATOR_CARRIER,
        "identity_type": "external_xmlid",
        "identity_key": OPERATOR_IDENTITY,
        "tenant_key": "baosheng",
        "authorization_basis": "docs/ops/iterations/example.md",
        "customer_modules": ["sce_customer_baosheng"],
        "contract": {
            "direct_grant_targets": [ENTRY.IMPORTER_GROUP],
            "transitive_implied_closure": [],
            "required_existing_groups": [ENTRY.INTERNAL_USER_GROUP],
            "expected_direct_grant_additions": [ENTRY.IMPORTER_GROUP],
            "expected_effective_group_additions": [ENTRY.IMPORTER_GROUP],
            "expected_undeclared_group_additions": [],
            "grant_scope_version": ENTRY.GRANT_SCOPE_VERSION,
            "expected_company_scope": 1,
        },
    }
    for key, value in overrides.items():
        if key == "contract":
            block["contract"] = dict(block["contract"], **value)
        else:
            block[key] = value
    return block


class FixtureDeclaration:
    """A declaration that declares a payload operator, plus a real ops root."""

    def __init__(self, block):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        ops_root = self.root / "ops"
        ops_root.mkdir(parents=True, exist_ok=True)
        (ops_root / ("%s.env" % CUSTOMER_DUTY)).write_text(
            "DUTY_NAME=%s\nCOMPOSE_PROJECT_NAME=sc-tenant-baosheng-dev\n"
            "DB_NAME=sc_tenant_baosheng_dev\nDB_USER=sc_tenant_baosheng_dev_app\n"
            "DB_DATA=sc_tenant_baosheng_dev_db_data\n"
            "ODOO_DATA=sc_tenant_baosheng_dev_odoo_data\n"
            "ODOO_IMAGE=odoo17-odoo:latest\nSC_SOURCE_REVISION=%s\n"
            % (CUSTOMER_DUTY, "a" * 40),
            encoding="utf-8",
        )
        declaration = json.loads(DECLARATION.read_text(encoding="utf-8"))
        declaration["ops_root"] = str(ops_root)
        for duty in declaration["duties"]:
            if duty["duty"] == CUSTOMER_DUTY:
                if block is None:
                    duty.pop("payload_operator", None)
                else:
                    duty["payload_operator"] = block
        self.path = self.root / "declaration.json"
        self.path.write_text(json.dumps(declaration), encoding="utf-8")

    def tool_root(self) -> Path:
        root = self.root / "tool"
        destination = root / Path(ENTRY.PROVISION_SCRIPT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("# fixture\n", encoding="utf-8")
        return root

    def close(self):
        self.temporary.cleanup()


class DeclarationTests(unittest.TestCase):
    def test_the_real_declaration_still_has_no_operator_identity(self):
        with self.assertRaisesRegex(
            ENTRY.OperatorGrantEntryError, "no payload_operator block"
        ):
            ENTRY.resolve_grant_duty(CUSTOMER_DUTY)

    def test_non_customer_duties_may_not_be_issued_the_grant(self):
        fixture = FixtureDeclaration(operator_block())
        self.addCleanup(fixture.close)
        for name in (DEMO_DUTY, "platform_control"):
            with self.subTest(duty=name):
                with self.assertRaisesRegex(ENTRY.OperatorGrantEntryError, "not customer"):
                    ENTRY.resolve_grant_duty(name, fixture.path)

    def test_undeclared_duty_is_rejected(self):
        fixture = FixtureDeclaration(operator_block())
        self.addCleanup(fixture.close)
        with self.assertRaisesRegex(ENTRY.OperatorGrantEntryError, "undeclared duty"):
            ENTRY.resolve_grant_duty("customer_tenant_nowhere", fixture.path)

    def test_a_declared_narrow_contract_resolves(self):
        fixture = FixtureDeclaration(operator_block())
        self.addCleanup(fixture.close)
        duty = ENTRY.resolve_grant_duty(CUSTOMER_DUTY, fixture.path)
        operator = duty["payload_operator"]
        self.assertEqual(operator["identity_key"], OPERATOR_IDENTITY)
        self.assertEqual(operator["direct_grant_targets"], [ENTRY.IMPORTER_GROUP])
        self.assertEqual(operator["expected_company_scope"], 1)
        self.assertEqual(operator["customer_modules"], ["sce_customer_baosheng"])

    def test_an_undecided_identity_is_a_stop(self):
        fixture = FixtureDeclaration(operator_block(identity_key=""))
        self.addCleanup(fixture.close)
        with self.assertRaisesRegex(
            ENTRY.OperatorGrantEntryError, "does not declare a usable payload operator identity"
        ):
            ENTRY.resolve_grant_duty(CUSTOMER_DUTY, fixture.path)

    def test_the_contract_may_not_be_widened(self):
        cases = {
            "closure": {"transitive_implied_closure": ["smart_core.group_smart_core_admin"]},
            "data operator": {"expected_effective_group_additions": [ENTRY.DATA_OPERATOR_GROUP]},
            "direct target": {"direct_grant_targets": []},
            "required group": {"required_existing_groups": []},
            "undeclared additions": {"expected_undeclared_group_additions": [ENTRY.IMPORTER_GROUP]},
            "scope version": {"grant_scope_version": 2},
            "company scope": {"expected_company_scope": 0},
        }
        for name, override in cases.items():
            with self.subTest(case=name):
                fixture = FixtureDeclaration(operator_block(contract=override))
                self.addCleanup(fixture.close)
                with self.assertRaises(ENTRY.OperatorGrantEntryError):
                    ENTRY.resolve_grant_duty(CUSTOMER_DUTY, fixture.path)

    def test_the_carrier_and_basis_are_required(self):
        for override in ({"carrier": "anything"}, {"authorization_basis": ""}, {"tenant_key": "other"}):
            with self.subTest(override=override):
                fixture = FixtureDeclaration(operator_block(**override))
                self.addCleanup(fixture.close)
                with self.assertRaises(ENTRY.OperatorGrantEntryError):
                    ENTRY.resolve_grant_duty(CUSTOMER_DUTY, fixture.path)

    def test_entry_hardcodes_no_duty_identity_or_operator(self):
        source = (ROOT / "scripts/ops/daily_runtime_duty_operator_grant.py").read_text()
        duties = json.loads(DECLARATION.read_text())["duties"]
        for duty in duties:
            for key in ("database", "database_role", "dbfilter"):
                value = duty[key]
                if re.fullmatch(r"[a-z]+", value):
                    continue
                self.assertNotIn(value, source, "%s.%s" % (duty["duty"], key))
            for section, key in (
                ("cluster", "container"),
                ("cluster", "data_volume"),
                ("cluster", "compose_project"),
                ("storage", "odoo_data_volume"),
                ("storage", "backup_namespace"),
            ):
                self.assertNotIn(
                    duty[section][key], source, "%s.%s.%s" % (duty["duty"], section, key)
                )
        self.assertNotIn("base.user_admin", source)


class CommandTests(unittest.TestCase):
    def _duty(self):
        fixture = FixtureDeclaration(operator_block())
        self.addCleanup(fixture.close)
        return ENTRY.resolve_grant_duty(CUSTOMER_DUTY, fixture.path)

    def test_the_grant_binds_only_the_declared_contract(self):
        duty = self._duty()
        command = ENTRY.grant_command(
            duty,
            ["docker", "compose", "--project-name", duty["compose_project"]],
            ENTRY.grant_environment(duty, "responsible-role"),
        )
        self.assertEqual(command[:3], ["docker", "compose", "--project-name"])
        self.assertIn("run", command)
        self.assertIn("--no-deps", command)
        self.assertIn("--rm", command)
        self.assertNotIn("--user", command)
        self.assertEqual(command[command.index("--entrypoint") + 1], ENTRY.APPLICATION_ENTRY)
        self.assertEqual(command[command.index("-d") + 1], duty["database"])
        for expected in (
            "SC_TENANT_PAYLOAD_DB_ALLOWLIST=%s" % duty["database"],
            "SC_TENANT_PAYLOAD_TENANT_KEY=%s" % duty["tenant_key"],
            "SC_TENANT_PAYLOAD_OPERATOR_IDENTITY_TYPE=external_xmlid",
            "SC_TENANT_PAYLOAD_OPERATOR_IDENTITY_KEY=%s" % OPERATOR_IDENTITY,
            'SC_TENANT_PAYLOAD_DIRECT_GRANT_TARGETS=["%s"]' % ENTRY.IMPORTER_GROUP,
            "SC_TENANT_PAYLOAD_TRANSITIVE_IMPLIED_CLOSURE=[]",
            'SC_TENANT_PAYLOAD_REQUIRED_EXISTING_GROUPS=["base.group_user"]',
            "SC_TENANT_PAYLOAD_EXPECTED_COMPANY_SCOPE=1",
            "SC_TENANT_PAYLOAD_GRANT_SCOPE_VERSION=3",
            "SC_TENANT_PAYLOAD_APPROVED_BY=responsible-role",
        ):
            self.assertIn(expected, command)

    def test_the_readback_binds_the_declared_identity(self):
        duty = self._duty()
        script = ENTRY.readback_script(duty)
        compile(script, "<readback>", "exec")
        self.assertIn('_identity_key = "%s"' % OPERATOR_IDENTITY, script)
        self.assertNotIn(ENTRY.IDENTITY_KEY_TOKEN, script)

    def test_the_readback_is_read_only_and_binds_the_duty(self):
        duty = self._duty()
        command = ENTRY.readback_command(
            duty, ["docker", "compose", "--project-name", duty["compose_project"]]
        )
        self.assertIn("--no-http", command)
        self.assertEqual(command[command.index("-d") + 1], duty["database"])


class GuardTests(unittest.TestCase):
    def _duty(self):
        fixture = FixtureDeclaration(operator_block())
        self.addCleanup(fixture.close)
        return ENTRY.resolve_grant_duty(CUSTOMER_DUTY, fixture.path)

    def test_an_unsupported_action_is_refused(self):
        with self.assertRaisesRegex(ENTRY.OperatorGrantEntryError, "unsupported"):
            ENTRY.execute(CUSTOMER_DUTY, action="widen")

    def _execute(self, duty, fixture, **kwargs):
        tool_root = fixture.tool_root()
        with mock.patch.object(
            ENTRY.duty_runtime, "read_duty_env", return_value={"ODOO_IMAGE": "odoo17-odoo:latest"}
        ), mock.patch.object(
            ENTRY.duty_runtime, "stack_compose_path", return_value=Path("/tmp/stack.yml")
        ), mock.patch.object(
            ENTRY.duty_runtime, "inspect_odoo_container", return_value={}
        ), mock.patch.object(
            ENTRY, "resolve_grant_duty", return_value=duty
        ):
            return ENTRY.execute(
                CUSTOMER_DUTY, declaration=fixture.path, tool_root=tool_root, **kwargs
            )

    def test_the_grant_requires_the_exact_confirmation(self):
        fixture = FixtureDeclaration(operator_block())
        self.addCleanup(fixture.close)
        duty = ENTRY.resolve_grant_duty(CUSTOMER_DUTY, fixture.path)
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ENTRY.OperatorGrantEntryError, "CONFIRM_DAILY_DUTY"):
                self._execute(duty, fixture, action="grant", approved_by="responsible-role")

    def test_the_grant_refuses_an_empty_or_guessed_approver(self):
        fixture = FixtureDeclaration(operator_block())
        self.addCleanup(fixture.close)
        duty = ENTRY.resolve_grant_duty(CUSTOMER_DUTY, fixture.path)
        with mock.patch.dict(
            os.environ,
            {"CONFIRM_DAILY_DUTY_OPERATOR_GRANT": "GRANT_NARROW_PAYLOAD_IMPORT_OPERATOR_IN_DAILY_DUTY"},
            clear=True,
        ):
            with self.assertRaisesRegex(ENTRY.OperatorGrantEntryError, "real approving subject"):
                self._execute(duty, fixture, action="grant", approved_by="  ")

    def test_a_grant_is_asserted_against_the_declaration(self):
        fixture = FixtureDeclaration(operator_block())
        self.addCleanup(fixture.close)
        duty = ENTRY.resolve_grant_duty(CUSTOMER_DUTY, fixture.path)
        after = json.loads(json.dumps(READBACK))
        after["operator"]["group_xmlids"] = ["base.group_user", ENTRY.IMPORTER_GROUP]
        after["operator"]["is_importer"] = True
        entry_report = {
            "schema_version": "tenant_payload_operator_grant.v3",
            "status": "PASS",
            "database": duty["database"],
            "operator_identity_type": "external_xmlid",
            "operator_identity_key": OPERATOR_IDENTITY,
            "direct_grant_targets": [ENTRY.IMPORTER_GROUP],
            "transitive_implied_closure": [],
            "required_existing_groups": [ENTRY.INTERNAL_USER_GROUP],
            "undeclared_group_additions": [],
            "data_operator_added": False,
            "company_scope_count": 1,
            "changed": True,
            "effective_group_additions": [ENTRY.IMPORTER_GROUP],
        }
        outputs = [
            ENTRY.READBACK_MARKER + json.dumps(READBACK),
            json.dumps(entry_report),
            ENTRY.READBACK_MARKER + json.dumps(after),
        ]
        with mock.patch.dict(
            os.environ,
            {"CONFIRM_DAILY_DUTY_OPERATOR_GRANT": "GRANT_NARROW_PAYLOAD_IMPORT_OPERATOR_IN_DAILY_DUTY"},
            clear=True,
        ), mock.patch.object(ENTRY, "run_script", side_effect=outputs):
            evidence = self._execute(
                duty, fixture, action="grant", approved_by="responsible-role"
            )
        self.assertEqual(evidence["action"], "grant")
        self.assertEqual(evidence["approved_by_fingerprint"], ENTRY.hashlib.sha256(
            b"responsible-role"
        ).hexdigest()[:12])
        self.assertNotIn("responsible-role", json.dumps(evidence))

    def test_readback_rejects_a_database_that_is_not_the_duty(self):
        duty = self._duty()
        tampered = dict(READBACK, database="sc_demo")
        with self.assertRaisesRegex(ENTRY.OperatorGrantEntryError, "another database"):
            ENTRY.assert_readback(tampered, duty)

    def test_readback_rejects_an_implied_closure_and_a_write(self):
        duty = self._duty()
        for tampered, message in (
            (dict(READBACK, importer_implied_xmlids=["smart_core.group_smart_core_admin"]), "implied closure"),
            (dict(READBACK, writes=1), "read-only"),
        ):
            with self.subTest(message=message):
                with self.assertRaisesRegex(ENTRY.OperatorGrantEntryError, message):
                    ENTRY.assert_readback(tampered, duty)

    def test_the_grant_refuses_a_widened_change(self):
        duty = self._duty()
        before = json.loads(json.dumps(READBACK))
        widened = json.loads(json.dumps(READBACK))
        widened["operator"]["group_xmlids"] = [
            "base.group_user",
            ENTRY.IMPORTER_GROUP,
            ENTRY.DATA_OPERATOR_GROUP,
        ]
        widened["operator"]["is_importer"] = True
        widened["operator"]["is_data_operator"] = True
        entry_report = {
            "database": duty["database"],
            "operator_identity_type": "external_xmlid",
            "operator_identity_key": OPERATOR_IDENTITY,
            "direct_grant_targets": [ENTRY.IMPORTER_GROUP],
            "transitive_implied_closure": [],
            "required_existing_groups": [ENTRY.INTERNAL_USER_GROUP],
            "undeclared_group_additions": [],
            "data_operator_added": False,
            "company_scope_count": 1,
            "changed": True,
            "effective_group_additions": [ENTRY.IMPORTER_GROUP],
        }
        with self.assertRaisesRegex(ENTRY.OperatorGrantEntryError, "data operator"):
            ENTRY.assert_grant(entry_report, duty, before, widened)

        undeclared = json.loads(json.dumps(widened))
        undeclared["operator"]["is_data_operator"] = False
        undeclared["operator"]["group_xmlids"] = [
            "base.group_user",
            ENTRY.IMPORTER_GROUP,
            "smart_core.group_smart_core_admin",
        ]
        with self.assertRaisesRegex(ENTRY.OperatorGrantEntryError, "did not name"):
            ENTRY.assert_grant(entry_report, duty, before, undeclared)

    def test_the_grant_refuses_a_scope_drift(self):
        duty = self._duty()
        before = json.loads(json.dumps(READBACK))
        after = json.loads(json.dumps(READBACK))
        after["operator"]["is_importer"] = True
        after["operator"]["company_count"] = 2
        after["operator"]["group_xmlids"] = ["base.group_user", ENTRY.IMPORTER_GROUP]
        entry_report = {
            "database": duty["database"],
            "operator_identity_type": "external_xmlid",
            "operator_identity_key": OPERATOR_IDENTITY,
            "direct_grant_targets": [ENTRY.IMPORTER_GROUP],
            "transitive_implied_closure": [],
            "required_existing_groups": [ENTRY.INTERNAL_USER_GROUP],
            "undeclared_group_additions": [],
            "data_operator_added": False,
            "company_scope_count": 1,
            "changed": True,
            "effective_group_additions": [ENTRY.IMPORTER_GROUP],
        }
        with self.assertRaisesRegex(ENTRY.OperatorGrantEntryError, "company scope"):
            ENTRY.assert_grant(entry_report, duty, before, after)


if __name__ == "__main__":
    unittest.main(verbosity=2)
