#!/usr/bin/env python3
"""Focused tests for the daily-duty payload-import operator lifecycle entry.

The real declaration carries the payload operator identity, and the entry
resolves it through the platform policy rather than restating the rules.  These
tests therefore cover both sides: the real declaration must resolve, and the
entry must still fail closed when the identity or the approval is undecided --
it never carries a default operator, a fabricated approver or an approval that
covers another subject.
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
OPERATOR_IDENTITY = "smart_core.svc_tenant_payload_operator_baosheng"
OPERATOR_LOGIN = "svc-tenant-payload-operator-baosheng"
PAYLOAD_CHECKSUM = "c" * 64

OPERATOR_STATE = {
    "id": 12,
    "login": OPERATOR_LOGIN,
    "name": "Tenant payload operator (baosheng, dev)",
    "active": True,
    "share": False,
    "company_ids": [1],
    "group_xmlids": ["base.group_user"],
    "is_importer": False,
    "is_data_operator": False,
    "has_stored_password": False,
    "has_native_api_keys": False,
}

READBACK = {
    "mode": "read_only",
    "writes": 0,
    "database": "sc_tenant_baosheng_dev",
    "bound_tenant_key": "baosheng",
    "identity_key": OPERATOR_IDENTITY,
    "importer_group_member_count": 0,
    "importer_implied_xmlids": [],
    "released_editions": [{"product_key": "construction.standard", "version": "v"}],
    "import_batch_count": 0,
    "operator": dict(OPERATOR_STATE),
}
UNPROVISIONED = dict(READBACK, operator=None)

APPROVAL = {
    "access_id": 7,
    "db_name": "sc_tenant_baosheng_dev",
    "tenant_key": "baosheng",
    "capability": "migrate",
    "state": "approved",
    "operator_identity_key": OPERATOR_IDENTITY,
    "subject_checksum": PAYLOAD_CHECKSUM,
    "approved_by": "owner-approver",
    "requested_by": "platform-maintenance",
    "valid_from": "2026-10-15 00:00:00",
    "valid_until": "2026-10-16 00:00:00",
}


def operator_block(**overrides) -> dict:
    block = {
        "carrier": ENTRY.OPERATOR_CARRIER,
        "identity_type": "external_xmlid",
        "identity_key": OPERATOR_IDENTITY,
        "login": OPERATOR_LOGIN,
        "name": "Tenant payload operator (baosheng, dev)",
        "company_xmlid": "base.main_company",
        "tenant_key": "baosheng",
        "authorization_basis": "docs/ops/iterations/daily_runtime_version_release_user_acceptance_20261015.md",
        "expected_account_groups": ["base.group_user"],
        "forbidden_account_groups": list(ENTRY.operator_policy().FORBIDDEN_ACCOUNT_GROUPS),
        "import_capability": ENTRY.operator_policy().IMPORT_CAPABILITY,
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
        for duty_name in (CUSTOMER_DUTY, ENTRY.PLATFORM_CONTROL_DUTY):
            (ops_root / ("%s.env" % duty_name)).write_text(
                "DUTY_NAME=%s\nCOMPOSE_PROJECT_NAME=sc-tenant-baosheng-dev\n"
                "DB_NAME=sc_tenant_baosheng_dev\nDB_USER=sc_tenant_baosheng_dev_app\n"
                "DB_DATA=sc_tenant_baosheng_dev_db_data\n"
                "ODOO_DATA=sc_tenant_baosheng_dev_odoo_data\n"
                "ODOO_IMAGE=odoo17-odoo:latest\nSC_SOURCE_REVISION=%s\n"
                % (duty_name, "a" * 40),
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

    def control_duty(self) -> dict:
        return ENTRY.duty_identity.resolve(ENTRY.PLATFORM_CONTROL_DUTY, self.path)

    def tool_root(self) -> Path:
        root = self.root / "tool"
        destination = root / Path(ENTRY.POLICY_SOURCE)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            (ROOT / ENTRY.POLICY_SOURCE).read_text(encoding="utf-8"), encoding="utf-8"
        )
        return root

    def close(self):
        self.temporary.cleanup()


class DeclarationTests(unittest.TestCase):
    def test_the_real_declaration_resolves_through_the_platform_policy(self):
        # The declaration owns the tenant difference; the platform policy owns
        # the rules.  Both must agree on the real declaration, and the entry
        # must not restate the contract on its own.
        duty = ENTRY.resolve_grant_duty(CUSTOMER_DUTY)
        operator = duty["payload_operator"]
        declared = ENTRY.duty_identity.load_duties(None)[CUSTOMER_DUTY]["payload_operator"]
        self.assertEqual(operator["carrier"], ENTRY.OPERATOR_CARRIER)
        self.assertEqual(operator["identity_type"], "external_xmlid")
        self.assertEqual(declared["tenant_key"], duty["tenant_key"])
        self.assertEqual(operator["identity_key"], declared["identity_key"])
        self.assertEqual(operator["login"], declared["login"])
        self.assertEqual(operator["direct_grant_targets"], [ENTRY.IMPORTER_GROUP])
        self.assertEqual(operator["transitive_implied_closure"], [])
        self.assertEqual(operator["required_existing_groups"], [ENTRY.INTERNAL_USER_GROUP])
        self.assertEqual(operator["expected_undeclared_group_additions"], [])
        self.assertEqual(operator["grant_scope_version"], ENTRY.GRANT_SCOPE_VERSION)
        self.assertEqual(operator["expected_company_scope"], 1)
        self.assertEqual(operator["customer_modules"], ["sce_customer_baosheng"])
        self.assertNotIn(ENTRY.DATA_OPERATOR_GROUP, operator["direct_grant_targets"])

    def test_a_duty_that_declares_no_operator_block_is_a_stop(self):
        fixture = FixtureDeclaration(None)
        self.addCleanup(fixture.close)
        with self.assertRaisesRegex(
            ENTRY.OperatorGrantEntryError, "no payload_operator block"
        ):
            ENTRY.resolve_grant_duty(CUSTOMER_DUTY, fixture.path)

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
        self.assertEqual(operator["login"], OPERATOR_LOGIN)
        self.assertEqual(operator["company_xmlid"], "base.main_company")
        self.assertEqual(operator["direct_grant_targets"], [ENTRY.IMPORTER_GROUP])
        self.assertEqual(operator["expected_company_scope"], 1)
        self.assertEqual(operator["customer_modules"], ["sce_customer_baosheng"])

    def test_the_carrier_must_be_the_unified_onboarding_mechanism(self):
        for carrier in ("", "narrow_import_grant", "customer_module"):
            with self.subTest(carrier=carrier):
                fixture = FixtureDeclaration(operator_block(carrier=carrier))
                self.addCleanup(fixture.close)
                with self.assertRaises(ENTRY.OperatorGrantEntryError):
                    ENTRY.resolve_grant_duty(CUSTOMER_DUTY, fixture.path)

    def test_an_undecided_identity_is_a_stop(self):
        fixture = FixtureDeclaration(operator_block(identity_key=""))
        self.addCleanup(fixture.close)
        with self.assertRaisesRegex(
            ENTRY.OperatorGrantEntryError, "unusable payload operator"
        ):
            ENTRY.resolve_grant_duty(CUSTOMER_DUTY, fixture.path)

    def test_an_identity_owned_by_base_is_a_stop(self):
        fixture = FixtureDeclaration(operator_block(identity_key="base.user_admin"))
        self.addCleanup(fixture.close)
        with self.assertRaisesRegex(ENTRY.OperatorGrantEntryError, "IDENTITY_MODULE_FORBIDDEN"):
            ENTRY.resolve_grant_duty(CUSTOMER_DUTY, fixture.path)

    def test_the_account_declaration_is_validated_by_the_platform_policy(self):
        cases = {
            "account ceiling": {"expected_account_groups": ["base.group_user", "base.group_system"]},
            "forbidden ceiling": {"forbidden_account_groups": ["base.group_system"]},
            "capability": {"import_capability": "read"},
            "company": {"company_xmlid": ""},
            "login": {"login": "A"},
            "name": {"name": ""},
            "basis": {"authorization_basis": ""},
        }
        for name, override in cases.items():
            with self.subTest(case=name):
                fixture = FixtureDeclaration(operator_block(**override))
                self.addCleanup(fixture.close)
                with self.assertRaises(ENTRY.OperatorGrantEntryError):
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

    def test_the_declaration_must_name_this_tenant(self):
        for override in ({"tenant_key": "other"}, {"tenant_key": ""}, {"carrier": "anything"}):
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

    def test_the_entry_owns_no_lifecycle_rule_of_its_own(self):
        """The declaration rules must come from the platform policy module."""
        source = (ROOT / "scripts/ops/daily_runtime_duty_operator_grant.py").read_text()
        self.assertIn("operator_policy", source)
        for rule in (
            "base.group_erp_manager",
            "group_smart_core_security_admin",
            "group_smart_core_business_config_admin",
        ):
            self.assertNotIn(rule, source)


class CommandTests(unittest.TestCase):
    def _duty(self, block=None):
        fixture = FixtureDeclaration(block or operator_block())
        self.addCleanup(fixture.close)
        return ENTRY.resolve_grant_duty(CUSTOMER_DUTY, fixture.path)

    def test_a_lifecycle_step_binds_only_the_declared_facts(self):
        duty = self._duty()
        command = ENTRY.lifecycle_command(
            duty,
            ["docker", "compose", "--project-name", duty["compose_project"]],
            ENTRY.lifecycle_environment(duty, "grant", APPROVAL),
        )
        self.assertEqual(command[:3], ["docker", "compose", "--project-name"])
        self.assertIn("run", command)
        self.assertIn("--no-deps", command)
        self.assertIn("--rm", command)
        self.assertNotIn("--user", command)
        self.assertEqual(command[command.index("--entrypoint") + 1], ENTRY.APPLICATION_ENTRY)
        self.assertEqual(command[command.index("-d") + 1], duty["database"])
        for expected in (
            "SC_TENANT_PAYLOAD_OPERATOR_ACTION=grant",
            "SC_TENANT_PAYLOAD_OPERATOR_IDENTITY_KEY=%s" % OPERATOR_IDENTITY,
            "SC_TENANT_PAYLOAD_DB_ALLOWLIST=%s" % duty["database"],
        ):
            self.assertIn(expected, command)
        self.assertTrue(
            any(row.startswith("SC_TENANT_PAYLOAD_OPERATOR_AUTHORIZATION={") for row in command)
        )

    def test_provisioning_carries_the_declaration_and_the_approval(self):
        duty = self._duty()
        environment = ENTRY.lifecycle_environment(duty, "provision", APPROVAL)
        self.assertIn("SC_TENANT_PAYLOAD_OPERATOR_ACTION=provision", environment)
        declaration_rows = [
            row for row in environment if row.startswith("SC_TENANT_PAYLOAD_OPERATOR_DECLARATION=")
        ]
        self.assertEqual(len(declaration_rows), 1)
        declared = json.loads(declaration_rows[0].split("=", 1)[1])
        self.assertEqual(declared["identity_key"], OPERATOR_IDENTITY)
        self.assertEqual(declared["expected_account_groups"], ["base.group_user"])

    def test_revocation_carries_no_approval_and_no_declaration(self):
        duty = self._duty()
        environment = ENTRY.lifecycle_environment(duty, "revoke", None)
        self.assertIn("SC_TENANT_PAYLOAD_OPERATOR_ACTION=revoke", environment)
        for prefix in (
            "SC_TENANT_PAYLOAD_OPERATOR_AUTHORIZATION=",
            "SC_TENANT_PAYLOAD_OPERATOR_DECLARATION=",
        ):
            self.assertFalse([row for row in environment if row.startswith(prefix)])

    def test_an_approval_requiring_action_without_one_is_a_stop(self):
        duty = self._duty()
        for action in ENTRY.APPROVAL_REQUIRED_ACTIONS:
            with self.subTest(action=action), self.assertRaisesRegex(
                ENTRY.OperatorGrantEntryError, "requires an approved maintenance access"
            ):
                ENTRY.lifecycle_environment(duty, action, None)

    def test_the_readback_binds_the_declared_identity(self):
        duty = self._duty()
        script = ENTRY.readback_script(duty)
        compile(script, "<readback>", "exec")
        self.assertIn('_identity_key = "%s"' % OPERATOR_IDENTITY, script)
        self.assertNotIn(ENTRY.IDENTITY_KEY_TOKEN, script)
        self.assertIn("tenant_payload_operator", script)

    def test_the_lifecycle_entry_commits_and_binds_the_duty(self):
        duty = self._duty()
        script = ENTRY.lifecycle_script(duty)
        compile(script, "<lifecycle>", "exec")
        self.assertIn('_identity_key = "%s"' % OPERATOR_IDENTITY, script)
        self.assertNotIn(ENTRY.IDENTITY_KEY_TOKEN, script)
        self.assertIn("env.cr.commit()", script)

    def test_the_approval_read_binds_the_duty_and_capability(self):
        duty = self._duty()
        script = ENTRY.approval_script(duty, "migrate")
        compile(script, "<approval>", "exec")
        self.assertIn('db_name="%s"' % duty["database"], script)
        self.assertIn('capability="migrate"', script)
        self.assertNotIn(ENTRY.DATABASE_TOKEN, script)
        self.assertNotIn(ENTRY.CAPABILITY_TOKEN, script)

    def test_an_unusable_subject_digest_is_a_stop(self):
        for value in ("", "abc", "C" * 64, "c" * 63, None):
            with self.subTest(value=value), self.assertRaises(ENTRY.OperatorGrantEntryError):
                ENTRY.subject_checksum(value)
        self.assertEqual(ENTRY.subject_checksum(PAYLOAD_CHECKSUM), PAYLOAD_CHECKSUM)

    def test_the_readback_is_read_only_and_binds_the_duty(self):
        duty = self._duty()
        command = ENTRY.readback_command(
            duty, ["docker", "compose", "--project-name", duty["compose_project"]]
        )
        self.assertIn("--no-http", command)
        self.assertEqual(command[command.index("-d") + 1], duty["database"])


class GuardTests(unittest.TestCase):
    def _duty(self, block=None):
        fixture = FixtureDeclaration(block or operator_block())
        self.addCleanup(fixture.close)
        return ENTRY.resolve_grant_duty(CUSTOMER_DUTY, fixture.path)

    def _approval_read(self, approval):
        return {"mode": "read_only", "writes": 0, "approval": approval}

    def test_an_unsupported_action_is_refused(self):
        with self.assertRaisesRegex(ENTRY.OperatorGrantEntryError, "unsupported"):
            ENTRY.execute(CUSTOMER_DUTY, action="widen")

    def _execute(self, duty, fixture, action, **kwargs):
        tool_root = fixture.tool_root()
        control = fixture.control_duty()

        def _resolve(name, path=None):
            return control if name == ENTRY.PLATFORM_CONTROL_DUTY else duty

        with mock.patch.object(
            ENTRY.duty_runtime, "read_duty_env", return_value={"ODOO_IMAGE": "odoo17-odoo:latest"}
        ), mock.patch.object(
            ENTRY.duty_runtime, "stack_compose_path", return_value=Path("/tmp/stack.yml")
        ), mock.patch.object(
            ENTRY.duty_runtime, "inspect_odoo_container", return_value={}
        ), mock.patch.object(
            ENTRY, "resolve_grant_duty", return_value=duty
        ), mock.patch.object(
            ENTRY.duty_identity, "resolve", side_effect=_resolve
        ):
            return ENTRY.execute(
                CUSTOMER_DUTY,
                action=action,
                declaration=fixture.path,
                tool_root=tool_root,
                **kwargs,
            )

    def test_every_lifecycle_write_requires_its_exact_confirmation(self):
        fixture = FixtureDeclaration(operator_block())
        self.addCleanup(fixture.close)
        duty = ENTRY.resolve_grant_duty(CUSTOMER_DUTY, fixture.path)
        with mock.patch.dict(os.environ, {}, clear=True):
            for action in ("provision", "grant", "revoke"):
                with self.subTest(action=action), self.assertRaisesRegex(
                    ENTRY.OperatorGrantEntryError, "CONFIRM_DAILY_DUTY"
                ):
                    self._execute(duty, fixture, action, subject=PAYLOAD_CHECKSUM)

    def test_the_grant_without_an_approval_is_refused_before_any_write(self):
        fixture = FixtureDeclaration(operator_block())
        self.addCleanup(fixture.close)
        duty = ENTRY.resolve_grant_duty(CUSTOMER_DUTY, fixture.path)
        environment = {
            "CONFIRM_DAILY_DUTY_OPERATOR_GRANT": "GRANT_NARROW_PAYLOAD_IMPORT_OPERATOR_IN_DAILY_DUTY"
        }
        with mock.patch.dict(os.environ, environment, clear=True), mock.patch.object(
            ENTRY,
            "run_script",
            side_effect=[
                ENTRY.READBACK_MARKER + json.dumps(READBACK),
                ENTRY.APPROVAL_MARKER + json.dumps(self._approval_read(None)),
            ],
        ) as runner:
            with self.assertRaisesRegex(
                ENTRY.OperatorGrantEntryError,
                "holds no approved, in-window maintenance access",
            ):
                self._execute(duty, fixture, "grant", subject=PAYLOAD_CHECKSUM)
        self.assertEqual(runner.call_count, 2)

    def test_the_approval_must_cover_this_run(self):
        duty = self._duty()
        cases = {
            "another database": {"db_name": "sc_demo"},
            "another tenant": {"tenant_key": "other"},
            "another operator": {"operator_identity_key": "smart_core.other"},
            "another capability": {"capability": "read"},
            "another subject": {"subject_checksum": "d" * 64},
            "not approved": {"state": "requested"},
            "no approver": {"approved_by": ""},
            "a self approval": {"approved_by": APPROVAL["requested_by"]},
            "no identity": {"access_id": 0},
        }
        for name, override in cases.items():
            with self.subTest(case=name), self.assertRaises(ENTRY.OperatorGrantEntryError):
                ENTRY.assert_approval(
                    self._approval_read(dict(APPROVAL, **override)), duty, PAYLOAD_CHECKSUM
                )
        ENTRY.assert_approval(self._approval_read(APPROVAL), duty, PAYLOAD_CHECKSUM)

    def test_an_approval_read_that_wrote_is_refused(self):
        duty = self._duty()
        with self.assertRaisesRegex(ENTRY.OperatorGrantEntryError, "read-only"):
            ENTRY.assert_approval(
                {"mode": "read_only", "writes": 1, "approval": APPROVAL},
                duty,
                PAYLOAD_CHECKSUM,
            )

    def test_a_provision_is_asserted_against_the_declaration(self):
        fixture = FixtureDeclaration(operator_block())
        self.addCleanup(fixture.close)
        duty = ENTRY.resolve_grant_duty(CUSTOMER_DUTY, fixture.path)
        entry_report = {
            "schema_version": "tenant_payload_operator_lifecycle.v1",
            "action": "provision",
            "identity_key": OPERATOR_IDENTITY,
            "database": duty["database"],
            "mode": "provision",
            "writes": 1,
            "created": True,
            "plan": {"grantable_group_xmlids": [ENTRY.IMPORTER_GROUP]},
            "operator": dict(OPERATOR_STATE),
        }
        outputs = [
            ENTRY.READBACK_MARKER + json.dumps(UNPROVISIONED),
            ENTRY.APPROVAL_MARKER + json.dumps(self._approval_read(APPROVAL)),
            ENTRY.LIFECYCLE_MARKER + json.dumps(entry_report),
            ENTRY.READBACK_MARKER + json.dumps(READBACK),
        ]
        environment = {
            "CONFIRM_DAILY_DUTY_OPERATOR_PROVISION": "PROVISION_DECLARED_PAYLOAD_IMPORT_OPERATOR_IN_DAILY_DUTY"
        }
        with mock.patch.dict(os.environ, environment, clear=True), mock.patch.object(
            ENTRY, "run_script", side_effect=outputs
        ):
            evidence = self._execute(
                duty, fixture, "provision", subject=PAYLOAD_CHECKSUM
            )
        self.assertEqual(evidence["action"], "provision")
        self.assertEqual(evidence["approval_access_id"], APPROVAL["access_id"])
        self.assertEqual(evidence["approved_subject_checksum"], PAYLOAD_CHECKSUM)
        self.assertEqual(
            evidence["approval_approved_by_fingerprint"],
            ENTRY.hashlib.sha256(b"owner-approver").hexdigest()[:12],
        )
        self.assertNotIn("owner-approver", json.dumps(evidence))

    def test_a_provision_that_invented_a_wider_plan_is_refused(self):
        duty = self._duty()
        entry_report = {
            "action": "provision",
            "identity_key": OPERATOR_IDENTITY,
            "database": duty["database"],
            "created": True,
            "plan": {"grantable_group_xmlids": [ENTRY.IMPORTER_GROUP, ENTRY.DATA_OPERATOR_GROUP]},
            "operator": dict(OPERATOR_STATE),
        }
        with self.assertRaisesRegex(ENTRY.OperatorGrantEntryError, "wider grant"):
            ENTRY.assert_lifecycle(entry_report, duty, "provision", UNPROVISIONED)

    def test_a_provision_holding_an_interactive_credential_is_refused(self):
        duty = self._duty()
        entry_report = {
            "action": "provision",
            "identity_key": OPERATOR_IDENTITY,
            "database": duty["database"],
            "created": True,
            "plan": {"grantable_group_xmlids": [ENTRY.IMPORTER_GROUP]},
            "operator": dict(OPERATOR_STATE, has_stored_password=True),
        }
        with self.assertRaisesRegex(ENTRY.OperatorGrantEntryError, "credential"):
            ENTRY.assert_lifecycle(entry_report, duty, "provision", UNPROVISIONED)

    def test_a_grant_is_asserted_against_the_declaration(self):
        duty = self._duty()
        after = json.loads(json.dumps(READBACK))
        after["operator"]["group_xmlids"] = ["base.group_user", ENTRY.IMPORTER_GROUP]
        after["operator"]["is_importer"] = True
        entry_report = {
            "schema_version": "tenant_payload_operator_lifecycle.v1",
            "action": "grant",
            "identity_key": OPERATOR_IDENTITY,
            "database": duty["database"],
            "before": UNPROVISIONED,
            "after": dict(after, mode="grant", writes=1, changed=True),
        }
        # The grant always follows provisioning, so the account already exists
        # when the "before" readback is taken.
        ENTRY.assert_lifecycle(entry_report, duty, "grant", READBACK)

        widened = json.loads(json.dumps(entry_report))
        widened["after"]["operator"]["group_xmlids"] = [
            "base.group_user",
            ENTRY.IMPORTER_GROUP,
            "smart_core.group_smart_core_admin",
        ]
        with self.assertRaisesRegex(ENTRY.OperatorGrantEntryError, "did not name"):
            ENTRY.assert_lifecycle(widened, duty, "grant", READBACK)

        removed = json.loads(json.dumps(entry_report))
        removed["after"]["operator"]["group_xmlids"] = [ENTRY.IMPORTER_GROUP]
        with self.assertRaisesRegex(ENTRY.OperatorGrantEntryError, "removed a group"):
            ENTRY.assert_lifecycle(removed, duty, "grant", READBACK)

    def test_a_grant_that_touched_the_data_operator_group_is_refused(self):
        duty = self._duty()
        after = json.loads(json.dumps(READBACK))
        after["operator"]["group_xmlids"] = ["base.group_user", ENTRY.IMPORTER_GROUP]
        after["operator"]["is_importer"] = True
        after["operator"]["is_data_operator"] = True
        entry_report = {
            "action": "grant",
            "identity_key": OPERATOR_IDENTITY,
            "database": duty["database"],
            "before": UNPROVISIONED,
            "after": dict(after, changed=True),
        }
        with self.assertRaisesRegex(ENTRY.OperatorGrantEntryError, "data operator"):
            ENTRY.assert_lifecycle(entry_report, duty, "grant", UNPROVISIONED)

    def test_a_revocation_must_keep_the_account_and_drop_the_permission(self):
        duty = self._duty()
        revoked = json.loads(json.dumps(READBACK))
        revoked["changed"] = True
        revoked["mode"] = "revoke"
        revoked["action"] = "revoke"
        ENTRY.assert_lifecycle(revoked, duty, "revoke", READBACK)

        still_held = json.loads(json.dumps(revoked))
        still_held["operator"]["is_importer"] = True
        with self.assertRaisesRegex(ENTRY.OperatorGrantEntryError, "still held"):
            ENTRY.assert_lifecycle(still_held, duty, "revoke", READBACK)

        removed_account = json.loads(json.dumps(revoked))
        removed_account["operator"] = None
        with self.assertRaisesRegex(ENTRY.OperatorGrantEntryError, "no operator state"):
            ENTRY.assert_lifecycle(removed_account, duty, "revoke", READBACK)

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
            (dict(READBACK, identity_key="smart_core.other"), "another identity"),
            (dict(READBACK, bound_tenant_key="other"), "another tenant"),
        ):
            with self.subTest(message=message):
                with self.assertRaisesRegex(ENTRY.OperatorGrantEntryError, message):
                    ENTRY.assert_readback(tampered, duty)

    def test_readback_rejects_an_operator_outside_the_declared_ceiling(self):
        duty = self._duty()
        cases = {
            "forbidden group": {"group_xmlids": ["base.group_user", "base.group_system"]},
            "data operator": {"group_xmlids": ["base.group_user", ENTRY.DATA_OPERATOR_GROUP]},
            "another login": {"login": "admin"},
            "another company": {"company_ids": [1, 2]},
            "shared": {"share": True},
            "archived": {"active": False},
            "interactive": {"has_stored_password": True},
            "api key": {"has_native_api_keys": True},
        }
        for name, override in cases.items():
            with self.subTest(case=name), self.assertRaises(ENTRY.OperatorGrantEntryError):
                ENTRY.assert_readback(
                    dict(READBACK, operator=dict(OPERATOR_STATE, **override)), duty
                )

    def test_a_readback_that_changed_nothing_is_reused(self):
        duty = self._duty()
        fixture = FixtureDeclaration(operator_block())
        self.addCleanup(fixture.close)
        outputs = [
            ENTRY.READBACK_MARKER + json.dumps(READBACK),
            ENTRY.READBACK_MARKER + json.dumps(READBACK),
        ]
        with mock.patch.object(ENTRY, "run_script", side_effect=outputs):
            evidence = self._execute(duty, fixture, "readback")
        self.assertEqual(evidence["action"], "readback")
        self.assertEqual(evidence["entry_report"], {})
        self.assertEqual(evidence["operator_state_before"], evidence["operator_state_after"])

    def test_the_readback_action_refuses_a_changed_state(self):
        duty = self._duty()
        fixture = FixtureDeclaration(operator_block())
        self.addCleanup(fixture.close)
        after = json.loads(json.dumps(READBACK))
        after["operator"]["is_importer"] = True
        outputs = [
            ENTRY.READBACK_MARKER + json.dumps(READBACK),
            ENTRY.READBACK_MARKER + json.dumps(after),
        ]
        with mock.patch.object(ENTRY, "run_script", side_effect=outputs):
            with self.assertRaisesRegex(ENTRY.OperatorGrantEntryError, "changed the duty"):
                self._execute(duty, fixture, "readback")


if __name__ == "__main__":
    unittest.main(verbosity=2)
