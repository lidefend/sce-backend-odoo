#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Focused tests for the security-administrator bootstrap runtime binding.

The bootstrap entry owns the decision; this transport owns the runtime binding
that gives it an exact control-plane identity.  These tests cover both sides:
the real declaration must resolve the control duty, the rendered scripts must
load the entry from the reviewed mount, and the transport must still fail closed
when the confirmation, the readback or the entry's own receipt is undecided.
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
    "daily_runtime_platform_security_admin_bootstrap",
    ROOT / "scripts/ops/daily_runtime_platform_security_admin_bootstrap.py",
)
assert SPEC and SPEC.loader
ENTRY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ENTRY)

DECLARATION = ROOT / "config/ops/daily_runtime_database_duties.v1.json"
CONTROL_DATABASE = "sc_platform_control"
LOGIN = "lidefend"
NAME = "Li Defend"
EVIDENCE = "owner ruling 2026-10-16 names lidefend as the platform security admin"
DIGEST = "a" * 64


def entry_module():
    return ENTRY.bootstrap_entry(ROOT)


def request():
    return {
        "login": LOGIN,
        "name": NAME,
        "evidence": EVIDENCE,
        "output": ENTRY.REMOTE_OUTPUT,
    }


def readback(**overrides):
    values = {
        "mode": "read_only",
        "writes": 0,
        "database": CONTROL_DATABASE,
        "declared_login": LOGIN,
        "declared_name": NAME,
        "evidence": EVIDENCE,
        "security_admin_group_exists": True,
        "security_admin_member_count": 0,
        "maintenance_access_rows": 0,
        "approves_maintenance_access": False,
        "allowed_group_closure_ids": [2, 14, 16],
        "allowed_group_closure_complete": True,
        "exists": False,
        "identity": None,
    }
    values.update(overrides)
    return values


def control():
    return {"duty": "platform_control", "database": CONTROL_DATABASE}


def entry_result(**overrides):
    values = {
        "ok": True,
        "status": "passed",
        "entry": entry_module().ENTRY,
        "login": LOGIN,
        "name": NAME,
        "created": True,
        "writes": 1,
        "group_xmlid": entry_module().SECURITY_ADMIN_GROUP_XMLID,
        "identity_readback": {
            "uid": 7,
            "login": LOGIN,
            "name": NAME,
            "active": True,
            "share": False,
            "is_security_admin": True,
            "has_stored_password": False,
            "group_ids": [2, 14, 16],
            "group_xmlids": ["base.group_user", entry_module().SECURITY_ADMIN_GROUP_XMLID],
            "groups_outside_allowed_closure": [],
        },
        "security_admin_member_count": 1,
        "maintenance_access_rows": 0,
        "approves_maintenance_access": False,
        "identity_groups_outside_allowed_closure": [],
        "effects": {"commit_state": "not_attempted", "uid": 7},
    }
    values.update(overrides)
    return values


class FixtureDeclaration:
    """A declaration with a real ops root and one rendered duty stack."""

    def __init__(self, *, purpose=None, mount=True, symlink=False):
        self.temporary = tempfile.TemporaryDirectory()
        self.ops_root = Path(self.temporary.name)
        declaration = json.loads(DECLARATION.read_text(encoding="utf-8"))
        declaration["ops_root"] = str(self.ops_root)
        for duty in declaration["duties"]:
            if (purpose and duty["duty"] in ("platform_control", "demo", "customer_tenant_dev")):
                duty["data_purpose"] = purpose
        self.path = self.ops_root / "duties.json"
        self.path.write_text(json.dumps(declaration, ensure_ascii=False), encoding="utf-8")
        self.stack = self.ops_root / "duty-stack-20261015.yml"
        body = "services:\n  odoo:\n    volumes:\n      - %s\n" % ENTRY.STACK_SCRIPTS_MOUNT
        if symlink:
            real = self.ops_root / "real-stack.yml"
            real.write_text(body, encoding="utf-8")
            self.stack.symlink_to(real)
        elif mount:
            self.stack.write_text(body, encoding="utf-8")
        else:
            self.stack.write_text("services:\n  odoo:\n    volumes: []\n", encoding="utf-8")

    def cleanup(self):
        self.temporary.cleanup()


class DutyResolutionTests(unittest.TestCase):
    def test_the_real_declaration_resolves_the_platform_control_duty(self):
        duty = ENTRY.resolve_control_duty(DECLARATION)
        self.assertEqual(duty["duty"], "platform_control")
        self.assertEqual(duty["database"], CONTROL_DATABASE)
        self.assertEqual(duty["data_purpose"], "platform_control")

    def test_the_control_duty_cannot_become_a_data_space(self):
        fixture = FixtureDeclaration(purpose="customer")
        self.addCleanup(fixture.cleanup)
        with self.assertRaisesRegex(ENTRY.BootstrapTransportError, "not platform_control"):
            ENTRY.resolve_control_duty(fixture.path)

    def test_the_transport_hardcodes_no_database_or_login(self):
        text = (ROOT / "scripts/ops/daily_runtime_platform_security_admin_bootstrap.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn('"sc_platform_control"', text)
        self.assertNotIn('"lidefend"', text)


class RequestAndConfirmationTests(unittest.TestCase):
    def test_a_declared_request_validates(self):
        resolved = ENTRY.declare_request(entry_module(), login=LOGIN, name=NAME, evidence=EVIDENCE)
        self.assertEqual(resolved["login"], LOGIN)
        self.assertEqual(resolved["output"], ENTRY.REMOTE_OUTPUT)

    def test_the_entrys_own_rules_reject_a_shared_login(self):
        with self.assertRaisesRegex(ENTRY.BootstrapTransportError, "NOT_AN_APPROVER"):
            ENTRY.declare_request(entry_module(), login="admin", name=NAME, evidence=EVIDENCE)

    def test_the_entrys_own_rules_reject_missing_evidence(self):
        with self.assertRaisesRegex(ENTRY.BootstrapTransportError, "EVIDENCE_REQUIRED"):
            ENTRY.declare_request(entry_module(), login=LOGIN, name=NAME, evidence="x")

    def test_a_readback_needs_no_confirmation(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(ENTRY.confirmation(entry_module(), "readback"), "")

    def test_the_write_action_requires_its_exact_confirmation(self):
        module = entry_module()
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ENTRY.BootstrapTransportError, "exact confirmation"):
                ENTRY.confirmation(module, "bootstrap")
        with mock.patch.dict(os.environ, {module.CONFIRM_ENV: "yes"}, clear=True):
            with self.assertRaisesRegex(ENTRY.BootstrapTransportError, "exact confirmation"):
                ENTRY.confirmation(module, "bootstrap")
        with mock.patch.dict(os.environ, {module.CONFIRM_ENV: module.CONFIRM_VALUE}, clear=True):
            self.assertEqual(ENTRY.confirmation(module, "bootstrap"), module.CONFIRM_VALUE)


class MountAndTemplateTests(unittest.TestCase):
    def test_the_reviewed_stack_must_expose_the_scripts_mount(self):
        fixture = FixtureDeclaration()
        self.addCleanup(fixture.cleanup)
        ENTRY.assert_scripts_mount(fixture.stack)
        without = FixtureDeclaration(mount=False)
        self.addCleanup(without.cleanup)
        with self.assertRaisesRegex(ENTRY.BootstrapTransportError, "does not mount"):
            ENTRY.assert_scripts_mount(without.stack)
        linked = FixtureDeclaration(symlink=True)
        self.addCleanup(linked.cleanup)
        with self.assertRaisesRegex(ENTRY.BootstrapTransportError, "unavailable"):
            ENTRY.assert_scripts_mount(linked.stack)

    def test_the_rendered_readback_loads_the_entry_from_the_mount(self):
        script = ENTRY.readback_script(entry_module())
        self.assertIn(ENTRY.BOOTSTRAP_ENTRY_MODULE, script)
        self.assertIn(ENTRY.READBACK_MARKER, script)
        self.assertIn('"%s"' % str(Path(ENTRY.PRODUCT_SCRIPTS_MOUNT).parent), script)
        self.assertNotIn(ENTRY.MOUNT_TOKEN, script)
        self.assertIn("_entry.readback(", script)
        compile(script, "<readback>", "exec")

    def test_the_rendered_entry_calls_the_entry_once(self):
        script = ENTRY.entry_script()
        self.assertIn(ENTRY.BOOTSTRAP_ENTRY_MODULE, script)
        self.assertIn(ENTRY.ENTRY_MARKER, script)
        self.assertIn("source_sha256", script)
        self.assertNotIn(ENTRY.MOUNT_TOKEN, script)
        compile(script, "<entry>", "exec")

    def test_the_entry_environment_carries_only_declared_inputs(self):
        module = entry_module()
        environment = ENTRY.entry_environment(module, request(), "b" * 32)
        joined = "\n".join(environment)
        self.assertIn("%s=%s" % (module.CONFIRM_ENV, module.CONFIRM_VALUE), joined)
        self.assertIn("PLATFORM_DATABASE_EXECUTION_ID=%s" % ("b" * 32,), joined)
        self.assertNotIn("APPROVED_BY", joined)
        self.assertNotIn("PASSWORD", joined.upper())


class ReadbackAssertionTests(unittest.TestCase):
    def test_a_readback_for_another_database_is_refused(self):
        with self.assertRaisesRegex(ENTRY.BootstrapTransportError, "another control database"):
            ENTRY.assert_readback(readback(database="sc_demo"), entry_module(), request(), control())

    def test_a_readback_that_wrote_is_refused(self):
        with self.assertRaisesRegex(ENTRY.BootstrapTransportError, "read-only"):
            ENTRY.assert_readback(readback(writes=1), entry_module(), request(), control())

    def test_a_readback_for_another_login_is_refused(self):
        with self.assertRaisesRegex(ENTRY.BootstrapTransportError, "another login"):
            ENTRY.assert_readback(
                readback(declared_login="someone_else"), entry_module(), request(), control()
            )

    def test_a_readback_without_the_group_is_refused(self):
        with self.assertRaisesRegex(ENTRY.BootstrapTransportError, "security-administrator group"):
            ENTRY.assert_readback(
                readback(security_admin_group_exists=False), entry_module(), request(), control()
            )

    def test_an_honest_absent_readback_is_accepted(self):
        report = ENTRY.assert_readback(readback(), entry_module(), request(), control())
        self.assertIs(report["exists"], False)
        self.assertIsNone(report["identity"])


class EntryResultTests(unittest.TestCase):
    def _assert(self, values, before=None):
        return ENTRY.assert_entry_result(
            {"source_sha256": DIGEST, "result": values},
            entry_module(),
            request(),
            DIGEST,
            before if before is not None else readback(),
        )

    def test_the_entry_receipt_must_come_from_the_reviewed_source(self):
        with self.assertRaisesRegex(ENTRY.BootstrapTransportError, "another security-administrator entry"):
            ENTRY.assert_entry_result(
                {"source_sha256": "b" * 64, "result": entry_result()},
                entry_module(),
                request(),
                DIGEST,
                readback(),
            )

    def test_an_uncommitted_entry_result_is_refused(self):
        with self.assertRaisesRegex(ENTRY.BootstrapTransportError, "committed success"):
            self._assert(entry_result(ok=False))
        with self.assertRaisesRegex(ENTRY.BootstrapTransportError, "did not pass"):
            self._assert(entry_result(status="pending"))

    def test_an_entry_that_established_another_identity_is_refused(self):
        with self.assertRaisesRegex(ENTRY.BootstrapTransportError, "another login"):
            self._assert(entry_result(login="someone_else"))

    def test_an_entry_that_granted_another_group_is_refused(self):
        with self.assertRaisesRegex(ENTRY.BootstrapTransportError, "another group"):
            self._assert(entry_result(group_xmlid="base.group_user"))

    def test_an_entry_that_approved_a_maintenance_access_is_refused(self):
        with self.assertRaisesRegex(ENTRY.BootstrapTransportError, "approved a maintenance access"):
            self._assert(entry_result(approves_maintenance_access=True))

    def test_an_entry_that_reported_a_widened_identity_is_refused(self):
        with self.assertRaisesRegex(ENTRY.BootstrapTransportError, "approver closure"):
            self._assert(
                entry_result(
                    identity_groups_outside_allowed_closure=[
                        "smart_construction_core.group_sc_contract_manager"
                    ]
                )
            )

    def test_an_entry_that_did_not_report_the_group_closure_is_refused(self):
        payload = entry_result()
        payload.pop("identity_groups_outside_allowed_closure")
        with self.assertRaisesRegex(ENTRY.BootstrapTransportError, "group closure"):
            self._assert(payload)

    def test_an_entry_that_moved_the_authorization_ledger_is_refused(self):
        with self.assertRaisesRegex(ENTRY.BootstrapTransportError, "authorization ledger"):
            self._assert(entry_result(maintenance_access_rows=1))

    def test_an_identity_that_is_not_a_security_admin_is_refused(self):
        with self.assertRaisesRegex(ENTRY.BootstrapTransportError, "not a control-plane security administrator"):
            self._assert(
                entry_result(identity_readback={"is_security_admin": False, "active": True, "share": False})
            )

    def test_an_identity_that_carries_a_credential_is_refused(self):
        identity = dict(entry_result()["identity_readback"], has_stored_password=True)
        with self.assertRaisesRegex(ENTRY.BootstrapTransportError, "stored credential"):
            self._assert(entry_result(identity_readback=identity))

    def test_an_identity_that_carries_unrelated_groups_is_refused(self):
        identity = dict(
            entry_result()["identity_readback"],
            groups_outside_allowed_closure=["smart_construction_core.group_sc_contract_manager"],
        )
        with self.assertRaisesRegex(ENTRY.BootstrapTransportError, "outside the approver closure"):
            self._assert(entry_result(identity_readback=identity))

    def test_an_identity_that_is_not_the_declared_named_person_is_refused(self):
        identity = dict(entry_result()["identity_readback"], name="Someone Else")
        with self.assertRaisesRegex(ENTRY.BootstrapTransportError, "declared named person"):
            self._assert(entry_result(identity_readback=identity))

    def test_an_identity_that_is_a_portal_or_inactive_is_refused(self):
        with self.assertRaisesRegex(ENTRY.BootstrapTransportError, "active internal account"):
            self._assert(entry_result(identity_readback=dict(entry_result()["identity_readback"], share=True)))
        with self.assertRaisesRegex(ENTRY.BootstrapTransportError, "active internal account"):
            self._assert(entry_result(identity_readback=dict(entry_result()["identity_readback"], active=False)))

    def test_a_creation_without_a_write_is_refused(self):
        with self.assertRaisesRegex(ENTRY.BootstrapTransportError, "creation without a write"):
            self._assert(entry_result(writes=0))

    def test_a_receipt_without_an_audited_identity_is_refused(self):
        with self.assertRaisesRegex(ENTRY.BootstrapTransportError, "audited identity"):
            self._assert(entry_result(effects={"commit_state": "not_attempted"}))

    def test_an_honest_creation_is_accepted(self):
        result = self._assert(entry_result())
        self.assertTrue(result["created"])
        self.assertEqual(result["writes"], 1)
        reused = self._assert(entry_result(created=False, writes=0))
        self.assertFalse(reused["created"])


class PostCreationTests(unittest.TestCase):
    def identity_report(self, **identity_overrides):
        module = entry_module()
        identity = {
            "login": LOGIN,
            "name": NAME,
            "active": True,
            "share": False,
            "is_security_admin": True,
            "has_stored_password": False,
            "group_ids": [2, 14, 16],
            "group_xmlids": ["base.group_user", module.SECURITY_ADMIN_GROUP_XMLID],
            "groups_outside_allowed_closure": [],
        }
        identity.update(identity_overrides)
        return readback(exists=True, identity=identity)

    def test_the_identity_must_be_readable_after_creation(self):
        with self.assertRaisesRegex(ENTRY.BootstrapTransportError, "not readable after"):
            ENTRY.assert_identity_after_creation(readback(), entry_module(), request(), entry_result())

    def test_the_identity_must_carry_the_group_exactly_once(self):
        report = self.identity_report(group_xmlids=[])
        with self.assertRaisesRegex(ENTRY.BootstrapTransportError, "exactly once"):
            ENTRY.assert_identity_after_creation(report, entry_module(), request(), entry_result())

    def test_the_identity_must_carry_the_declared_name_after_creation(self):
        report = self.identity_report(name="Someone Else")
        with self.assertRaisesRegex(ENTRY.BootstrapTransportError, "another name"):
            ENTRY.assert_identity_after_creation(report, entry_module(), request(), entry_result())

    def test_the_identity_must_stay_inside_the_approver_closure(self):
        report = self.identity_report(
            groups_outside_allowed_closure=["smart_construction_core.group_sc_contract_manager"]
        )
        with self.assertRaisesRegex(ENTRY.BootstrapTransportError, "outside the approver closure"):
            ENTRY.assert_identity_after_creation(report, entry_module(), request(), entry_result())

    def test_an_honest_created_identity_is_accepted(self):
        ENTRY.assert_identity_after_creation(
            self.identity_report(), entry_module(), request(), entry_result()
        )


class MakeTargetTests(unittest.TestCase):
    """The daily entry points are wired, and they guard their inputs first."""

    def setUp(self):
        self.make = (ROOT / "make/daily_candidate.mk").read_text(encoding="utf-8")

    def test_the_bootstrap_targets_are_declared(self):
        for target in (
            "daily.runtime.platform.security_admin.bootstrap.remote_install:",
            "daily.runtime.platform.security_admin.bootstrap.remote_readback:",
            "daily.runtime.platform.security_admin.bootstrap.remote_bootstrap:",
            "verify.platform.security_admin.bootstrap:",
        ):
            self.assertIn(target, self.make)

    def test_each_remote_entry_validates_name_and_evidence_before_connecting(self):
        # A name or an evidence reference travels through the ssh payload as a
        # shell argument, so both remote entries refuse the characters that
        # would break out of it before the connection is made.
        self.assertEqual(self.make.count("it would break the ssh payload"), 4)
        self.assertEqual(self.make.count("{2,200}$$'"), 2)
        self.assertEqual(self.make.count("{10,400}$$'"), 2)

    def test_the_bootstrap_reuses_the_declared_identity_binding(self):
        self.assertIn("bootstrap --login \"$(DAILY_SECURITY_ADMIN_LOGIN)\"", self.make)
        self.assertIn("readback --login \"$(DAILY_SECURITY_ADMIN_LOGIN)\"", self.make)


if __name__ == "__main__":
    unittest.main(verbosity=2)
