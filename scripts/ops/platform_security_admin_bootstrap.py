#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Governed ops entry for the platform security-administrator identity.

Owner ruling (2026-10-16): an independent approving identity must exist as a
real, named administrator before the maintenance-authorization flow can be used
for real, and creating it is a separate governed bootstrap step rather than a
side effect of any maintenance request.

The step is deliberately narrow:

* it only *establishes and verifies* one named administrator and grants exactly
  the control-plane security-administrator group;
* it never approves a maintenance access, and it asserts the authorization
  ledger is exactly as it found it;
* it never introduces a business data scope: the readback reports the identity's
  *actual* group membership against the environment's own implied closure of the
  two allowed groups, so any further membership -- an industry or customer
  business role in particular -- is refused instead of adopted;
* it never takes over a shared or technical carrier: the built-in ``admin``,
  the system and portal carriers and any disabled or portal account are stops,
  because an approval identity that anybody else also uses is not an
  independent approver;
* it is idempotent in the safe direction: an existing identity that matches the
  declaration is verified and reused, and an existing account that merely shares
  the declared login is refused rather than adopted.

The credential is never an input of this entry.  The account is created without
a stored password and without interactive login; a credential is issued later
through the existing governed credential path if one is needed.

The module body only needs the standard library, so the pure decision helpers
stay importable by a hermetic unit test.
"""

from __future__ import annotations

import os
import re

from scripts.ops.platform_database_receipt import operation_receipt

ENTRY = "platform.security_admin.bootstrap"
CONFIRM_ENV = "SC_CONFIRM_PLATFORM_SECURITY_ADMIN_BOOTSTRAP"
CONFIRM_VALUE = "BOOTSTRAP_DECLARED_PLATFORM_SECURITY_ADMIN"
LOGIN_ENV = "PLATFORM_SECURITY_ADMIN_LOGIN"
NAME_ENV = "PLATFORM_SECURITY_ADMIN_NAME"
EVIDENCE_ENV = "PLATFORM_SECURITY_ADMIN_EVIDENCE"
OUTPUT_ENV = "PLATFORM_SECURITY_ADMIN_OUTPUT"
DEFAULT_OUTPUT = "/tmp/platform_security_admin_bootstrap.json"

#: The control-plane security-administrator group, addressed by its Odoo xmlid.
SECURITY_ADMIN_GROUP_XMLID = "smart_core.group_smart_core_security_admin"
#: The one ordinary group the identity carries in addition to that role.
INTERNAL_USER_GROUP_XMLID = "base.group_user"

#: Carriers that may never become the approving identity.  They are shared,
#: technical or implicit principals: an approval from one of them is an approval
#: from whoever else can use it, which is exactly what independence forbids.
REFUSED_LOGINS = (
    "admin",
    "__system__",
    "default",
    "public",
    "portaltemplate",
    "system",
    "root",
    "odoo",
)
#: The complete set of groups the approving identity may carry: the ordinary
#: internal-user group plus the control-plane security-administrator role.  The
#: environment's transitive implied closure of these two is added when the
#: membership is read, because Odoo completes a membership with the implied
#: groups of the groups an account is created with.  Any membership outside that
#: closure means the account is something other than the independent approver --
#: for example an internal user that also holds a business role -- and reusing it
#: would hand the control-plane role to a business identity.
ALLOWED_GROUP_XMLIDS = (INTERNAL_USER_GROUP_XMLID, SECURITY_ADMIN_GROUP_XMLID)

#: Operation identities that carry the narrow signed-payload import capability.
#: The security administrator decides maintenance access; it must never be the
#: identity that executes it.  These groups are already outside the allowed
#: closure; naming them keeps the refusal specific.
REFUSED_GROUP_XMLIDS = (
    "smart_core.group_smart_core_tenant_payload_importer",
    "smart_core.group_smart_core_data_operator",
)

LOGIN = re.compile(r"^[a-z][a-z0-9_.-]{2,62}$")
#: A human name.  A real name may be Chinese, so this is deliberately not
#: ASCII-only; what it does refuse is the characters that would break out of the
#: shell argument, the JSON string or the SQL literal the value travels through.
NAME = re.compile(r"^[^\"'`$\\;|<>&()\x00-\x1f\x7f]{2,80}$")
#: The evidence reference cites the ruling that names this administrator.  Same
#: character policy as the name, long enough to cite a source.
EVIDENCE = re.compile(r"^[^\"'`$\\;|<>&()\x00-\x1f\x7f]{10,200}$")


class BootstrapError(RuntimeError):
    """Any fail-closed refusal of this entry."""


def resolve_request(environ):
    """Validate the bootstrap request, fail closed on anything undeclared."""
    if str(environ.get(CONFIRM_ENV) or "").strip() != CONFIRM_VALUE:
        raise BootstrapError("PLATFORM_SECURITY_ADMIN_CONFIRMATION_REQUIRED:%s" % (CONFIRM_ENV,))
    login = str(environ.get(LOGIN_ENV) or "").strip()
    if not LOGIN.fullmatch(login):
        raise BootstrapError("PLATFORM_SECURITY_ADMIN_LOGIN_INVALID")
    if login in REFUSED_LOGINS:
        raise BootstrapError("PLATFORM_SECURITY_ADMIN_LOGIN_NOT_AN_APPROVER:%s" % (login,))
    name = str(environ.get(NAME_ENV) or "").strip()
    if not name:
        raise BootstrapError("PLATFORM_SECURITY_ADMIN_NAME_REQUIRED")
    if not NAME.fullmatch(name):
        raise BootstrapError("PLATFORM_SECURITY_ADMIN_NAME_INVALID")
    evidence = str(environ.get(EVIDENCE_ENV) or "").strip()
    if not EVIDENCE.fullmatch(evidence):
        raise BootstrapError("PLATFORM_SECURITY_ADMIN_EVIDENCE_REQUIRED")
    return {
        "login": login,
        "name": name,
        "evidence": evidence,
        "output": str(environ.get(OUTPUT_ENV) or DEFAULT_OUTPUT).strip() or DEFAULT_OUTPUT,
    }


def _group_labels(env, group_ids):
    """The name of every group, whether or not it carries an external id.

    A group an add-on or a test created without an ``ir.model.data`` row has no
    xmlid; it is labelled by its database id instead of being dropped, so a
    membership comparison can never pass by silently ignoring a group.
    """
    if not group_ids:
        return []
    rows = env["ir.model.data"].sudo().search(
        [("model", "=", "res.groups"), ("res_id", "in", sorted(set(group_ids)))]
    )
    by_id = {}
    for row in rows:
        by_id.setdefault(row.res_id, []).append("%s.%s" % (row.module, row.name))
    labels = []
    for group_id in sorted(set(group_ids)):
        names = sorted(by_id.get(group_id) or [])
        labels.append(names[0] if names else "#%s" % (group_id,))
    return labels


def _allowed_group_closure_ids(env, seeds):
    """The ids the approver may carry: the declared groups plus their closure.

    The closure is read from the environment rather than hard-coded, because
    which module implies which group is environment knowledge.  A missing seed
    answers with an empty set, which callers treat as "cannot decide" and refuse,
    never as "nothing is allowed but everything passes".
    """
    ids = []
    for seed in seeds:
        if not seed or seed._name != "res.groups":
            return set()
        ids.append(seed.id)
    groups = env["res.groups"].sudo().browse(sorted(set(ids)))
    return set((groups | groups.trans_implied_ids).ids)


def _groups_outside_closure(env, group_ids, allowed_ids):
    """The labels of the memberships the approver closure does not cover."""
    outside = sorted(set(group_ids) - set(allowed_ids))
    if not outside:
        return []
    return _group_labels(env, outside)


def _stored_password(env, user_id):
    """Read the credential fact from the database, not from a cached field."""
    env.cr.execute("SELECT COALESCE(password, '') FROM res_users WHERE id = %s", (user_id,))
    row = env.cr.fetchone()
    return bool(row and str(row[0] or "").strip())


def readback(env, request):
    """Every fact this step asserts, read from the current state.

    The membership fact is the identity's *actual* groups compared with the
    environment's own closure of the two allowed groups.  That is the real
    answer to "does this approver carry a business data scope": the closure
    holds no business role, so anything outside it is a widened identity.  The
    platform helper that answers that question from an administrator identity
    alone is deliberately not used here as evidence of it.
    """
    user = env["res.users"].sudo().with_context(active_test=False).search(
        [("login", "=", request["login"])], limit=1
    )
    Access = env["sc.platform.maintenance.access"].sudo()
    group = env.ref(SECURITY_ADMIN_GROUP_XMLID, raise_if_not_found=False)
    # The declared closure is consumed from the module constant rather than
    # repeated here, so the seeded groups and the reported closure cannot drift.
    seeds = tuple(
        env.ref(xmlid, raise_if_not_found=False) for xmlid in ALLOWED_GROUP_XMLIDS
    )
    allowed_ids = _allowed_group_closure_ids(env, seeds)
    report = {
        "mode": "read_only",
        "writes": 0,
        "database": env.cr.dbname,
        "declared_login": request["login"],
        "declared_name": request["name"],
        "evidence": request["evidence"],
        "security_admin_group": SECURITY_ADMIN_GROUP_XMLID,
        "security_admin_group_exists": bool(group) and group._name == "res.groups",
        "security_admin_member_count": env["res.users"].sudo().with_context(active_test=False).search_count(
            [("groups_id", "in", [group.id])]
        )
        if group and group._name == "res.groups"
        else 0,
        "maintenance_access_rows": Access.search_count([]),
        "approves_maintenance_access": False,
        "allowed_group_closure_ids": sorted(allowed_ids),
        # The labels travel with the ids so a reader can check the closure holds
        # no business role without re-resolving the groups in this environment.
        "allowed_group_closure_labels": _group_labels(env, allowed_ids),
        "allowed_group_closure_complete": bool(allowed_ids),
        "exists": bool(user),
    }
    if not user:
        report["identity"] = None
        return report
    from odoo.addons.smart_core.security.platform_admin import user_is_security_admin

    report["identity"] = {
        "uid": user.id,
        "login": user.login,
        "name": user.name,
        "active": bool(user.active),
        "share": bool(user.share),
        "company_id": user.company_id.id,
        "group_ids": sorted(user.groups_id.ids),
        "group_xmlids": _group_labels(env, user.groups_id.ids),
        "groups_outside_allowed_closure": _groups_outside_closure(
            env, user.groups_id.ids, report["allowed_group_closure_ids"]
        ),
        "is_security_admin": user_is_security_admin(user),
        "has_stored_password": _stored_password(env, user.id),
    }
    return report


def _assert_readable(report, request):
    """The readback must describe the declared identity or nothing at all."""
    if report.get("mode") != "read_only" or int(report.get("writes") or 0) != 0:
        raise BootstrapError("PLATFORM_SECURITY_ADMIN_READBACK_NOT_READ_ONLY")
    if report.get("declared_login") != request["login"]:
        raise BootstrapError("PLATFORM_SECURITY_ADMIN_READBACK_COVERS_ANOTHER_LOGIN")
    if report.get("approves_maintenance_access") is not False:
        raise BootstrapError("PLATFORM_SECURITY_ADMIN_BOOTSTRAP_MUST_NOT_APPROVE")
    if not report.get("security_admin_group_exists"):
        raise BootstrapError("PLATFORM_SECURITY_ADMIN_GROUP_MISSING")
    identity = report.get("identity")
    if identity is None:
        return
    if not report.get("allowed_group_closure_complete"):
        raise BootstrapError("PLATFORM_SECURITY_ADMIN_ALLOWED_GROUP_MISSING")
    outside = identity.get("groups_outside_allowed_closure")
    if outside:
        raise BootstrapError(
            "PLATFORM_SECURITY_ADMIN_HOLDS_UNRELATED_GROUPS:%s" % (",".join(outside),)
        )
    if identity.get("login") != request["login"]:
        raise BootstrapError("PLATFORM_SECURITY_ADMIN_READBACK_OTHER_IDENTITY")
    if identity.get("name") != request["name"]:
        raise BootstrapError("PLATFORM_SECURITY_ADMIN_READBACK_OTHER_NAME")


def _run_operation(env, environ, receipt):
    request = resolve_request(environ)
    registry = env["sc.platform.database.registration"]
    # The governed maintenance principal is the only writer of platform identity.
    registry._assert_governance_principal()
    group = env.ref(SECURITY_ADMIN_GROUP_XMLID, raise_if_not_found=False)
    if not group or group._name != "res.groups":
        raise BootstrapError("PLATFORM_SECURITY_ADMIN_GROUP_MISSING")
    internal = env.ref(INTERNAL_USER_GROUP_XMLID, raise_if_not_found=False)
    if not internal or internal._name != "res.groups":
        raise BootstrapError("PLATFORM_SECURITY_ADMIN_INTERNAL_GROUP_MISSING")
    Access = env["sc.platform.maintenance.access"].sudo()
    access_rows_before = Access.search_count([])

    users = env["res.users"].sudo().with_context(active_test=False)
    user = users.search([("login", "=", request["login"])], limit=1)
    created = False
    writes = 0
    if user:
        after = readback(env, request)
        identity = after["identity"]
        # An account that merely shares the declared login is another person's
        # account: reusing it would attach the control-plane role to whoever
        # that account really is, so the declared name must be the fact.
        if identity["name"] != request["name"]:
            raise BootstrapError("PLATFORM_SECURITY_ADMIN_EXISTING_IDENTITY_MISMATCH")
        if not identity["active"]:
            raise BootstrapError("PLATFORM_SECURITY_ADMIN_EXISTING_IDENTITY_INACTIVE")
        if identity["share"]:
            raise BootstrapError("PLATFORM_SECURITY_ADMIN_EXISTING_IDENTITY_IS_PORTAL")
        conflicting = sorted(
            set(identity["group_xmlids"]) & set(REFUSED_GROUP_XMLIDS)
        )
        if conflicting:
            raise BootstrapError(
                "PLATFORM_SECURITY_ADMIN_EXISTING_IDENTITY_IS_AN_OPERATOR:%s"
                % (",".join(conflicting),)
            )
        # The closure is what the account may carry: internal user plus the
        # control-plane role and the platform's own implications of them.  A
        # business role in the membership would make this one account both the
        # approver and a customer-data holder, which is the combination the
        # owner forbade, so it is refused rather than adopted.
        widened = identity.get("groups_outside_allowed_closure") or []
        if widened:
            raise BootstrapError(
                "PLATFORM_SECURITY_ADMIN_EXISTING_IDENTITY_HAS_UNRELATED_GROUPS:%s"
                % (",".join(widened),)
            )
        if group.id not in user.groups_id.ids:
            groups_before = set(user.groups_id.ids)
            user.write({"groups_id": [(4, group.id)]})
            if set(user.groups_id.ids) - groups_before - {group.id}:
                raise BootstrapError("PLATFORM_SECURITY_ADMIN_UNRELATED_MEMBERSHIP_CHANGED")
            writes += 1
    else:
        user = users.with_context(no_reset_password=True).create({
            "name": request["name"],
            "login": request["login"],
            "active": True,
            "share": False,
            "groups_id": [(6, 0, [internal.id, group.id])],
        })
        created = True
        writes += 1
    env.cr.flush()
    result = readback(env, request)
    _assert_readable(result, request)
    if not (result["identity"] or {}).get("is_security_admin"):
        raise BootstrapError("PLATFORM_SECURITY_ADMIN_POSTCONDITION_FAILED")
    if result["identity"]["group_xmlids"].count(SECURITY_ADMIN_GROUP_XMLID) != 1:
        raise BootstrapError("PLATFORM_SECURITY_ADMIN_GROUP_NOT_EXACT")
    if result["identity"]["has_stored_password"]:
        raise BootstrapError("PLATFORM_SECURITY_ADMIN_MUST_NOT_CARRY_A_CREDENTIAL")
    if result["identity"]["groups_outside_allowed_closure"]:
        raise BootstrapError(
            "PLATFORM_SECURITY_ADMIN_HOLDS_UNRELATED_GROUPS:%s"
            % (",".join(result["identity"]["groups_outside_allowed_closure"]),)
        )
    if result["maintenance_access_rows"] != access_rows_before:
        raise BootstrapError("PLATFORM_SECURITY_ADMIN_BOOTSTRAP_TOUCHED_THE_LEDGER")
    user_id = user.id
    try:
        env.cr.commit()
    except Exception as error:  # noqa: BLE001 - report, never replay silently
        raise BootstrapError(
            "PLATFORM_SECURITY_ADMIN_COMMIT_UNCONFIRMED:uid=%s; do not replay" % (user_id,)
        ) from error
    independent = _independent_readback(env, request)
    _assert_readable(independent, request)
    if not (independent["identity"] or {}).get("is_security_admin"):
        raise BootstrapError("PLATFORM_SECURITY_ADMIN_COMMIT_UNCONFIRMED:uid=%s" % (user_id,))
    committed = {
        "ok": True,
        "entry": ENTRY,
        "login": request["login"],
        "name": request["name"],
        "evidence": request["evidence"],
        "created": created,
        "writes": writes,
        "group_xmlid": SECURITY_ADMIN_GROUP_XMLID,
        "allowed_group_closure_ids": independent["allowed_group_closure_ids"],
        "identity_readback": independent["identity"],
        "identity_groups_outside_allowed_closure": list(
            independent["identity"]["groups_outside_allowed_closure"]
        ),
        "security_admin_member_count": independent["security_admin_member_count"],
        "maintenance_access_rows": independent["maintenance_access_rows"],
        "approves_maintenance_access": False,
    }
    receipt.effects["uid"] = user_id
    try:
        return receipt.succeed(committed)
    except Exception as error:
        raise BootstrapError(
            "PLATFORM_SECURITY_ADMIN_COMMITTED_RECEIPT_FAILED:uid=%s; do not replay" % (user_id,)
        ) from error


def _independent_readback(env, request):
    """Read the identity after commit from a separate transaction."""
    from odoo.api import Environment

    with env.registry.cursor() as cursor:
        return readback(Environment(cursor, env.uid, {}), request)


def run(env, environ):
    request_identity = {
        key: str(environ.get(key) or "")
        for key in (LOGIN_ENV, NAME_ENV, EVIDENCE_ENV)
    }
    output = str(environ.get(OUTPUT_ENV) or DEFAULT_OUTPUT).strip() or DEFAULT_OUTPUT
    with operation_receipt(
        output,
        ENTRY,
        environ.get("PLATFORM_DATABASE_EXECUTION_ID"),
        request_identity,
    ) as receipt:
        return _run_operation(env, environ, receipt)


def _entrypoint():
    shell_env = globals().get("env")
    if shell_env is None:
        raise SystemExit(
            "platform security admin bootstrap must run through odoo shell "
            "(scripts/ops/odoo_shell_exec.sh)"
        )
    try:
        result = run(shell_env, os.environ)
    except Exception as error:
        print("[%s] FAILED: %s" % (ENTRY, error))
        raise
    print(
        "[%s] %s %s with %s (created=%s)"
        % (
            ENTRY,
            result["login"],
            "created" if result["created"] else "verified",
            result["group_xmlid"],
            result["created"],
        )
    )


try:
    env  # noqa: B018 - provided by odoo shell
except NameError:
    pass
else:
    _entrypoint()
