#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Focused tests for the governed platform security-administrator bootstrap.

The owner ruling requires an independent approving identity to exist as a real,
named administrator before the maintenance-authorization flow can be used, and
requires that creating it is a separate governed step rather than a side effect
of any maintenance request.  These tests therefore cover both sides: the entry
must refuse anything undeclared, and it must refuse a readback that would make
the bootstrap approve its own request, take over a shared carrier, adopt another
person's account, or widen the identity beyond the approver group closure.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "platform_security_admin_bootstrap",
    ROOT / "scripts/ops/platform_security_admin_bootstrap.py",
)
assert SPEC and SPEC.loader
ENTRY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ENTRY)

LOGIN = "lidefend"
NAME = "Li Defend"
EVIDENCE = "owner ruling 2026-10-16 names lidefend as the platform security admin"
CONFIRM = ENTRY.CONFIRM_VALUE


def environ(**overrides):
    values = {
        ENTRY.CONFIRM_ENV: CONFIRM,
        ENTRY.LOGIN_ENV: LOGIN,
        ENTRY.NAME_ENV: NAME,
        ENTRY.EVIDENCE_ENV: EVIDENCE,
    }
    values.update(overrides)
    return values


def request():
    return {"login": LOGIN, "name": NAME, "evidence": EVIDENCE, "output": ENTRY.DEFAULT_OUTPUT}


def identity(**overrides):
    values = {
        "uid": 7,
        "login": LOGIN,
        "name": NAME,
        "active": True,
        "share": False,
        "company_id": 1,
        "group_ids": [2, 16],
        "group_xmlids": ["base.group_user", ENTRY.SECURITY_ADMIN_GROUP_XMLID],
        "groups_outside_allowed_closure": [],
        "is_security_admin": True,
        "has_stored_password": False,
    }
    values.update(overrides)
    return values


def report(**overrides):
    values = {
        "mode": "read_only",
        "writes": 0,
        "database": "sc_platform_control",
        "declared_login": LOGIN,
        "declared_name": NAME,
        "evidence": EVIDENCE,
        "security_admin_group": ENTRY.SECURITY_ADMIN_GROUP_XMLID,
        "security_admin_group_exists": True,
        "security_admin_member_count": 1,
        "maintenance_access_rows": 0,
        "approves_maintenance_access": False,
        "allowed_group_closure_ids": [2, 16],
        "allowed_group_closure_complete": True,
        "exists": True,
        "identity": identity(),
    }
    values.update(overrides)
    return values


def source() -> str:
    return (ROOT / "scripts/ops/platform_security_admin_bootstrap.py").read_text(encoding="utf-8")


class RequestTests(unittest.TestCase):
    def test_a_complete_request_resolves(self):
        resolved = ENTRY.resolve_request(environ())
        self.assertEqual(resolved["login"], LOGIN)
        self.assertEqual(resolved["name"], NAME)
        self.assertEqual(resolved["evidence"], EVIDENCE)
        self.assertEqual(resolved["output"], ENTRY.DEFAULT_OUTPUT)

    def test_the_declared_output_overrides_the_default(self):
        resolved = ENTRY.resolve_request(environ(**{ENTRY.OUTPUT_ENV: "/tmp/other.json"}))
        self.assertEqual(resolved["output"], "/tmp/other.json")

    def test_the_confirmation_is_required_and_exact(self):
        with self.assertRaisesRegex(ENTRY.BootstrapError, "CONFIRMATION_REQUIRED"):
            ENTRY.resolve_request({})
        with self.assertRaisesRegex(ENTRY.BootstrapError, "CONFIRMATION_REQUIRED"):
            ENTRY.resolve_request(environ(**{ENTRY.CONFIRM_ENV: "bootstrap_the_admin"}))

    def test_an_invalid_login_is_refused(self):
        for bad in ("", "A", "ab", "lid efend", "1lidefend", "-lidefend", "lidefend!", "l" * 64):
            with self.subTest(login=bad):
                with self.assertRaises(ENTRY.BootstrapError) as caught:
                    ENTRY.resolve_request(environ(**{ENTRY.LOGIN_ENV: bad}))
                self.assertIn("LOGIN_INVALID", str(caught.exception))

    def test_a_shared_or_technical_login_can_never_approve(self):
        self.assertTrue(ENTRY.REFUSED_LOGINS, "the refusal list must not be empty")
        for bad in ENTRY.REFUSED_LOGINS:
            with self.subTest(login=bad):
                with self.assertRaises(ENTRY.BootstrapError) as caught:
                    ENTRY.resolve_request(environ(**{ENTRY.LOGIN_ENV: bad}))
                # A carrier outside the login syntax is stopped by the grammar,
                # one inside it by the explicit refusal list; both are refusals.
                self.assertTrue(
                    "NOT_AN_APPROVER" in str(caught.exception)
                    or "LOGIN_INVALID" in str(caught.exception),
                    str(caught.exception),
                )

    def test_the_name_is_required(self):
        with self.assertRaisesRegex(ENTRY.BootstrapError, "NAME_REQUIRED"):
            ENTRY.resolve_request(environ(**{ENTRY.NAME_ENV: "   "}))

    def test_evidence_is_required_and_bounded(self):
        for bad in ("", "short", " x  1", "x" * 201, "bad;evidence"):
            with self.subTest(evidence=bad):
                with self.assertRaises(ENTRY.BootstrapError) as caught:
                    ENTRY.resolve_request(environ(**{ENTRY.EVIDENCE_ENV: bad}))
                self.assertIn("EVIDENCE_REQUIRED", str(caught.exception))

    def test_the_name_may_be_a_real_name_of_any_script(self):
        for good in ("Li Defend", "李德奋", "lidefend", "Li De-fen", "李德奋 平台安全管理员"):
            with self.subTest(name=good):
                resolved = ENTRY.resolve_request(environ(**{ENTRY.NAME_ENV: good}))
                self.assertEqual(resolved["name"], good)

    def test_a_name_that_could_break_the_payload_is_refused(self):
        # The name travels through the ssh payload and the entry's receipt, so
        # the characters that would break out of those carriers are refused
        # rather than escaped.
        for bad in ("Li 'D'", 'Li "D"', "Li`x`", "Li$x", "Li\\D", "Li;rm", "Li|rm", "Li\nDefend"):
            with self.subTest(name=bad):
                with self.assertRaises(ENTRY.BootstrapError) as caught:
                    ENTRY.resolve_request(environ(**{ENTRY.NAME_ENV: bad}))
                self.assertIn("NAME_INVALID", str(caught.exception))

    def test_evidence_that_could_break_the_payload_is_refused(self):
        for bad in ("owner's ruling 2026-10-16", "owner ruling `id` 2026-10-16", "owner ruling $(id) 2026-10-16"):
            with self.subTest(evidence=bad):
                with self.assertRaises(ENTRY.BootstrapError) as caught:
                    ENTRY.resolve_request(environ(**{ENTRY.EVIDENCE_ENV: bad}))
                self.assertIn("EVIDENCE_REQUIRED", str(caught.exception))


class ReadbackGateTests(unittest.TestCase):
    def test_a_readback_for_another_login_is_refused(self):
        with self.assertRaisesRegex(ENTRY.BootstrapError, "COVERS_ANOTHER_LOGIN"):
            ENTRY._assert_readable(report(declared_login="someone_else"), request())

    def test_a_readback_that_reports_a_write_is_refused(self):
        with self.assertRaisesRegex(ENTRY.BootstrapError, "READBACK_NOT_READ_ONLY"):
            ENTRY._assert_readable(report(writes=1), request())
        with self.assertRaisesRegex(ENTRY.BootstrapError, "READBACK_NOT_READ_ONLY"):
            ENTRY._assert_readable(report(mode="write"), request())

    def test_a_readback_that_approves_maintenance_access_is_refused(self):
        with self.assertRaisesRegex(ENTRY.BootstrapError, "MUST_NOT_APPROVE"):
            ENTRY._assert_readable(report(approves_maintenance_access=True), request())

    def test_a_readback_without_the_group_is_refused(self):
        with self.assertRaisesRegex(ENTRY.BootstrapError, "GROUP_MISSING"):
            ENTRY._assert_readable(report(security_admin_group_exists=False), request())

    def test_a_readback_of_a_widened_identity_is_refused(self):
        with self.assertRaisesRegex(ENTRY.BootstrapError, "HOLDS_UNRELATED_GROUPS"):
            ENTRY._assert_readable(
                report(
                    identity=identity(
                        groups_outside_allowed_closure=[
                            "smart_construction_core.group_sc_contract_manager"
                        ]
                    )
                ),
                request(),
            )

    def test_a_readback_of_another_named_person_is_refused(self):
        with self.assertRaisesRegex(ENTRY.BootstrapError, "READBACK_OTHER_NAME"):
            ENTRY._assert_readable(report(identity=identity(name="Someone Else")), request())

    def test_a_readback_without_the_declared_groups_is_refused(self):
        with self.assertRaisesRegex(ENTRY.BootstrapError, "ALLOWED_GROUP_MISSING"):
            ENTRY._assert_readable(
                report(allowed_group_closure_complete=False, allowed_group_closure_ids=[]),
                request(),
            )

    def test_a_readback_of_another_identity_is_refused(self):
        with self.assertRaisesRegex(ENTRY.BootstrapError, "READBACK_OTHER_IDENTITY"):
            ENTRY._assert_readable(report(identity=identity(login="someone_else")), request())

    def test_a_readback_of_an_absent_identity_is_honest(self):
        ENTRY._assert_readable(report(exists=False, identity=None), request())

    def test_a_readback_of_the_declared_identity_passes(self):
        ENTRY._assert_readable(report(), request())


class _Row:
    def __init__(self, module, name, res_id):
        self.module = module
        self.name = name
        self.res_id = res_id


class _FakeModel:
    """A minimal stand-in for one Odoo model, enough for these helpers."""

    def __init__(self, env, name):
        self._env = env
        self._name = name

    def sudo(self):
        return self

    def search(self, domain):
        ids = set(domain[1][2])
        return [
            _Row(module, name, res_id)
            for module, name, res_id in self._env.data_rows
            if res_id in ids
        ]

    def browse(self, ids):
        return _FakeGroupSet(self._env, list(ids))


class _FakeGroupSet:
    def __init__(self, env, ids):
        self._env = env
        self._ids = list(ids)

    def __or__(self, other):
        return _FakeGroupSet(self._env, self._ids + other._ids)

    @property
    def ids(self):
        return list(self._ids)

    @property
    def trans_implied_ids(self):
        return _FakeGroupSet(self._env, sorted(self._env.implied_closure(self._ids)))


class _Seed:
    _name = "res.groups"

    def __init__(self, group_id):
        self.id = group_id


class _FakeEnv:
    """An environment with recorded memberships and implied relationships."""

    def __init__(self, data_rows=(), implied=None):
        self.data_rows = list(data_rows)
        self._implied = dict(implied or {})

    def __getitem__(self, model):
        return _FakeModel(self, model)

    def implied_closure(self, ids):
        seen = set()
        pending = list(ids)
        while pending:
            group_id = pending.pop()
            if group_id in seen:
                continue
            seen.add(group_id)
            pending.extend(self._implied.get(group_id, ()))
        return seen


class GroupClosureTests(unittest.TestCase):
    def test_a_group_without_an_external_id_is_still_a_membership(self):
        env = _FakeEnv(data_rows=[("base", "group_user", 2)])
        self.assertEqual(ENTRY._group_labels(env, [2, 77]), ["base.group_user", "#77"])

    def test_the_closure_covers_the_platform_implications_and_nothing_else(self):
        env = _FakeEnv(
            data_rows=[
                ("base", "group_user", 2),
                ("smart_core", "group_smart_core_user", 14),
                ("smart_core", "group_smart_core_security_admin", 16),
                ("smart_construction_core", "group_sc_contract_manager", 40),
            ],
            implied={16: (14,), 14: (2,)},
        )
        allowed = ENTRY._allowed_group_closure_ids(env, (_Seed(2), _Seed(16)))
        self.assertEqual(allowed, {2, 14, 16})
        self.assertEqual(ENTRY._groups_outside_closure(env, [2, 14, 16], allowed), [])
        self.assertEqual(
            ENTRY._groups_outside_closure(env, [2, 14, 16, 40], allowed),
            ["smart_construction_core.group_sc_contract_manager"],
        )

    def test_a_missing_declared_group_is_undecidable_rather_than_permissive(self):
        self.assertEqual(ENTRY._allowed_group_closure_ids(_FakeEnv(), (False, _Seed(16))), set())
        self.assertEqual(ENTRY._allowed_group_closure_ids(_FakeEnv(), (_Seed(2), None)), set())


class SourceDisciplineTests(unittest.TestCase):
    def test_the_entry_binds_the_one_control_plane_security_admin_group(self):
        self.assertEqual(ENTRY.SECURITY_ADMIN_GROUP_XMLID, "smart_core.group_smart_core_security_admin")
        self.assertEqual(ENTRY.INTERNAL_USER_GROUP_XMLID, "base.group_user")

    def test_the_entry_refuses_the_operator_groups(self):
        self.assertIn(
            "smart_core.group_smart_core_tenant_payload_importer", ENTRY.REFUSED_GROUP_XMLIDS
        )

    def test_the_entry_declares_the_approver_group_closure(self):
        self.assertEqual(
            ENTRY.ALLOWED_GROUP_XMLIDS,
            (ENTRY.INTERNAL_USER_GROUP_XMLID, ENTRY.SECURITY_ADMIN_GROUP_XMLID),
        )

    def test_the_reuse_path_compares_the_name_and_the_group_closure(self):
        text = source()
        self.assertIn("PLATFORM_SECURITY_ADMIN_EXISTING_IDENTITY_MISMATCH", text)
        self.assertIn("PLATFORM_SECURITY_ADMIN_EXISTING_IDENTITY_HAS_UNRELATED_GROUPS", text)
        self.assertIn('identity["name"] != request["name"]', text)

    def test_the_entry_does_not_use_the_administrator_identity_scope_stub(self):
        # The platform helper answers a different question ("does an
        # administrator identity alone imply a customer data scope"); using it
        # as evidence here would be an assertion that can never fail.
        self.assertNotIn("has_customer_business_data_scope", source())

    def test_the_entry_takes_no_credential_input(self):
        text = source()
        self.assertNotIn("PASSWORD_ENV", text)
        self.assertIn("no_reset_password", text)
        for line in text.splitlines():
            if "environ.get(" in line or "os.environ" in line:
                self.assertNotIn("PASSWORD", line.upper(), line)

    def test_the_entry_asserts_the_authorization_ledger_was_not_touched(self):
        text = source()
        self.assertIn("access_rows_before", text)
        self.assertIn("TOUCHED_THE_LEDGER", text)
        self.assertIn("PLATFORM_SECURITY_ADMIN_BOOTSTRAP_MUST_NOT_APPROVE", text)

    def test_the_entry_creates_without_an_interactive_carrier(self):
        self.assertIn('"share": False', source())


if __name__ == "__main__":
    unittest.main(verbosity=2)
