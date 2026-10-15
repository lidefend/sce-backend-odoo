#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Governed one-time credential for the platform security administrator.

Owner ruling (2026-10-16): the independent approver is the named security
administrator ``lidefend``, and the approval itself must stay a product
capability -- a caller authenticates at the product entry and the server reads
the decider from that authenticated principal -- never a caller-supplied
``APPROVED_BY`` string and never a one-off shell that rewrites the authorization
row.  That leaves exactly one missing fact: the named administrator exists
without a stored credential by design, so no principal can authenticate as it
and the approval cannot be exercised for real.

This step supplies that fact and nothing else.  It is deliberately narrow:

* it only issues a credential for an identity that already exists and already
  carries exactly the control-plane security-administrator closure, so issuing
  can never create the approver and can never widen one;
* it refuses to take over an account that already carries a stored credential,
  so it can never silently replace somebody's password; clearing must be asked
  for explicitly first;
* it changes no group membership, approves no maintenance access, and asserts
  the authorization ledger is exactly as it found it;
* ``clear`` takes the credential back, returning the identity to the
  no-stored-password state the bootstrap asserts, and it retires any token the
  issued credential could have minted by advancing the account's token version;
* the credential is written by this step to a governed operator-only file
  outside the git tree.  It is never an argv, never a printed line and never
  part of a readback, so it cannot leak through a command line or a log.

The module body only needs the standard library, so the pure decision helpers
stay importable by a hermetic unit test.
"""

from __future__ import annotations

import json
import os
import re
import secrets
from datetime import datetime, timezone

from scripts.ops.platform_database_receipt import operation_receipt
from scripts.ops import platform_security_admin_bootstrap as bootstrap

ENTRY = "platform.security_admin.credential"

#: One confirmation per state-changing action.  Reading needs none.
CONFIRM_ENV = "SC_CONFIRM_PLATFORM_SECURITY_ADMIN_CREDENTIAL"
CONFIRM_VALUES = {
    "issue": "ISSUE_ONE_TIME_PLATFORM_SECURITY_ADMIN_CREDENTIAL",
    "clear": "CLEAR_PLATFORM_SECURITY_ADMIN_CREDENTIAL",
}
ACTIONS = ("readback", "issue", "clear")

LOGIN_ENV = bootstrap.LOGIN_ENV
NAME_ENV = bootstrap.NAME_ENV
EVIDENCE_ENV = bootstrap.EVIDENCE_ENV
OUTPUT_ENV = "PLATFORM_SECURITY_ADMIN_CREDENTIAL_OUTPUT"
#: The governed, operator-only destination.  ``/mnt/artifacts`` is the duty
#: stack's own writable mount of ``${SC_PRODUCT_ROOT}/artifacts``, which is
#: outside version control; the entry writes there and nowhere else.
DEFAULT_OUTPUT = "/mnt/artifacts/platform-security-admin-credential.json"
OUTPUT_ROOT = "/mnt/artifacts"

MINIMUM_PASSWORD_LENGTH = 24
#: Unambiguous, shell-safe, JSON-safe: no quote, no backslash, no operator, and
#: no character pair a reader could mistake for another.
PASSWORD_ALPHABET = (
    "abcdefghijkmnopqrstuvwxyz"
    "ABCDEFGHJKLMNPQRSTUVWXYZ"
    "23456789"
    "-_"
)
PASSWORD = re.compile(r"^[A-Za-z0-9_-]{%d,}$" % (MINIMUM_PASSWORD_LENGTH,))

OUTPUT_PATH = re.compile(
    r"^%s/[A-Za-z0-9][A-Za-z0-9_.-]{0,120}\.json$" % (re.escape(OUTPUT_ROOT),)
)

LOGIN = bootstrap.LOGIN
NAME = bootstrap.NAME
EVIDENCE = bootstrap.EVIDENCE


class CredentialError(RuntimeError):
    """Any fail-closed refusal of this entry."""


def resolve_request(environ, action):
    """Validate one credential request, fail closed on anything undeclared."""
    if action not in ACTIONS:
        raise CredentialError("PLATFORM_SECURITY_ADMIN_CREDENTIAL_ACTION_UNKNOWN:%s" % (action,))
    if action in CONFIRM_VALUES:
        declared = str(environ.get(CONFIRM_ENV) or "").strip()
        if declared != CONFIRM_VALUES[action]:
            raise CredentialError(
                "PLATFORM_SECURITY_ADMIN_CREDENTIAL_CONFIRMATION_REQUIRED:%s" % (CONFIRM_ENV,)
            )
    login = str(environ.get(LOGIN_ENV) or "").strip()
    if not LOGIN.fullmatch(login):
        raise CredentialError("PLATFORM_SECURITY_ADMIN_LOGIN_INVALID")
    if login in bootstrap.REFUSED_LOGINS:
        raise CredentialError("PLATFORM_SECURITY_ADMIN_LOGIN_NOT_AN_APPROVER:%s" % (login,))
    name = str(environ.get(NAME_ENV) or "").strip()
    if not NAME.fullmatch(name):
        raise CredentialError("PLATFORM_SECURITY_ADMIN_NAME_INVALID")
    evidence = str(environ.get(EVIDENCE_ENV) or "").strip()
    if not EVIDENCE.fullmatch(evidence):
        raise CredentialError("PLATFORM_SECURITY_ADMIN_EVIDENCE_REQUIRED")
    output = str(environ.get(OUTPUT_ENV) or DEFAULT_OUTPUT).strip() or DEFAULT_OUTPUT
    if not OUTPUT_PATH.fullmatch(output):
        raise CredentialError("PLATFORM_SECURITY_ADMIN_CREDENTIAL_OUTPUT_INVALID")
    return {
        "login": login,
        "name": name,
        "evidence": evidence,
        "output": output,
        "action": action,
    }


def _generate_password():
    """A one-time credential drawn from the declared safe alphabet."""
    while True:
        candidate = "".join(secrets.choice(PASSWORD_ALPHABET) for _ in range(28))
        if PASSWORD.fullmatch(candidate):
            return candidate


def _identity_guard(readback, request):
    """The declared identity must be the approver this step may not widen."""
    identity = readback.get("identity")
    if identity is None:
        raise CredentialError("PLATFORM_SECURITY_ADMIN_CREDENTIAL_TARGET_MISSING")
    if not identity.get("active"):
        raise CredentialError("PLATFORM_SECURITY_ADMIN_CREDENTIAL_TARGET_INACTIVE")
    if identity.get("share"):
        raise CredentialError("PLATFORM_SECURITY_ADMIN_CREDENTIAL_TARGET_IS_PORTAL")
    if not identity.get("is_security_admin"):
        raise CredentialError("PLATFORM_SECURITY_ADMIN_CREDENTIAL_TARGET_NOT_APPROVER")
    if identity.get("groups_outside_allowed_closure"):
        raise CredentialError(
            "PLATFORM_SECURITY_ADMIN_CREDENTIAL_TARGET_HAS_UNRELATED_GROUPS:%s"
            % (",".join(identity["groups_outside_allowed_closure"]),)
        )
    return identity


def _write_credential_file(request, password, execution_id):
    """Write the credential operator-only; never stdout, never argv."""
    path = request["output"]
    payload = {
        "entry": ENTRY,
        "login": request["login"],
        "name": request["name"],
        "evidence": request["evidence"],
        "password": password,
        "issued_at": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "execution_id": execution_id,
        "single_use": True,
        "clear_with": "make daily.runtime.platform.security_admin.credential.remote_clear",
    }
    handle = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, sort_keys=True)
            stream.write("\n")
    except Exception:
        try:
            os.unlink(path)
        except OSError:
            pass
        raise
    return path


def _succeed(receipt, uid, committed):
    """Report a committed effect through the shared receipt.

    ``uid`` is already written and the identity has already been read back in a
    separate transaction, so the receipt must say ``passed``.  Leaving it
    ``pending`` would report the commit state as unknown exactly where it is
    known, and a later reader could not tell this from a step that never ran.
    """
    receipt.effects["commit_state"] = "committed"
    try:
        return receipt.succeed(committed)
    except Exception as error:  # noqa: BLE001 - the write already happened
        raise CredentialError(
            "PLATFORM_SECURITY_ADMIN_CREDENTIAL_COMMITTED_RECEIPT_FAILED:uid=%s; do not replay"
            % (uid,)
        ) from error


def _run_issue(env, environ, receipt):
    request = resolve_request(environ, "issue")
    registry = env["sc.platform.database.registration"]
    registry._assert_governance_principal()
    execution_id = str(environ.get("PLATFORM_DATABASE_EXECUTION_ID") or "").strip()

    before = bootstrap.readback(env, request)
    bootstrap._assert_readable(before, request)
    identity = _identity_guard(before, request)
    if identity.get("has_stored_password"):
        # Never take over a credential somebody else may be using: taking it
        # over would let this step read as "the account always belonged to me".
        raise CredentialError("PLATFORM_SECURITY_ADMIN_CREDENTIAL_ALREADY_ISSUED")
    ledger_before = int(before["maintenance_access_rows"])
    groups_before = list(identity["group_ids"])

    password = _generate_password()
    user = env["res.users"].sudo().browse(identity["uid"])
    user.write({"password": password})
    env.cr.flush()

    after = bootstrap.readback(env, request)
    bootstrap._assert_readable(after, request)
    confirmed = after["identity"]
    if not confirmed.get("has_stored_password"):
        raise CredentialError("PLATFORM_SECURITY_ADMIN_CREDENTIAL_NOT_STORED")
    if list(confirmed["group_ids"]) != groups_before:
        raise CredentialError("PLATFORM_SECURITY_ADMIN_CREDENTIAL_CHANGED_MEMBERSHIP")
    if int(after["maintenance_access_rows"]) != ledger_before:
        raise CredentialError("PLATFORM_SECURITY_ADMIN_CREDENTIAL_TOUCHED_THE_LEDGER")

    receipt.effects["uid"] = identity["uid"]
    try:
        env.cr.commit()
    except Exception as error:  # noqa: BLE001 - report, never replay silently
        raise CredentialError(
            "PLATFORM_SECURITY_ADMIN_CREDENTIAL_COMMIT_UNCONFIRMED:uid=%s; do not replay"
            % (identity["uid"],)
        ) from error

    independent = bootstrap._independent_readback(env, request)
    bootstrap._assert_readable(independent, request)
    if not independent["identity"].get("has_stored_password"):
        raise CredentialError(
            "PLATFORM_SECURITY_ADMIN_CREDENTIAL_COMMIT_UNCONFIRMED:uid=%s" % (identity["uid"],)
        )
    path = _write_credential_file(request, password, execution_id)
    return _succeed(receipt, identity["uid"], {
        "ok": True,
        "entry": ENTRY,
        "action": "issue",
        "login": request["login"],
        "name": request["name"],
        "evidence": request["evidence"],
        "writes": 1,
        "database": independent["database"],
        "uid": identity["uid"],
        "credential_file": path,
        "credential_written": True,
        "identity": independent["identity"],
        "security_admin_member_count": independent["security_admin_member_count"],
        "maintenance_access_rows": independent["maintenance_access_rows"],
        "group_ids_unchanged": True,
        "approves_maintenance_access": False,
    })


def _run_clear(env, environ, receipt):
    request = resolve_request(environ, "clear")
    registry = env["sc.platform.database.registration"]
    registry._assert_governance_principal()

    before = bootstrap.readback(env, request)
    bootstrap._assert_readable(before, request)
    identity = _identity_guard(before, request)
    ledger_before = int(before["maintenance_access_rows"])
    groups_before = list(identity["group_ids"])
    stored_before = bool(identity.get("has_stored_password"))

    user = env["res.users"].sudo().browse(identity["uid"])
    writes = 0
    if stored_before:
        # Retire the credential and every token it could have minted.
        user.write({"password": False, "token_version": int(user.token_version or 0) + 1})
        env.cr.flush()
        writes = 1

    after = bootstrap.readback(env, request)
    bootstrap._assert_readable(after, request)
    confirmed = after["identity"]
    if confirmed.get("has_stored_password"):
        raise CredentialError("PLATFORM_SECURITY_ADMIN_CREDENTIAL_NOT_CLEARED")
    if list(confirmed["group_ids"]) != groups_before:
        raise CredentialError("PLATFORM_SECURITY_ADMIN_CREDENTIAL_CHANGED_MEMBERSHIP")
    if int(after["maintenance_access_rows"]) != ledger_before:
        raise CredentialError("PLATFORM_SECURITY_ADMIN_CREDENTIAL_TOUCHED_THE_LEDGER")

    receipt.effects["uid"] = identity["uid"]
    try:
        env.cr.commit()
    except Exception as error:  # noqa: BLE001
        raise CredentialError(
            "PLATFORM_SECURITY_ADMIN_CREDENTIAL_COMMIT_UNCONFIRMED:uid=%s; do not replay"
            % (identity["uid"],)
        ) from error

    independent = bootstrap._independent_readback(env, request)
    bootstrap._assert_readable(independent, request)
    if independent["identity"].get("has_stored_password"):
        raise CredentialError("PLATFORM_SECURITY_ADMIN_CREDENTIAL_NOT_CLEARED")
    try:
        if os.path.exists(request["output"]):
            os.unlink(request["output"])
    except OSError:
        pass
    return _succeed(receipt, identity["uid"], {
        "ok": True,
        "entry": ENTRY,
        "action": "clear",
        "login": request["login"],
        "name": request["name"],
        "evidence": request["evidence"],
        "writes": writes,
        "database": independent["database"],
        "uid": identity["uid"],
        "cleared": stored_before,
        "credential_file": request["output"],
        "credential_file_removed": not os.path.exists(request["output"]),
        "identity": independent["identity"],
        "security_admin_member_count": independent["security_admin_member_count"],
        "maintenance_access_rows": independent["maintenance_access_rows"],
        "group_ids_unchanged": True,
        "approves_maintenance_access": False,
    })


def readback(env, request):
    """The identity facts this step asserts, plus its own read-only posture."""
    report = bootstrap.readback(env, request)
    report["credential_entry"] = ENTRY
    report["credential_actions"] = list(ACTIONS)
    report["output_declared"] = request["output"]
    return report


def run(env, environ, action):
    request = resolve_request(environ, action)
    # The receipt is a separate artefact from the credential: the receipt is the
    # shared run record and the credential is the operator-only secret, so the
    # two must never be allowed to land on one path and overwrite each other.
    output = str(environ.get(bootstrap.OUTPUT_ENV) or bootstrap.DEFAULT_OUTPUT).strip()
    if output == request["output"]:
        raise CredentialError("PLATFORM_SECURITY_ADMIN_CREDENTIAL_RECEIPT_COLLIDES_WITH_CREDENTIAL")
    if action == "readback":
        report = readback(env, request)
        bootstrap._assert_readable(report, request)
        report["writes"] = 0
        report["mode"] = "read_only"
        return report
    with operation_receipt(output, ENTRY, environ.get("PLATFORM_DATABASE_EXECUTION_ID"), {
        key: str(environ.get(key) or "")
        for key in (CONFIRM_ENV, LOGIN_ENV, NAME_ENV, EVIDENCE_ENV, OUTPUT_ENV)
    }) as receipt:
        if action == "issue":
            return _run_issue(env, environ, receipt)
        return _run_clear(env, environ, receipt)


def _entrypoint():
    shell_env = globals().get("env")
    if shell_env is None:
        raise SystemExit(
            "platform security admin credential must run through odoo shell "
            "(scripts/ops/odoo_shell_exec.sh)"
        )
    action = str(os.environ.get("PLATFORM_SECURITY_ADMIN_CREDENTIAL_ACTION") or "").strip()
    try:
        result = run(shell_env, os.environ, action)
    except Exception as error:
        print("[%s] FAILED: %s" % (ENTRY, error))
        raise
    printable = dict(result)
    printable.pop("password", None)
    print("[%s] %s %s" % (ENTRY, action, json.dumps(printable, ensure_ascii=False, sort_keys=True, default=str)))


try:
    env  # noqa: B018 - provided by odoo shell
except NameError:
    pass
else:
    _entrypoint()
