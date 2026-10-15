#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Focused tests for the governed security-administrator credential step.

The owner ruling keeps the maintenance approval a product capability: the
decider is read from an authenticated principal at the product entry, never from
a caller-supplied string and never by a one-off shell that rewrites the
authorization row.  The missing fact is therefore that the named approver exists
without a credential, so these tests cover the step that supplies one and
nothing else: it must refuse anything undeclared, it must refuse to create,
widen or take over an account, and it must leave the authorization ledger
exactly as it found it -- because a step that could move the ledger would be an
approval wearing a credential's name.

The pure helpers run hermetically.  The two state-changing paths run against a
recorded fake environment, with the Odoo imports stubbed, so the post-conditions
the entry asserts are exercised for real rather than restated.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import stat
import sys
import tempfile
import types
import unittest
from contextlib import contextmanager
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "platform_security_admin_credential",
    ROOT / "scripts/ops/platform_security_admin_credential.py",
)
assert SPEC and SPEC.loader
ENTRY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ENTRY)

BOOTSTRAP = ENTRY.bootstrap

LOGIN = "lidefend"
NAME = "Li Defend"
EVIDENCE = "owner ruling 2026-10-16 names lidefend as the platform security admin"
CONFIRM = ENTRY.CONFIRM_VALUES


def environ(action="issue", **overrides):
    values = {
        ENTRY.LOGIN_ENV: LOGIN,
        ENTRY.NAME_ENV: NAME,
        ENTRY.EVIDENCE_ENV: EVIDENCE,
    }
    if action in CONFIRM:
        values[ENTRY.CONFIRM_ENV] = CONFIRM[action]
    values.update(overrides)
    return values


def request(action="issue", output=ENTRY.DEFAULT_OUTPUT):
    return {
        "login": LOGIN,
        "name": NAME,
        "evidence": EVIDENCE,
        "output": output,
        "action": action,
    }


def identity(**overrides):
    values = {
        "uid": 6,
        "login": LOGIN,
        "name": NAME,
        "active": True,
        "share": False,
        "company_id": 1,
        "group_ids": [2, 16],
        "group_xmlids": ["base.group_user", BOOTSTRAP.SECURITY_ADMIN_GROUP_XMLID],
        "groups_outside_allowed_closure": [],
        "is_security_admin": True,
        "has_stored_password": False,
    }
    values.update(overrides)
    return values


def readback(**overrides):
    values = {
        "mode": "read_only",
        "writes": 0,
        "database": "sc_platform_control",
        "declared_login": LOGIN,
        "declared_name": NAME,
        "evidence": EVIDENCE,
        "security_admin_group": BOOTSTRAP.SECURITY_ADMIN_GROUP_XMLID,
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
    return (ROOT / "scripts/ops/platform_security_admin_credential.py").read_text(encoding="utf-8")


class RequestTests(unittest.TestCase):
    def test_a_complete_issue_request_resolves(self):
        resolved = ENTRY.resolve_request(environ("issue"), "issue")
        self.assertEqual(resolved["action"], "issue")
        self.assertEqual(resolved["login"], LOGIN)
        self.assertEqual(resolved["name"], NAME)
        self.assertEqual(resolved["evidence"], EVIDENCE)
        self.assertEqual(resolved["output"], ENTRY.DEFAULT_OUTPUT)

    def test_reading_a_credential_needs_no_confirmation(self):
        resolved = ENTRY.resolve_request(environ("readback"), "readback")
        self.assertEqual(resolved["action"], "readback")
        self.assertEqual(resolved["login"], LOGIN)

    def test_each_state_changing_action_needs_its_own_confirmation(self):
        for action in ("issue", "clear"):
            with self.subTest(action=action):
                with self.assertRaisesRegex(ENTRY.CredentialError, "CONFIRMATION_REQUIRED"):
                    ENTRY.resolve_request({}, action)
                with self.assertRaisesRegex(ENTRY.CredentialError, "CONFIRMATION_REQUIRED"):
                    ENTRY.resolve_request(environ(action, **{ENTRY.CONFIRM_ENV: "yes"}), action)
                # The other action's confirmation is not this action's.
                other = "clear" if action == "issue" else "issue"
                with self.assertRaisesRegex(ENTRY.CredentialError, "CONFIRMATION_REQUIRED"):
                    ENTRY.resolve_request(
                        environ(action, **{ENTRY.CONFIRM_ENV: CONFIRM[other]}), action
                    )

    def test_an_undeclared_action_is_refused(self):
        for bad in ("", "rotate", "ISSUE", "clear "):
            with self.subTest(action=bad):
                with self.assertRaisesRegex(ENTRY.CredentialError, "ACTION_UNKNOWN"):
                    ENTRY.resolve_request(environ("issue"), bad)

    def test_an_invalid_login_is_refused(self):
        for bad in ("", "A", "ab", "lid efend", "1lidefend", "-lidefend", "lidefend!", "l" * 64):
            with self.subTest(login=bad):
                with self.assertRaises(ENTRY.CredentialError) as caught:
                    ENTRY.resolve_request(environ("issue", **{ENTRY.LOGIN_ENV: bad}), "issue")
                self.assertIn("LOGIN_INVALID", str(caught.exception))

    def test_a_shared_or_technical_login_can_never_receive_a_credential(self):
        self.assertTrue(BOOTSTRAP.REFUSED_LOGINS, "the refusal list must not be empty")
        for bad in BOOTSTRAP.REFUSED_LOGINS:
            with self.subTest(login=bad):
                with self.assertRaises(ENTRY.CredentialError) as caught:
                    ENTRY.resolve_request(environ("issue", **{ENTRY.LOGIN_ENV: bad}), "issue")
                self.assertTrue(
                    "NOT_AN_APPROVER" in str(caught.exception)
                    or "LOGIN_INVALID" in str(caught.exception),
                    str(caught.exception),
                )

    def test_the_name_grammar_is_the_bootstrap_grammar(self):
        with self.assertRaises(ENTRY.CredentialError) as caught:
            ENTRY.resolve_request(environ("issue", **{ENTRY.NAME_ENV: "  "}), "issue")
        self.assertIn("NAME_INVALID", str(caught.exception))
        for bad in ("x", "x" * 81, "Li 'D'", 'Li "D"', "Li`x`", "Li$x", "Li\\D", "Li;rm", "Li|rm"):
            with self.subTest(name=bad):
                with self.assertRaises(ENTRY.CredentialError) as caught:
                    ENTRY.resolve_request(environ("issue", **{ENTRY.NAME_ENV: bad}), "issue")
                self.assertIn("NAME_INVALID", str(caught.exception))
        self.assertEqual(ENTRY.NAME, BOOTSTRAP.NAME)
        resolved = ENTRY.resolve_request(environ("issue", **{ENTRY.NAME_ENV: "x" * 80}), "issue")
        self.assertEqual(len(resolved["name"]), 80)

    def test_evidence_is_required_and_bounded(self):
        for bad in ("", "short", "x" * 201, "bad;evidence", "bad evidence `id`"):
            with self.subTest(evidence=bad):
                with self.assertRaises(ENTRY.CredentialError) as caught:
                    ENTRY.resolve_request(environ("issue", **{ENTRY.EVIDENCE_ENV: bad}), "issue")
                self.assertIn("EVIDENCE_REQUIRED", str(caught.exception))
        resolved = ENTRY.resolve_request(environ("issue", **{ENTRY.EVIDENCE_ENV: "e" * 200}), "issue")
        self.assertEqual(len(resolved["evidence"]), 200)

    def test_the_credential_may_only_be_written_to_the_governed_directory(self):
        self.assertTrue(ENTRY.OUTPUT_PATH.fullmatch(ENTRY.DEFAULT_OUTPUT))
        # An undeclared destination falls back to the governed default rather
        # than to a path the caller chose, so it cannot widen the write.
        self.assertEqual(
            ENTRY.resolve_request(environ("issue", **{ENTRY.OUTPUT_ENV: "  "}), "issue")["output"],
            ENTRY.DEFAULT_OUTPUT,
        )
        self.assertTrue(ENTRY.DEFAULT_OUTPUT.startswith(ENTRY.OUTPUT_ROOT + "/"))
        for bad in (
            "/tmp/credential.json",
            "/mnt/artifacts",
            "/mnt/artifacts/",
            "/mnt/artifacts/sub/dir.json",
            "/mnt/artifacts/credential.txt",
            "/mnt/artifacts/../etc/passwd.json",
            "artifacts/credential.json",
        ):
            with self.subTest(output=bad):
                with self.assertRaises(ENTRY.CredentialError) as caught:
                    ENTRY.resolve_request(
                        environ("issue", **{ENTRY.OUTPUT_ENV: bad}), "issue"
                    )
                self.assertIn("OUTPUT_INVALID", str(caught.exception))

    def test_the_declared_output_overrides_the_default(self):
        declared = ENTRY.OUTPUT_ROOT + "/other-credential.json"
        resolved = ENTRY.resolve_request(environ("issue", **{ENTRY.OUTPUT_ENV: declared}), "issue")
        self.assertEqual(resolved["output"], declared)


class PasswordTests(unittest.TestCase):
    def test_the_alphabet_avoids_characters_a_reader_could_confuse(self):
        self.assertFalse(set("lIO01") & set(ENTRY.PASSWORD_ALPHABET))
        self.assertFalse(set("'\"`$\\;|<>&()") & set(ENTRY.PASSWORD_ALPHABET))

    def test_the_minimum_length_is_a_real_secret_length(self):
        self.assertGreaterEqual(ENTRY.MINIMUM_PASSWORD_LENGTH, 24)

    def test_a_generated_credential_obeys_its_own_grammar(self):
        drawn = {ENTRY._generate_password() for _ in range(50)}
        self.assertEqual(len(drawn), 50, "the generator must not repeat inside a small draw")
        for candidate in drawn:
            with self.subTest(candidate_length=len(candidate)):
                self.assertGreaterEqual(len(candidate), ENTRY.MINIMUM_PASSWORD_LENGTH)
                self.assertTrue(ENTRY.PASSWORD.fullmatch(candidate))
                self.assertFalse(set(candidate) - set(ENTRY.PASSWORD_ALPHABET))


class IdentityGuardTests(unittest.TestCase):
    def test_the_declared_approver_passes(self):
        guarded = ENTRY._identity_guard(readback(), request())
        self.assertEqual(guarded["uid"], 6)

    def test_an_absent_target_is_refused(self):
        with self.assertRaisesRegex(ENTRY.CredentialError, "TARGET_MISSING"):
            ENTRY._identity_guard(readback(identity=None, exists=False), request())

    def test_an_inactive_or_portal_target_is_refused(self):
        with self.assertRaisesRegex(ENTRY.CredentialError, "TARGET_INACTIVE"):
            ENTRY._identity_guard(readback(identity=identity(active=False)), request())
        with self.assertRaisesRegex(ENTRY.CredentialError, "TARGET_IS_PORTAL"):
            ENTRY._identity_guard(readback(identity=identity(share=True)), request())

    def test_a_target_without_the_approver_role_is_refused(self):
        with self.assertRaisesRegex(ENTRY.CredentialError, "TARGET_NOT_APPROVER"):
            ENTRY._identity_guard(readback(identity=identity(is_security_admin=False)), request())

    def test_a_widened_target_is_refused_and_named(self):
        widened = identity(
            groups_outside_allowed_closure=["smart_construction_core.group_sc_contract_manager"]
        )
        with self.assertRaises(ENTRY.CredentialError) as caught:
            ENTRY._identity_guard(readback(identity=widened), request())
        self.assertIn("TARGET_HAS_UNRELATED_GROUPS", str(caught.exception))
        self.assertIn("group_sc_contract_manager", str(caught.exception))


class CredentialFileTests(unittest.TestCase):
    def test_the_credential_file_is_operator_only_and_self_describing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "credential.json")
            written = ENTRY._write_credential_file(request(output=path), "secret-value", "a" * 32)
            self.assertEqual(written, path)
            mode = stat.S_IMODE(os.stat(path).st_mode)
            self.assertEqual(mode, 0o600, "the credential must not be group or world readable")
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            self.assertEqual(payload["entry"], ENTRY.ENTRY)
            self.assertEqual(payload["login"], LOGIN)
            self.assertEqual(payload["name"], NAME)
            self.assertEqual(payload["password"], "secret-value")
            self.assertEqual(payload["execution_id"], "a" * 32)
            self.assertIs(payload["single_use"], True)
            self.assertEqual(
                payload["clear_with"],
                "make daily.runtime.platform.security_admin.credential.remote_clear",
            )

    def test_a_failed_write_leaves_no_credential_behind(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "absent", "credential.json")
            with self.assertRaises(OSError):
                ENTRY._write_credential_file(request(output=path), "secret-value", "a" * 32)
            self.assertFalse(os.path.exists(path))

    def test_the_entry_never_returns_the_credential_value(self):
        body = source()
        # The credential value reaches exactly one place that can serialise it,
        # and the entry point strips it before printing a result.
        # Exactly two places name the credential together with its value: the
        # governed payload file and the account write.  Neither is a result.
        self.assertEqual(body.count('"password": password'), 2)
        self.assertIn('printable.pop("password", None)', body)
        self.assertIn("os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)", body)


class _Row:
    def __init__(self, module, name, res_id):
        self.module = module
        self.name = name
        self.res_id = res_id


class _User:
    _name = "res.users"

    def __init__(self, env):
        self._env = env

    @property
    def id(self):
        return self._env.uid

    @property
    def login(self):
        return self._env.login

    @property
    def name(self):
        return self._env.name

    @property
    def active(self):
        return self._env.active

    @property
    def share(self):
        return self._env.share

    @property
    def company_id(self):
        return types.SimpleNamespace(id=1)

    @property
    def groups_id(self):
        return types.SimpleNamespace(ids=list(self._env.group_ids))

    @property
    def is_security_admin(self):
        return self._env.is_security_admin

    @property
    def token_version(self):
        return self._env.token_version

    def write(self, values):
        self._env.write(values)


class _UserSet:
    def __init__(self, env, users):
        self._env = env
        self._users = users

    def sudo(self):
        return self

    def with_context(self, **kwargs):
        return self

    def search(self, domain, limit=None):
        # An Odoo search answers with a recordset, so the fake answers with the
        # single record itself, and with a falsy empty list when it is absent.
        if not self._users:
            return []
        return _User(self._env)

    def search_count(self, domain):
        return 1 if self._users else 0

    def browse(self, ids):
        return _User(self._env)


class _Access:
    def __init__(self, env):
        self._env = env

    def sudo(self):
        return self

    def search_count(self, domain):
        return self._env.access_rows


class _Registration:
    def __init__(self, env):
        self._env = env

    def sudo(self):
        return self

    def _assert_governance_principal(self):
        self._env.governance_principal_asserted = True
        return True


class _GroupSet:
    def __init__(self, env, ids):
        self._env = env
        self._ids = list(ids)

    def __or__(self, other):
        return _GroupSet(self._env, self._ids + list(other._ids))

    @property
    def ids(self):
        return list(self._ids)

    @property
    def trans_implied_ids(self):
        return _GroupSet(self._env, sorted(self._env.closure(self._ids)))


class _Groups:
    def __init__(self, env):
        self._env = env

    def sudo(self):
        return self

    def browse(self, ids):
        return _GroupSet(self._env, list(ids))


class _ModelData:
    def __init__(self, env):
        self._env = env

    def sudo(self):
        return self

    def search(self, domain):
        wanted = set(domain[1][2])
        return [row for row in self._env.data_rows if row.res_id in wanted]


class _Seed:
    _name = "res.groups"

    def __init__(self, group_id):
        self.id = group_id


class _Cursor:
    def __init__(self, env):
        self.env = env
        self.dbname = env.dbname
        self._row = ("",)

    def execute(self, sql, params=None):
        self._row = ("x" if self.env.password else "",)

    def fetchone(self):
        return self._row

    def flush(self):
        self.env.flushed += 1

    def commit(self):
        self.env.commits += 1


class _FakeEnv:
    """A recorded environment: the facts the credential step reads and asserts."""

    def __init__(self, *, password=False, access_rows=0, group_ids=(2, 16)):
        self.dbname = "sc_platform_control"
        self.uid = 6
        self.login = LOGIN
        self.name = NAME
        self.active = True
        self.share = False
        self.group_ids = list(group_ids)
        self.is_security_admin = True
        self.password = password
        self.access_rows = access_rows
        self.token_version = 3
        self.users = True
        self.data_rows = [
            _Row("base", "group_user", 2),
            _Row("smart_core", "group_smart_core_security_admin", 16),
        ]
        self.implied = {2: [], 16: [2]}
        self.writes = []
        self.commits = 0
        self.flushed = 0
        self.writes_do_not_stick = False
        self.ledger_moves_on_write = False
        self.membership_moves_on_write = False
        self.cr = _Cursor(self)
        self.registry = types.SimpleNamespace(cursor=self._cursor)

    def closure(self, ids):
        seen = set()
        pending = list(ids)
        while pending:
            group_id = pending.pop()
            if group_id in seen:
                continue
            seen.add(group_id)
            pending.extend(self.implied.get(group_id, ()))
        return seen

    @contextmanager
    def _cursor(self):
        yield _Cursor(self)

    def ref(self, xmlid, raise_if_not_found=False):
        if xmlid == BOOTSTRAP.INTERNAL_USER_GROUP_XMLID:
            return _Seed(2)
        if xmlid == BOOTSTRAP.SECURITY_ADMIN_GROUP_XMLID:
            return _Seed(16)
        return False

    def write(self, values):
        self.writes.append(dict(values))
        if "password" in values and not self.writes_do_not_stick:
            self.password = bool(values["password"])
        if self.ledger_moves_on_write:
            self.access_rows += 1
        if self.membership_moves_on_write:
            # A membership that moves inside the approver closure: the readback
            # stays readable, so only the post-condition can catch it.
            self.group_ids = sorted(list(self.group_ids) + [16])

    def __getitem__(self, model):
        if model == "res.users":
            return _UserSet(self, self.users)
        if model == "sc.platform.maintenance.access":
            return _Access(self)
        if model == "sc.platform.database.registration":
            return _Registration(self)
        if model == "res.groups":
            return _Groups(self)
        if model == "ir.model.data":
            return _ModelData(self)
        raise KeyError(model)


def _install_odoo_stub():
    """``readback`` imports the platform helper lazily; keep the test hermetic."""
    installed = {}
    for name in (
        "odoo",
        "odoo.api",
        "odoo.addons",
        "odoo.addons.smart_core",
        "odoo.addons.smart_core.security",
        "odoo.addons.smart_core.security.platform_admin",
    ):
        installed[name] = sys.modules.get(name)
    api = types.ModuleType("odoo.api")
    api.Environment = lambda cursor, uid, context: cursor.env
    platform_admin = types.ModuleType("odoo.addons.smart_core.security.platform_admin")
    platform_admin.user_is_security_admin = lambda user: bool(user.is_security_admin)
    odoo = types.ModuleType("odoo")
    addons = types.ModuleType("odoo.addons")
    smart_core = types.ModuleType("odoo.addons.smart_core")
    security = types.ModuleType("odoo.addons.smart_core.security")
    odoo.addons = addons
    addons.smart_core = smart_core
    smart_core.security = security
    security.platform_admin = platform_admin
    sys.modules.update({
        "odoo": odoo,
        "odoo.api": api,
        "odoo.addons": addons,
        "odoo.addons.smart_core": smart_core,
        "odoo.addons.smart_core.security": security,
        "odoo.addons.smart_core.security.platform_admin": platform_admin,
    })
    return installed


class RunFlowTests(unittest.TestCase):
    """The two state-changing paths, exercised against a recorded environment."""

    def setUp(self):
        self.previous = _install_odoo_stub()
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.credential = os.path.join(self.directory.name, "credential.json")
        self.receipt = os.path.join(self.directory.name, "receipt.json")
        # The governed destination itself is asserted in
        # ``test_the_credential_may_only_be_written_to_the_governed_directory``;
        # here the temporary directory stands in for it so the write is exercised
        # for real without touching the deployment's artefact mount.
        self.addCleanup(setattr, ENTRY, "OUTPUT_PATH", ENTRY.OUTPUT_PATH)
        ENTRY.OUTPUT_PATH = re.compile(
            r"^%s/[A-Za-z0-9][A-Za-z0-9_.-]{0,120}\.json$" % (re.escape(self.directory.name),)
        )

    def tearDown(self):
        for name, module in self.previous.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module

    def flow_environ(self, action):
        return environ(
            action,
            **{
                ENTRY.OUTPUT_ENV: self.credential,
                BOOTSTRAP.OUTPUT_ENV: self.receipt,
                "PLATFORM_DATABASE_EXECUTION_ID": "b" * 32,
            },
        )

    def test_issue_stores_an_operator_only_credential_and_reports_a_pass(self):
        env = _FakeEnv()
        result = ENTRY.run(env, self.flow_environ("issue"), "issue")
        self.assertIs(result["ok"], True)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["entry"], ENTRY.ENTRY)
        self.assertNotIn("password", result)
        self.assertEqual(result["action"], "issue")
        self.assertEqual(result["login"], LOGIN)
        self.assertEqual(result["credential_file"], self.credential)
        self.assertIs(result["approves_maintenance_access"], False)
        self.assertIs(result["group_ids_unchanged"], True)
        self.assertEqual(set(env.writes[0]), {"password"})
        self.assertTrue(ENTRY.PASSWORD.fullmatch(env.writes[0]["password"]))
        self.assertEqual(stat.S_IMODE(os.stat(self.credential).st_mode), 0o600)
        payload = json.loads(Path(self.credential).read_text(encoding="utf-8"))
        self.assertTrue(ENTRY.PASSWORD.fullmatch(payload["password"]))
        receipt_text = Path(self.receipt).read_text(encoding="utf-8")
        receipt = json.loads(receipt_text)
        self.assertEqual(receipt["status"], "passed")
        self.assertEqual(receipt["effects"]["commit_state"], "committed")
        self.assertEqual(receipt["effects"]["uid"], 6)
        # The receipt records the state the step is accountable for, and never
        # the credential value that produced it.
        self.assertIn('"has_stored_password": true', receipt_text)
        self.assertNotIn(env.writes[0]["password"], receipt_text)
        self.assertNotIn(env.writes[0]["password"], json.dumps(result))

    def test_issue_needs_the_declared_governance_principal(self):
        env = _FakeEnv()
        ENTRY.run(env, self.flow_environ("issue"), "issue")
        self.assertTrue(env.governance_principal_asserted)

    def test_issue_writes_nothing_when_a_credential_is_already_stored(self):
        env = _FakeEnv(password=True)
        with self.assertRaisesRegex(ENTRY.CredentialError, "ALREADY_ISSUED"):
            ENTRY.run(env, self.flow_environ("issue"), "issue")
        self.assertEqual(env.writes, [], "a refusal must not touch the account")
        self.assertEqual(env.commits, 0, "a refusal must not commit")
        self.assertFalse(os.path.exists(self.credential))

    def test_issue_is_refused_when_the_step_moves_the_authorization_ledger(self):
        env = _FakeEnv()
        env.ledger_moves_on_write = True
        with self.assertRaisesRegex(ENTRY.CredentialError, "TOUCHED_THE_LEDGER"):
            ENTRY.run(env, self.flow_environ("issue"), "issue")
        self.assertEqual(env.commits, 0)
        self.assertFalse(os.path.exists(self.credential))

    def test_issue_is_refused_when_the_step_changes_membership(self):
        env = _FakeEnv()
        env.membership_moves_on_write = True
        with self.assertRaisesRegex(ENTRY.CredentialError, "CHANGED_MEMBERSHIP"):
            ENTRY.run(env, self.flow_environ("issue"), "issue")
        self.assertEqual(env.commits, 0)
        self.assertFalse(os.path.exists(self.credential))

    def test_issue_is_refused_when_the_credential_was_not_stored(self):
        env = _FakeEnv()
        env.writes_do_not_stick = True
        with self.assertRaisesRegex(ENTRY.CredentialError, "COMMIT_UNCONFIRMED|NOT_STORED"):
            ENTRY.run(env, self.flow_environ("issue"), "issue")

    def test_clear_retires_the_credential_and_advances_the_token_version(self):
        env = _FakeEnv(password=True)
        Path(self.credential).write_text("{}", encoding="utf-8")
        result = ENTRY.run(env, self.flow_environ("clear"), "clear")
        self.assertEqual(result["status"], "passed")
        self.assertIs(result["cleared"], True)
        self.assertEqual(result["writes"], 1)
        self.assertFalse(os.path.exists(self.credential))
        self.assertIs(result["credential_file_removed"], True)
        self.assertEqual(env.writes[0]["password"], False)
        self.assertEqual(env.writes[0]["token_version"], 4)

    def test_clear_of_an_account_without_a_credential_writes_nothing(self):
        env = _FakeEnv()
        result = ENTRY.run(env, self.flow_environ("clear"), "clear")
        self.assertEqual(result["status"], "passed")
        self.assertIs(result["cleared"], False)
        self.assertEqual(result["writes"], 0)
        self.assertEqual(env.writes, [])

    def test_clear_is_refused_when_the_credential_survives(self):
        env = _FakeEnv(password=True)
        env.writes_do_not_stick = True
        with self.assertRaisesRegex(ENTRY.CredentialError, "NOT_CLEARED"):
            ENTRY.run(env, self.flow_environ("clear"), "clear")
        self.assertEqual(env.commits, 0)
        self.assertFalse(os.path.exists(self.credential))

    def test_readback_reports_read_only_and_writes_nothing(self):
        env = _FakeEnv()
        result = ENTRY.run(env, self.flow_environ("readback"), "readback")
        self.assertEqual(result["mode"], "read_only")
        self.assertEqual(result["writes"], 0)
        self.assertEqual(result["credential_entry"], ENTRY.ENTRY)
        self.assertEqual(result["declared_login"], LOGIN)
        self.assertEqual(sorted(result["credential_actions"]), ["clear", "issue", "readback"])
        self.assertEqual(env.writes, [])
        self.assertEqual(env.commits, 0)
        self.assertFalse(os.path.exists(self.receipt))
        self.assertFalse(os.path.exists(self.credential))

    def test_the_receipt_may_not_be_written_onto_the_credential(self):
        env = _FakeEnv()
        with self.assertRaisesRegex(ENTRY.CredentialError, "RECEIPT_COLLIDES_WITH_CREDENTIAL"):
            ENTRY.run(
                env,
                environ(
                    "issue",
                    **{
                        ENTRY.OUTPUT_ENV: self.credential,
                        BOOTSTRAP.OUTPUT_ENV: self.credential,
                    },
                ),
                "issue",
            )
        self.assertEqual(env.writes, [])


class TransportGateTests(unittest.TestCase):
    """The transport's own refusals: it must not carry or claim more than the entry."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "daily_runtime_platform_security_admin_credential",
            ROOT / "scripts/ops/daily_runtime_platform_security_admin_credential.py",
        )
        assert spec and spec.loader
        cls.TRANSPORT = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.TRANSPORT)

    def control(self):
        return {"database": "sc_platform_control"}

    def entry_result(self, **overrides):
        values = {
            "ok": True,
            "entry": ENTRY.ENTRY,
            "action": "issue",
            "login": LOGIN,
            "name": NAME,
            "credential_file": "/mnt/artifacts/credential.json",
            "credential_written": True,
            "approves_maintenance_access": False,
            "group_ids_unchanged": True,
            "maintenance_access_rows": 0,
        }
        values.update(overrides)
        return values

    def envelope(self, **overrides):
        values = {"source_sha256": "a" * 64, "result": self.entry_result()}
        values.update(overrides)
        return values

    def test_reading_needs_no_confirmation_and_writing_needs_the_exact_one(self):
        self.assertEqual(self.TRANSPORT.confirmation(ENTRY, "readback"), "")
        for action in ("issue", "clear"):
            with self.subTest(action=action):
                previous = os.environ.pop(ENTRY.CONFIRM_ENV, None)
                try:
                    with self.assertRaises(self.TRANSPORT.CredentialTransportError):
                        self.TRANSPORT.confirmation(ENTRY, action)
                    other = "clear" if action == "issue" else "issue"
                    os.environ[ENTRY.CONFIRM_ENV] = CONFIRM[other]
                    with self.assertRaises(self.TRANSPORT.CredentialTransportError):
                        self.TRANSPORT.confirmation(ENTRY, action)
                    os.environ[ENTRY.CONFIRM_ENV] = CONFIRM[action]
                    self.assertEqual(self.TRANSPORT.confirmation(ENTRY, action), CONFIRM[action])
                finally:
                    if previous is None:
                        os.environ.pop(ENTRY.CONFIRM_ENV, None)
                    else:
                        os.environ[ENTRY.CONFIRM_ENV] = previous

    def test_the_declared_inputs_use_the_entrys_own_rules(self):
        with self.assertRaises(self.TRANSPORT.CredentialTransportError):
            self.TRANSPORT.declare_request(
                ENTRY, login="admin", name=NAME, evidence=EVIDENCE, action="readback"
            )
        with self.assertRaises(self.TRANSPORT.CredentialTransportError):
            self.TRANSPORT.declare_request(
                ENTRY, login=LOGIN, name="", evidence=EVIDENCE, action="readback"
            )
        declared = self.TRANSPORT.declare_request(
            ENTRY, login=LOGIN, name=NAME, evidence=EVIDENCE, action="readback"
        )
        self.assertEqual(declared["output"], ENTRY.DEFAULT_OUTPUT)

    def test_the_read_environment_carries_no_confirmation_and_no_action(self):
        request = ENTRY.resolve_request(
            environ("readback", **{ENTRY.OUTPUT_ENV: ENTRY.DEFAULT_OUTPUT}), "readback"
        )
        declared = self.TRANSPORT.readback_environment(ENTRY, request)
        joined = " ".join(declared)
        self.assertIn("PLATFORM_SECURITY_ADMIN_CREDENTIAL_ACTION=readback", joined)
        self.assertNotIn(ENTRY.CONFIRM_ENV, joined)
        self.assertEqual(len(declared) // 2, 4)

    def test_the_write_environment_carries_only_the_declared_inputs(self):
        request = ENTRY.resolve_request(
            environ("issue", **{ENTRY.OUTPUT_ENV: ENTRY.DEFAULT_OUTPUT}), "issue"
        )
        declared = self.TRANSPORT.entry_environment(ENTRY, request, "issue", "c" * 32)
        joined = " ".join(declared)
        self.assertIn("%s=%s" % (ENTRY.CONFIRM_ENV, CONFIRM["issue"]), joined)
        self.assertIn("PLATFORM_DATABASE_EXECUTION_ID=%s" % ("c" * 32,), joined)
        self.assertIn("%s=%s" % (ENTRY.OUTPUT_ENV, ENTRY.DEFAULT_OUTPUT), joined)
        self.assertNotIn("password", joined.lower())

    def test_a_readback_that_is_not_a_read_is_refused(self):
        request = ENTRY.resolve_request(
            environ("readback", **{ENTRY.OUTPUT_ENV: ENTRY.DEFAULT_OUTPUT}), "readback"
        )
        for bad in (readback(writes=1), readback(mode="write")):
            with self.subTest(report=bad["mode"]):
                with self.assertRaises(self.TRANSPORT.CredentialTransportError):
                    self.TRANSPORT.assert_readback(bad, ENTRY, request, self.control())
        for bad in (
            readback(database="sc_demo"),
            readback(declared_login="someone_else"),
            readback(security_admin_group_exists=False),
            readback(allowed_group_closure_ids=[]),
            readback(maintenance_access_rows=-1),
        ):
            with self.subTest(report=bad["database"]):
                with self.assertRaises(self.TRANSPORT.CredentialTransportError):
                    self.TRANSPORT.assert_readback(bad, ENTRY, request, self.control())
        self.assertEqual(
            self.TRANSPORT.assert_readback(readback(), ENTRY, request, self.control())["database"],
            "sc_platform_control",
        )

    def test_an_entry_result_that_claims_another_fact_is_refused(self):
        request = ENTRY.resolve_request(
            environ("issue", **{ENTRY.OUTPUT_ENV: ENTRY.DEFAULT_OUTPUT}), "issue"
        )
        for bad in (
            self.envelope(source_sha256="b" * 64),
            self.envelope(result=self.entry_result(ok=False)),
            self.envelope(result=self.entry_result(action="clear")),
            self.envelope(result=self.entry_result(login="someone_else")),
            self.envelope(result=self.entry_result(name="Someone Else")),
            self.envelope(result=self.entry_result(approves_maintenance_access=True)),
            self.envelope(result=self.entry_result(group_ids_unchanged=False)),
            self.envelope(result=self.entry_result(password="value")),
            self.envelope(result=self.entry_result(maintenance_access_rows=1)),
            self.envelope(result=None),
        ):
            with self.subTest(envelope=json.dumps(bad)[:60]):
                with self.assertRaises(self.TRANSPORT.CredentialTransportError):
                    self.TRANSPORT.assert_entry_result(bad, ENTRY, request, "a" * 64, "issue", readback())
        accepted = self.TRANSPORT.assert_entry_result(
            self.envelope(), ENTRY, request, "a" * 64, "issue", readback()
        )
        self.assertEqual(accepted["credential_file"], "/mnt/artifacts/credential.json")


class TransportScrubTests(unittest.TestCase):
    """The transport must never print a credential value."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "daily_runtime_platform_security_admin_credential",
            ROOT / "scripts/ops/daily_runtime_platform_security_admin_credential.py",
        )
        assert spec and spec.loader
        cls.TRANSPORT = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.TRANSPORT)

    def test_a_credential_value_is_dropped_at_any_depth(self):
        scrubbed = self.TRANSPORT.scrub(
            {
                "credential_file": "/mnt/artifacts/credential.json",
                "password": "value",
                "api_key": "value",
                "secret": "value",
                "token": "value",
                "identity": {"has_stored_password": True, "login": LOGIN},
                "nested": [{"token": "value", "kept": 1}],
                "token_version": 4,
            }
        )
        for dropped in ("password", "api_key", "secret", "token"):
            with self.subTest(dropped=dropped):
                self.assertNotIn(dropped, scrubbed)
        self.assertEqual(scrubbed["nested"], [{"kept": 1}])
        # A boolean beside a credential name is a fact an audit needs, so it
        # stays; the credential itself is text, and text is what is dropped.
        self.assertEqual(scrubbed["identity"], {"has_stored_password": True, "login": LOGIN})
        self.assertEqual(scrubbed["token_version"], 4)
        self.assertEqual(scrubbed["credential_file"], "/mnt/artifacts/credential.json")

    def test_the_transport_declares_the_entrys_own_inputs(self):
        entry = self.TRANSPORT.credential_entry(ROOT)
        self.assertEqual(entry.ENTRY, ENTRY.ENTRY)
        self.assertEqual(entry.CONFIRM_VALUES["issue"], CONFIRM["issue"])
        self.assertEqual(entry.CONFIRM_VALUES["clear"], CONFIRM["clear"])
        self.assertEqual(entry.DEFAULT_OUTPUT, ENTRY.DEFAULT_OUTPUT)
        declared = self.TRANSPORT.declare_request(
            entry, login=LOGIN, name=NAME, evidence=EVIDENCE, action="readback"
        )
        self.assertEqual(declared["login"], LOGIN)
        self.assertEqual(declared["output"], ENTRY.DEFAULT_OUTPUT)


class MakeTargetTests(unittest.TestCase):
    """The credential step is reachable only through the guarded daily targets."""

    def setUp(self):
        self.make = (ROOT / "make/daily_candidate.mk").read_text(encoding="utf-8")

    def test_the_credential_targets_are_declared(self):
        for target in (
            "verify.platform.security_admin.credential:",
            "daily.runtime.platform.security_admin.credential.remote_install:",
            "daily.runtime.platform.security_admin.credential.remote_readback:",
            "daily.runtime.platform.security_admin.credential.remote_issue:",
            "daily.runtime.platform.security_admin.credential.remote_clear:",
        ):
            self.assertIn(target, self.make)

    def test_the_two_state_changing_actions_keep_their_exact_confirmations(self):
        self.assertIn(CONFIRM["issue"], self.make)
        self.assertIn(CONFIRM["clear"], self.make)

    def test_the_targets_carry_the_entry_and_its_single_payload_guard(self):
        self.assertIn(
            "scripts/ops/platform_security_admin_credential.py",
            self.make,
        )
        self.assertIn("daily.runtime.security_admin.payload_inputs", self.make)
        self.assertIn("daily_runtime_platform_security_admin_credential.py", self.make)


if __name__ == "__main__":
    unittest.main()
