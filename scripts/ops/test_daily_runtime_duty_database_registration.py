#!/usr/bin/env python3
"""Focused tests for the daily-duty platform database registration entry.

The registration fact is owned by the platform model, and its only production
writer is the immutable registration entry.  This transport is the governed
runtime binding for the daily profile: it resolves the target from the duty
declaration and the role/strategy vocabulary from the platform's own modules.
These tests therefore cover both sides -- the real declaration must resolve
through the platform module, and the transport must still fail closed when the
target, the confirmation, the reason or the readback is undecided.
"""

from __future__ import annotations

import hashlib
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
    "daily_runtime_duty_database_registration",
    ROOT / "scripts/ops/daily_runtime_duty_database_registration.py",
)
assert SPEC and SPEC.loader
ENTRY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ENTRY)

DECLARATION = ROOT / "config/ops/daily_runtime_database_duties.v1.json"
CUSTOMER_DUTY = "customer_tenant_dev"
CONTROL_DATABASE = "sc_platform_control"
CUSTOMER_DATABASE = "sc_tenant_baosheng_dev"
REASON_TEXT = "owner ruling 2026-10-15 unified onboarding register baosheng dev tenant"
CONFIRM = "REGISTER_DECLARED_DAILY_DUTY_IN_PLATFORM_REGISTRY"

REGISTRATION = {
    "db_name": CUSTOMER_DATABASE,
    "dbfilter": "^%s$" % CUSTOMER_DATABASE,
    "environment_role": "customer_production",
    "strategy": "database_per_customer_tenant",
    "data_purpose": "customer",
    "tenant_key": "baosheng",
    "lifecycle_state": "declared",
    "last_operation": "register",
    "operation_count": 1,
    "maintenance_access_count": 0,
    "grants_business_data_scope": False,
}

REGISTER_OPERATION = {
    "operation": "register",
    "from_state": "",
    "to_state": "declared",
    "actor_login": "admin",
}

READBACK = {
    "mode": "read_only",
    "writes": 0,
    "database": CONTROL_DATABASE,
    "target_database": CUSTOMER_DATABASE,
    "registered": True,
    "registration": dict(REGISTRATION),
    "operations": [dict(REGISTER_OPERATION)],
}
ABSENT = {
    "mode": "read_only",
    "writes": 0,
    "database": CONTROL_DATABASE,
    "target_database": CUSTOMER_DATABASE,
    "registered": False,
    "registration": None,
    "operations": [],
}

ENTRY_RESULT = {
    "ok": True,
    "status": "passed",
    "entry": "platform.database.register",
    "operation_id": 12,
    "db_name": CUSTOMER_DATABASE,
    "environment_role": "customer_production",
    "data_purpose": "customer",
    "reason": REASON_TEXT,
    "initial_state": "declared",
    "strategy": "database_per_customer_tenant",
    "registration_readback": dict(
        REGISTRATION,
        operation_request={"reason": REASON_TEXT, "execution_id": "a" * 32},
    ),
}


def entry_source_sha256() -> str:
    return hashlib.sha256((ROOT / ENTRY.REGISTER_ENTRY_SOURCE).read_bytes()).hexdigest()


class FixtureDeclaration:
    """A declaration with a real ops root and an immutable tool tree."""

    def __init__(self, *, purpose="customer", tenant_key="baosheng", database=CUSTOMER_DATABASE):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        ops_root = self.root / "ops"
        ops_root.mkdir(parents=True, exist_ok=True)
        (ops_root / "duty-stack-20261015.yml").write_text(
            "services:\n  odoo:\n    volumes:\n      - %s\n" % ENTRY.STACK_SCRIPTS_MOUNT,
            encoding="utf-8",
        )
        declaration = json.loads(DECLARATION.read_text(encoding="utf-8"))
        declaration["ops_root"] = str(ops_root)
        for duty in declaration["duties"]:
            if duty["duty"] == CUSTOMER_DUTY:
                duty["data_purpose"] = purpose
                duty["tenant_key"] = tenant_key
                duty["database"] = database
                duty["dbfilter"] = "^%s$" % database
                duty["storage"]["filestore_scope"] = database
        self.path = self.root / "declaration.json"
        self.path.write_text(json.dumps(declaration), encoding="utf-8")
        self.ops_root = ops_root

    def control_duty(self) -> dict:
        return ENTRY.duty_identity.resolve(ENTRY.PLATFORM_CONTROL_DUTY, self.path)

    def stack_path(self) -> Path:
        return self.ops_root / "duty-stack-20261015.yml"

    def tool_root(self) -> Path:
        root = self.root / "tool"
        for relative in (
            ENTRY.REGISTER_ENTRY_SOURCE,
            ENTRY.RECEIPT_SOURCE,
            ENTRY.PROVISIONING_SOURCE,
            ENTRY.GOVERNANCE_SOURCE,
        ):
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(
                (ROOT / relative).read_text(encoding="utf-8"), encoding="utf-8"
            )
        return root

    def close(self):
        self.temporary.cleanup()


class DeclarationTests(unittest.TestCase):
    def test_the_real_declaration_resolves_the_customer_duty(self):
        duty = ENTRY.resolve_registration_target(CUSTOMER_DUTY)
        self.assertEqual(duty["database"], CUSTOMER_DATABASE)
        self.assertEqual(duty["data_purpose"], "customer")
        self.assertEqual(duty["tenant_key"], "baosheng")
        # The role and the strategy are the platform's own vocabulary, not this
        # entry's opinion.
        provisioning = ENTRY.provisioning_policy()
        self.assertEqual(
            duty["environment_role"], provisioning.PURPOSE_ENVIRONMENT_ROLE["customer"]
        )
        self.assertEqual(duty["strategy"], provisioning.PURPOSE_STRATEGY["customer"])

    def test_the_platform_control_duty_is_refused_as_a_data_space(self):
        with self.assertRaisesRegex(
            ENTRY.RegistrationEntryError, "not a registered data purpose"
        ):
            ENTRY.resolve_registration_target(ENTRY.PLATFORM_CONTROL_DUTY)

    def test_an_undeclared_duty_is_rejected(self):
        with self.assertRaises(ENTRY.RegistrationEntryError):
            ENTRY.resolve_registration_target("customer_tenant_missing")

    def test_a_duty_without_a_registered_purpose_is_refused(self):
        fixture = FixtureDeclaration(purpose="platform_control")
        self.addCleanup(fixture.close)
        with self.assertRaisesRegex(
            ENTRY.RegistrationEntryError, "not a registered data purpose"
        ):
            ENTRY.resolve_registration_target(CUSTOMER_DUTY, fixture.path)

    def test_a_customer_duty_must_declare_its_tenant_key(self):
        fixture = FixtureDeclaration(tenant_key="")
        self.addCleanup(fixture.close)
        with self.assertRaisesRegex(ENTRY.RegistrationEntryError, "tenant key"):
            ENTRY.resolve_registration_target(CUSTOMER_DUTY, fixture.path)

    def test_the_entry_hardcodes_no_duty_identity(self):
        source = (
            ROOT / "scripts/ops/daily_runtime_duty_database_registration.py"
        ).read_text()
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

    def test_the_entry_hardcodes_no_environment_role_or_strategy(self):
        """The role and strategy must come from the platform vocabulary."""
        source = (
            ROOT / "scripts/ops/daily_runtime_duty_database_registration.py"
        ).read_text()
        provisioning = ENTRY.provisioning_policy()
        for purpose in provisioning.PURPOSE_STRATEGY:
            self.assertNotIn(provisioning.PURPOSE_ENVIRONMENT_ROLE[purpose], source)
            self.assertNotIn(provisioning.PURPOSE_STRATEGY[purpose], source)

    def test_only_a_write_action_needs_a_confirmation(self):
        self.assertEqual(ENTRY.ACTIONS, ("readback", "register"))
        self.assertEqual(list(ENTRY.CONFIRMATIONS), ["register"])


class ReasonTests(unittest.TestCase):
    def test_the_registration_reason_is_required_and_bounded(self):
        for value in ("", "short", "x" * 201, "line\nbreak", "quote\"mark", None):
            with self.subTest(value=value), self.assertRaises(ENTRY.RegistrationEntryError):
                ENTRY.registration_reason(value)
        self.assertEqual(ENTRY.registration_reason(REASON_TEXT), REASON_TEXT)


class ScriptTests(unittest.TestCase):
    def _duty(self, fixture=None):
        if fixture is None:
            return ENTRY.resolve_registration_target(CUSTOMER_DUTY)
        return ENTRY.resolve_registration_target(CUSTOMER_DUTY, fixture.path)

    def test_the_readback_script_binds_the_target_database(self):
        duty = self._duty()
        script = ENTRY.readback_script(duty)
        compile(script, "<readback>", "exec")
        self.assertIn('"target_database": "%s"' % CUSTOMER_DATABASE, script)
        self.assertIn("sc.platform.database.registration", script)
        self.assertNotIn(ENTRY.DATABASE_TOKEN, script)

    def test_the_register_script_binds_the_product_scripts_mount(self):
        script = ENTRY.register_script()
        compile(script, "<register>", "exec")
        self.assertIn(
            'sys.path.insert(0, "%s")' % str(Path(ENTRY.PRODUCT_SCRIPTS_MOUNT).parent), script
        )
        self.assertIn("scripts.ops.platform_database_register", script)
        self.assertNotIn(ENTRY.MOUNT_TOKEN, script)

    def test_the_register_script_loads_the_module_the_entry_declares(self):
        """The template carries the placeholder and the constant is its only
        source, so the loaded module and the declared module cannot drift."""
        source = (
            ROOT / "scripts/ops/daily_runtime_duty_database_registration.py"
        ).read_text()
        self.assertIn('importlib.import_module("%(module)s")', source)
        self.assertIn(
            'importlib.import_module("%s")' % ENTRY.REGISTER_ENTRY_MODULE,
            ENTRY.REGISTER_SCRIPT,
        )

    def test_the_reviewed_stack_must_expose_the_scripts_mount(self):
        fixture = FixtureDeclaration()
        self.addCleanup(fixture.close)
        ENTRY.assert_scripts_mount(fixture.stack_path())
        missing = fixture.root / "duty-stack-other.yml"
        missing.write_text("services:\n  odoo:\n    volumes: []\n", encoding="utf-8")
        with self.assertRaisesRegex(ENTRY.RegistrationEntryError, "does not mount"):
            ENTRY.assert_scripts_mount(missing)

    def test_the_register_command_shells_in_control_and_declares_the_duty(self):
        """The register shell runs in the control plane; the fact it declares is
        the duty's database.  Swapping the two would write the registration into
        the tenant database, so both halves are asserted against each other."""
        fixture = FixtureDeclaration()
        self.addCleanup(fixture.close)
        duty = self._duty(fixture)
        control = fixture.control_duty()
        command = ENTRY.register_command(
            control,
            ["docker", "compose", "--project-name", control["compose_project"]],
            ENTRY.register_environment(duty, ENTRY.register_entry(), REASON_TEXT),
        )
        self.assertEqual(command[command.index("-d") + 1], CONTROL_DATABASE)
        self.assertEqual(command[command.index("-d") + 1], control["database"])
        self.assertNotEqual(control["database"], duty["database"])
        # The one write targets the declared duty, never the control plane.
        self.assertIn("PLATFORM_DATABASE_REGISTER_DB=%s" % CUSTOMER_DATABASE, command)
        self.assertNotIn("PLATFORM_DATABASE_REGISTER_DB=%s" % CONTROL_DATABASE, command)
        self.assertEqual(command[command.index("--entrypoint") + 1], ENTRY.duty_runtime.APPLICATION_ENTRY)
        self.assertIn("--no-deps", command)
        self.assertIn("--rm", command)
        for expected in (
            "SC_CONFIRM_PLATFORM_DATABASE_REGISTRY=REGISTER_GOVERNED_PLATFORM_DATABASE",
            "PLATFORM_DATABASE_REGISTER_ENVIRONMENT_ROLE=customer_production",
            "PLATFORM_DATABASE_REGISTER_DATA_PURPOSE=customer",
            "PLATFORM_DATABASE_REGISTER_TENANT_KEY=baosheng",
            "PLATFORM_DATABASE_REGISTER_DBFILTER=^%s$" % CUSTOMER_DATABASE,
            "PLATFORM_DATABASE_REGISTER_REASON=%s" % REASON_TEXT,
        ):
            self.assertIn(expected, command)
        self.assertFalse([row for row in command if row.startswith("PLATFORM_DATABASE_REGISTER_OUTPUT")])

    def test_the_readback_command_runs_in_the_control_database(self):
        fixture = FixtureDeclaration()
        self.addCleanup(fixture.close)
        control = fixture.control_duty()
        command = ENTRY.readback_command(
            control, ["docker", "compose", "--project-name", control["compose_project"]]
        )
        self.assertEqual(command[command.index("-d") + 1], CONTROL_DATABASE)
        self.assertIn("--no-http", command)
        self.assertFalse([row for row in command if row.startswith("-e")])


class GuardTests(unittest.TestCase):
    def _duty(self):
        return ENTRY.resolve_registration_target(CUSTOMER_DUTY)

    def _execute(self, fixture, action, **kwargs):
        control = fixture.control_duty()
        original_resolve = ENTRY.duty_identity.resolve

        def _resolve(name, path=None):
            if name == ENTRY.PLATFORM_CONTROL_DUTY:
                return control
            return original_resolve(name, path)

        with mock.patch.object(
            ENTRY.duty_runtime, "read_duty_env", return_value={"ODOO_IMAGE": "odoo17-odoo:latest"}
        ), mock.patch.object(
            ENTRY.duty_runtime, "stack_compose_path", return_value=fixture.stack_path()
        ), mock.patch.object(
            ENTRY.duty_runtime, "inspect_odoo_container", return_value={}
        ), mock.patch.object(
            ENTRY.duty_identity, "resolve", side_effect=_resolve
        ):
            return ENTRY.execute(
                CUSTOMER_DUTY,
                action=action,
                declaration=fixture.path,
                tool_root=fixture.tool_root(),
                **kwargs,
            )

    def test_every_write_action_requires_its_exact_confirmation(self):
        fixture = FixtureDeclaration()
        self.addCleanup(fixture.close)
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(
                ENTRY.RegistrationEntryError, "CONFIRM_DAILY_DUTY_DATABASE_REGISTRATION"
            ):
                self._execute(fixture, "register", reason=REASON_TEXT)

    def test_the_register_action_without_a_reason_is_refused(self):
        fixture = FixtureDeclaration()
        self.addCleanup(fixture.close)
        with mock.patch.dict(
            os.environ, {"CONFIRM_DAILY_DUTY_DATABASE_REGISTRATION": CONFIRM}, clear=True
        ):
            with self.assertRaisesRegex(ENTRY.RegistrationEntryError, "why this database"):
                self._execute(fixture, "register")

    def test_an_unsupported_action_is_refused(self):
        with self.assertRaisesRegex(ENTRY.RegistrationEntryError, "unsupported"):
            ENTRY.execute(CUSTOMER_DUTY, action="retire")

    def test_the_control_plane_is_never_the_registration_target(self):
        duty = self._duty()
        duty["database"] = CONTROL_DATABASE
        with mock.patch.object(ENTRY, "resolve_registration_target", return_value=duty):
            with self.assertRaisesRegex(
                ENTRY.RegistrationEntryError, "never registers the platform control plane"
            ):
                ENTRY.execute(CUSTOMER_DUTY, action="readback")

    def test_the_readback_action_reports_an_absent_registration(self):
        fixture = FixtureDeclaration()
        self.addCleanup(fixture.close)
        outputs = [
            ENTRY.READBACK_MARKER + json.dumps(ABSENT),
            ENTRY.READBACK_MARKER + json.dumps(ABSENT),
        ]
        with mock.patch.object(ENTRY, "run_script", side_effect=outputs):
            evidence = self._execute(fixture, "readback")
        self.assertEqual(evidence["action"], "readback")
        self.assertIs(evidence["registered_before"], False)
        self.assertIs(evidence["created"], False)
        self.assertEqual(evidence["entry_report"], {})

    def test_the_readback_action_refuses_a_changed_state(self):
        fixture = FixtureDeclaration()
        self.addCleanup(fixture.close)
        changed = json.loads(json.dumps(ABSENT))
        changed["registered"] = True
        changed["registration"] = dict(REGISTRATION)
        outputs = [
            ENTRY.READBACK_MARKER + json.dumps(ABSENT),
            ENTRY.READBACK_MARKER + json.dumps(changed),
        ]
        with mock.patch.object(ENTRY, "run_script", side_effect=outputs):
            with self.assertRaisesRegex(ENTRY.RegistrationEntryError, "changed the duty"):
                self._execute(fixture, "readback")

    def test_registration_reuses_an_existing_identical_row_without_writing(self):
        fixture = FixtureDeclaration()
        self.addCleanup(fixture.close)
        marker = ENTRY.READBACK_MARKER + json.dumps(READBACK)
        with mock.patch.dict(
            os.environ, {"CONFIRM_DAILY_DUTY_DATABASE_REGISTRATION": CONFIRM}, clear=True
        ), mock.patch.object(ENTRY, "run_script", side_effect=[marker, marker]) as runner:
            evidence = self._execute(fixture, "register", reason=REASON_TEXT)
        self.assertIs(evidence["registered_before"], True)
        self.assertIs(evidence["created"], False)
        self.assertEqual(runner.call_count, 2)  # readback before and after only

    def test_a_registry_that_moved_without_a_write_is_refused(self):
        """A reuse path that did not write must leave the registry unmoved.

        The moved row still satisfies every declared fact, so only the
        before/after comparison can catch it: this is the counter-example for
        the stability check that guards the no-write path.
        """
        fixture = FixtureDeclaration()
        self.addCleanup(fixture.close)
        before = ENTRY.READBACK_MARKER + json.dumps(READBACK)
        moved = json.loads(json.dumps(READBACK))
        moved["registration"]["operation_count"] = 2
        self.assertNotEqual(moved, READBACK)
        after = ENTRY.READBACK_MARKER + json.dumps(moved)
        with mock.patch.dict(
            os.environ, {"CONFIRM_DAILY_DUTY_DATABASE_REGISTRATION": CONFIRM}, clear=True
        ), mock.patch.object(ENTRY, "run_script", side_effect=[before, after]) as runner:
            with self.assertRaisesRegex(
                ENTRY.RegistrationEntryError, "although this run refused to write"
            ):
                self._execute(fixture, "register", reason=REASON_TEXT)
        self.assertEqual(runner.call_count, 2)  # the entry was never invoked

    def test_a_registration_is_asserted_against_the_entry_and_the_declaration(self):
        fixture = FixtureDeclaration()
        self.addCleanup(fixture.close)
        entry_output = ENTRY.ENTRY_MARKER + json.dumps(
            {"source_sha256": entry_source_sha256(), "result": ENTRY_RESULT}
        )
        outputs = [
            ENTRY.READBACK_MARKER + json.dumps(ABSENT),
            entry_output,
            ENTRY.READBACK_MARKER + json.dumps(READBACK),
        ]
        with mock.patch.dict(
            os.environ, {"CONFIRM_DAILY_DUTY_DATABASE_REGISTRATION": CONFIRM}, clear=True
        ), mock.patch.object(ENTRY, "run_script", side_effect=outputs):
            evidence = self._execute(fixture, "register", reason=REASON_TEXT)
        self.assertIs(evidence["created"], True)
        self.assertEqual(evidence["environment_role"], "customer_production")
        self.assertEqual(evidence["registration_after"]["registration"]["db_name"], CUSTOMER_DATABASE)

    def test_the_register_action_shells_in_control_and_declares_the_duty(self):
        """The command the action really runs must shell in the control database
        while declaring the duty's database.  Swapping those two would register
        the tenant database from inside itself, so both halves are asserted
        against the commands the run actually carried."""
        fixture = FixtureDeclaration()
        self.addCleanup(fixture.close)
        entry_output = ENTRY.ENTRY_MARKER + json.dumps(
            {"source_sha256": entry_source_sha256(), "result": ENTRY_RESULT}
        )
        outputs = [
            ENTRY.READBACK_MARKER + json.dumps(ABSENT),
            entry_output,
            ENTRY.READBACK_MARKER + json.dumps(READBACK),
        ]
        commands: list[list[str]] = []

        def _record(command, script, ops_root):
            commands.append(list(command))
            return outputs[len(commands) - 1]

        with mock.patch.dict(
            os.environ, {"CONFIRM_DAILY_DUTY_DATABASE_REGISTRATION": CONFIRM}, clear=True
        ), mock.patch.object(ENTRY, "run_script", side_effect=_record):
            evidence = self._execute(fixture, "register", reason=REASON_TEXT)
        self.assertIs(evidence["created"], True)
        self.assertEqual(len(commands), 3)  # readback, register, readback
        self.assertEqual(
            [command[command.index("-d") + 1] for command in commands],
            [CONTROL_DATABASE] * 3,
        )
        register = commands[1]
        self.assertIn("PLATFORM_DATABASE_REGISTER_DB=%s" % CUSTOMER_DATABASE, register)
        self.assertNotIn("PLATFORM_DATABASE_REGISTER_DB=%s" % CONTROL_DATABASE, register)

    def test_a_registration_that_landed_another_identity_is_refused(self):
        fixture = FixtureDeclaration()
        self.addCleanup(fixture.close)
        entry_output = ENTRY.ENTRY_MARKER + json.dumps(
            {"source_sha256": entry_source_sha256(), "result": ENTRY_RESULT}
        )
        tampered = json.loads(json.dumps(READBACK))
        tampered["registration"]["tenant_key"] = "another"
        outputs = [
            ENTRY.READBACK_MARKER + json.dumps(ABSENT),
            entry_output,
            ENTRY.READBACK_MARKER + json.dumps(tampered),
        ]
        with mock.patch.dict(
            os.environ, {"CONFIRM_DAILY_DUTY_DATABASE_REGISTRATION": CONFIRM}, clear=True
        ), mock.patch.object(ENTRY, "run_script", side_effect=outputs):
            with self.assertRaisesRegex(ENTRY.RegistrationEntryError, "tenant_key"):
                self._execute(fixture, "register", reason=REASON_TEXT)

    def test_the_entry_report_from_another_source_is_refused(self):
        fixture = FixtureDeclaration()
        self.addCleanup(fixture.close)
        entry_output = ENTRY.ENTRY_MARKER + json.dumps(
            {"source_sha256": "b" * 64, "result": ENTRY_RESULT}
        )
        outputs = [
            ENTRY.READBACK_MARKER + json.dumps(ABSENT),
            entry_output,
            ENTRY.READBACK_MARKER + json.dumps(READBACK),
        ]
        with mock.patch.dict(
            os.environ, {"CONFIRM_DAILY_DUTY_DATABASE_REGISTRATION": CONFIRM}, clear=True
        ), mock.patch.object(ENTRY, "run_script", side_effect=outputs):
            with self.assertRaisesRegex(ENTRY.RegistrationEntryError, "not the immutable one"):
                self._execute(fixture, "register", reason=REASON_TEXT)

    def test_a_register_entry_that_registered_another_reason_is_refused(self):
        fixture = FixtureDeclaration()
        self.addCleanup(fixture.close)
        result = json.loads(json.dumps(ENTRY_RESULT))
        result["registration_readback"]["operation_request"]["reason"] = "another reason"
        entry_output = ENTRY.ENTRY_MARKER + json.dumps(
            {"source_sha256": entry_source_sha256(), "result": result}
        )
        outputs = [
            ENTRY.READBACK_MARKER + json.dumps(ABSENT),
            entry_output,
            ENTRY.READBACK_MARKER + json.dumps(READBACK),
        ]
        with mock.patch.dict(
            os.environ, {"CONFIRM_DAILY_DUTY_DATABASE_REGISTRATION": CONFIRM}, clear=True
        ), mock.patch.object(ENTRY, "run_script", side_effect=outputs):
            with self.assertRaisesRegex(ENTRY.RegistrationEntryError, "this run's reason"):
                self._execute(fixture, "register", reason=REASON_TEXT)


class ReadbackTests(unittest.TestCase):
    def setUp(self):
        self.fixture = FixtureDeclaration()
        self.addCleanup(self.fixture.close)
        self.duty = ENTRY.resolve_registration_target(CUSTOMER_DUTY, self.fixture.path)
        self.control = self.fixture.control_duty()

    def test_readback_rejects_a_write_or_another_control_database(self):
        for tampered, message in (
            (dict(READBACK, writes=1), "read-only"),
            (dict(READBACK, mode="write"), "read-only"),
            (dict(READBACK, database="sc_demo"), "another control database"),
            (dict(READBACK, target_database="sc_demo"), "another database than the duty's"),
            (dict(READBACK, registered="yes"), "whether the database is registered"),
        ):
            with self.subTest(message=message):
                with self.assertRaisesRegex(ENTRY.RegistrationEntryError, message):
                    ENTRY.assert_readback(tampered, self.duty, self.control)

    def test_readback_rejects_a_registration_outside_the_declaration(self):
        cases = {
            "db_name": "sc_demo",
            "dbfilter": "^sc_demo$",
            "data_purpose": "demo",
            "environment_role": "platform_internal_demo",
            "strategy": "single_db_multi_company",
            "tenant_key": "other",
            "lifecycle_state": "invented",
        }
        for key, value in cases.items():
            with self.subTest(key=key), self.assertRaises(ENTRY.RegistrationEntryError):
                ENTRY.assert_readback(
                    dict(READBACK, registration=dict(REGISTRATION, **{key: value})),
                    self.duty,
                    self.control,
                )

    def test_readback_rejects_a_business_data_scope_claim(self):
        with self.assertRaisesRegex(ENTRY.RegistrationEntryError, "business data scope"):
            ENTRY.assert_readback(
                dict(
                    READBACK,
                    registration=dict(REGISTRATION, grants_business_data_scope=True),
                ),
                self.duty,
                self.control,
            )

    def test_readback_rejects_a_history_the_entry_did_not_write(self):
        for operations in ([], [dict(REGISTER_OPERATION), dict(REGISTER_OPERATION)], None):
            with self.subTest(operations=operations), self.assertRaises(
                ENTRY.RegistrationEntryError
            ):
                ENTRY.assert_readback(
                    dict(READBACK, operations=operations), self.duty, self.control
                )
        with self.assertRaisesRegex(ENTRY.RegistrationEntryError, "initial state"):
            ENTRY.assert_readback(
                dict(READBACK, operations=[dict(REGISTER_OPERATION, to_state="active")]),
                self.duty,
                self.control,
            )

    def test_readback_accepts_an_honest_absent_registration(self):
        self.assertIs(ENTRY.assert_readback(ABSENT, self.duty, self.control), False)
        with self.assertRaisesRegex(ENTRY.RegistrationEntryError, "not registered"):
            ENTRY.assert_readback(ABSENT, self.duty, self.control, registered=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
