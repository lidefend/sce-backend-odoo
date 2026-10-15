#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Governed runtime binding for the platform security-administrator credential.

Owner ruling (2026-10-16): the independent approver is the named security
administrator, but the approval itself must stay a product capability.  The
approver therefore needs a credential it can authenticate with at the product
entry, and issuing that credential is a separate governed step -- never a
one-off shell that rewrites the authorization row, never an ``APPROVED_BY``
string, and never a credential that is printed, templated or committed.

The immutable entry (``scripts/ops/platform_security_admin_credential.py``)
owns the decision; this transport is the governed runtime binding that gives it
an exact control-plane identity, because that entry needs a database, a cluster
and a rendered stack to run against and must not invent one.

Three properties are deliberate:

* it never issues against an identity it has not just read as the declared
  approver, and the entry itself refuses to take over an account that already
  carries a credential, so this step can neither create the approver nor
  silently replace somebody's password;
* it never approves a maintenance access and never fabricates one.  The entry
  asserts the authorization ledger is exactly as it found it, and this
  transport reads the ledger in separate processes before and after and stops
  when the row count moved;
* the credential itself never travels through this transport.  The entry writes
  it to a governed operator-only file, and every receipt this transport prints
  is scrubbed of any credential value, so nothing can leak into a log, a report
  or a conversation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import daily_runtime_duty_identity as duty_identity  # noqa: E402
import daily_runtime_duty_payload as duty_runtime  # noqa: E402
import daily_runtime_platform_security_admin_bootstrap as binding  # noqa: E402


READBACK_MARKER = "PLATFORM_SECURITY_ADMIN_CREDENTIAL_READBACK="
ENTRY_MARKER = "PLATFORM_SECURITY_ADMIN_CREDENTIAL_ENTRY="
ACTION_ENV = "PLATFORM_SECURITY_ADMIN_CREDENTIAL_ACTION"

ACTIONS = ("readback", "issue", "clear")

#: The immutable platform sources this transport drives and binds to.
CREDENTIAL_ENTRY_SOURCE = "scripts/ops/platform_security_admin_credential.py"
CREDENTIAL_ENTRY_MODULE = "scripts.ops.platform_security_admin_credential"
MOUNT_TOKEN = "__PLATFORM_SECURITY_ADMIN_CREDENTIAL_SCRIPTS_PARENT__"
#: A receipt path inside the throwaway container; the entry's own operator-only
#: credential destination comes from the entry, not from here.
REMOTE_OUTPUT = "/tmp/platform_security_admin_credential.json"
#: Keys that must never appear in a value this transport prints.
SECRET_KEYS = ("password", "secret", "api_key", "token")


class CredentialTransportError(RuntimeError):
    """A stop: the transport refuses to continue rather than guess a fact."""


def _fail(message: str) -> None:
    raise CredentialTransportError(message)


def credential_entry(root: Path | None = None):
    return binding.load_module(
        root or ROOT, CREDENTIAL_ENTRY_SOURCE, "daily_runtime_duty_security_admin_credential_entry"
    )


def declare_request(entry, *, login: str, name: str, evidence: str, action: str) -> dict:
    """Validate the operator's inputs with the entry's own rules, not a copy."""
    environ = {
        entry.LOGIN_ENV: binding._text(login),
        entry.NAME_ENV: binding._text(name),
        entry.EVIDENCE_ENV: binding._text(evidence),
        entry.OUTPUT_ENV: entry.DEFAULT_OUTPUT,
    }
    if action in entry.CONFIRM_VALUES:
        environ[entry.CONFIRM_ENV] = entry.CONFIRM_VALUES[action]
    try:
        return entry.resolve_request(environ, action)
    except entry.CredentialError as exc:
        _fail(str(exc))


def confirmation(entry, action: str) -> str:
    """Only a state-changing action needs the entry's own confirmation."""
    if action == "readback":
        return ""
    declared = binding._text(os.environ.get(entry.CONFIRM_ENV))
    if declared != entry.CONFIRM_VALUES.get(action):
        _fail(
            "the %s action requires its exact confirmation in %s"
            % (action, entry.CONFIRM_ENV)
        )
    return declared


def readback_environment(entry, request: dict) -> list[str]:
    """The declared identity the read path asserts, and nothing that writes."""
    return [
        "-e", "%s=%s" % (entry.LOGIN_ENV, request["login"]),
        "-e", "%s=%s" % (entry.NAME_ENV, request["name"]),
        "-e", "%s=%s" % (entry.EVIDENCE_ENV, request["evidence"]),
        "-e", "%s=readback" % (ACTION_ENV,),
    ]


def entry_environment(entry, request: dict, action: str, execution_id: str) -> list[str]:
    """The declared inputs, the action's own confirmation, and nothing else."""
    return [
        "-e", "%s=%s" % (entry.CONFIRM_ENV, entry.CONFIRM_VALUES[action]),
        "-e", "%s=%s" % (entry.LOGIN_ENV, request["login"]),
        "-e", "%s=%s" % (entry.NAME_ENV, request["name"]),
        "-e", "%s=%s" % (entry.EVIDENCE_ENV, request["evidence"]),
        "-e", "%s=%s" % (entry.OUTPUT_ENV, entry.DEFAULT_OUTPUT),
        "-e", "%s=%s" % (ACTION_ENV, action),
        "-e", "PLATFORM_DATABASE_EXECUTION_ID=%s" % execution_id,
    ]


def readback_script(entry) -> str:
    if MOUNT_TOKEN not in READBACK_SCRIPT:
        _fail("the credential readback template lost its mount placeholder")
    parent = str(Path(binding.PRODUCT_SCRIPTS_MOUNT).parent)
    return (READBACK_SCRIPT % {
        "module": CREDENTIAL_ENTRY_MODULE,
        "marker": READBACK_MARKER,
    }).replace(MOUNT_TOKEN, parent)


def entry_script(entry) -> str:
    if MOUNT_TOKEN not in ENTRY_SCRIPT:
        _fail("the credential binding lost its mount placeholder")
    parent = str(Path(binding.PRODUCT_SCRIPTS_MOUNT).parent)
    return (ENTRY_SCRIPT % {
        "module": CREDENTIAL_ENTRY_MODULE,
        "marker": ENTRY_MARKER,
        "action_env": ACTION_ENV,
    }).replace(MOUNT_TOKEN, parent)


def scrub(value):
    """Drop anything that could be a credential before it is printed.

    The drop is by key name *and* by shape: a credential is text, while a
    boolean or a count that merely shares the name is a fact an audit needs to
    see -- ``has_stored_password`` says whether the account carries a credential,
    which is exactly the state this step is accountable for, and ``token_version``
    says whether a minted token was retired.  Only the value itself is withheld.
    """
    if isinstance(value, dict):
        return {
            key: scrub(item)
            for key, item in value.items()
            if not (isinstance(item, str) and any(marker in str(key).lower() for marker in SECRET_KEYS))
        }
    if isinstance(value, list):
        return [scrub(item) for item in value]
    return value


def assert_readback(report: dict, entry, request: dict, control: dict) -> dict:
    """The readback is a read fact about the declared identity, and nothing more."""
    if report.get("mode") != "read_only" or int(report.get("writes") or 0) != 0:
        _fail("the identity read did not declare itself read-only")
    if binding._text(report.get("database")) != control["database"]:
        _fail("the identity read ran against another control database")
    if binding._text(report.get("declared_login")) != request["login"]:
        _fail("the identity read covers another login than the declared one")
    if not report.get("security_admin_group_exists"):
        _fail("the control plane does not carry the security-administrator group")
    try:
        entry.bootstrap._assert_readable(report, request)
    except entry.bootstrap.BootstrapError as exc:
        _fail(str(exc))
    closure_ids = report.get("allowed_group_closure_ids")
    if not isinstance(closure_ids, list) or not closure_ids:
        _fail("the environment did not declare the approver group closure")
    if int(report.get("maintenance_access_rows") or 0) < 0:
        _fail("the authorization ledger reported an impossible size")
    return report


def assert_entry_result(envelope: dict, entry, request: dict, expected_digest: str, action: str, before: dict) -> dict:
    """The entry's own receipt must be this action on this identity, and no other."""
    if envelope.get("source_sha256") != expected_digest:
        _fail("the credential entry that ran is not the reviewed one")
    result = envelope.get("result")
    if not isinstance(result, dict) or result.get("ok") is not True:
        _fail("the credential entry did not report success")
    if result.get("entry") != entry.ENTRY:
        _fail("the credential entry reported another entry")
    if result.get("action") != action:
        _fail("the credential entry reported another action")
    if binding._text(result.get("login")) != request["login"]:
        _fail("the credential entry acted on another login")
    if binding._text(result.get("name")) != request["name"]:
        _fail("the credential entry acted on another name")
    if result.get("approves_maintenance_access") is not False:
        _fail("the credential entry must never approve a maintenance access")
    if result.get("group_ids_unchanged") is not True:
        _fail("the credential entry reported a membership change")
    if "password" in result:
        _fail("the credential entry returned a credential value; it must only be written")
    if int(result.get("maintenance_access_rows") or 0) != int(before.get("maintenance_access_rows") or 0):
        _fail("the authorization ledger changed across the credential step")
    return result


def execute(
    *,
    action: str,
    login: str,
    name: str,
    evidence: str,
    declaration: Path | None = None,
    tool_root: Path | None = None,
) -> dict:
    if action not in ACTIONS:
        _fail("unsupported security-administrator credential action: %s" % (action,))
    root = tool_root or ROOT
    entry = credential_entry(root)
    request = declare_request(entry, login=login, name=name, evidence=evidence, action=action)
    confirmed = confirmation(entry, action)

    duty = binding.resolve_control_duty(declaration)
    ops_root = Path(duty_identity.load_declaration(declaration).get("ops_root") or "")
    if not ops_root.is_absolute():
        _fail("the declaration must name an absolute ops root")
    env_path = ops_root / ("%s.env" % duty["duty"])
    values = duty_runtime.read_duty_env(env_path, duty)
    stack = duty_runtime.stack_compose_path(ops_root)
    binding.assert_scripts_mount(stack)
    duty_runtime.inspect_odoo_container(duty, values)
    base = duty_runtime.compose_base(duty, ops_root, env_path, stack)

    entry_source = root / CREDENTIAL_ENTRY_SOURCE
    if not entry_source.is_file():
        _fail("the immutable security-administrator credential entry is unavailable")
    entry_digest = hashlib.sha256(entry_source.read_bytes()).hexdigest()
    tool_sha = binding.tool_identity(root)

    def read_identity() -> dict:
        return assert_readback(
            binding._marked_report(
                binding.run_script(
                    binding.one_off_command(duty, base, readback_environment(entry, request)),
                    readback_script(entry),
                    ops_root,
                ),
                READBACK_MARKER,
                "security administrator credential readback",
            ),
            entry,
            request,
            duty,
        )

    before = read_identity()
    if action == "readback":
        return scrub({
            "ok": True,
            "action": "readback",
            "entry": entry.ENTRY,
            "database": duty["database"],
            "target_login": request["login"],
            "writes": 0,
            "tool_sha": tool_sha,
            "entry_source_sha256": entry_digest,
            "identity": before.get("identity"),
            "exist": before.get("exists"),
            "security_admin_member_count": before.get("security_admin_member_count"),
            "maintenance_access_rows": before.get("maintenance_access_rows"),
            "allowed_group_closure_ids": before.get("allowed_group_closure_ids"),
            "allowed_group_closure_labels": before.get("allowed_group_closure_labels"),
            "readback": before,
        })

    execution_id = uuid.uuid4().hex
    envelope = binding._marked_report(
        binding.run_script(
            binding.one_off_command(duty, base, entry_environment(entry, request, action, execution_id)),
            entry_script(entry),
            ops_root,
        ),
        ENTRY_MARKER,
        "security administrator credential entry",
    )
    result = assert_entry_result(envelope, entry, request, entry_digest, action, before)
    after = read_identity()

    if int(after["maintenance_access_rows"]) != int(before["maintenance_access_rows"]):
        _fail("the maintenance authorization ledger changed across the credential step")
    if list(after["identity"].get("group_ids") or []) != list(before["identity"].get("group_ids") or []):
        _fail("the approver membership changed across the credential step")
    if int(after.get("security_admin_member_count") or 0) != int(before.get("security_admin_member_count") or 0):
        _fail("the security-administrator membership count changed across the credential step")
    if action == "issue":
        if not after["identity"].get("has_stored_password"):
            _fail("the credential step reports success but no credential is stored")
    if action == "clear" and after["identity"].get("has_stored_password"):
        _fail("the credential step reports success but a credential is still stored")
    return scrub({
        "ok": True,
        "action": action,
        "entry": entry.ENTRY,
        "database": duty["database"],
        "target_login": request["login"],
        "confirmation": confirmed,
        "writes": int(result.get("writes") or 0),
        "execution_id": execution_id,
        "tool_sha": tool_sha,
        "entry_source_sha256": entry_digest,
        "identity": after.get("identity"),
        "identity_before": before.get("identity"),
        "security_admin_member_count": after.get("security_admin_member_count"),
        "maintenance_access_rows": after.get("maintenance_access_rows"),
        "credential_file": result.get("credential_file"),
        "credential_file_removed": result.get("credential_file_removed"),
        "entry_result": result,
    })


READBACK_SCRIPT = """
import importlib
import json
import os
import sys

sys.path.insert(0, "__PLATFORM_SECURITY_ADMIN_CREDENTIAL_SCRIPTS_PARENT__")
_entry = importlib.import_module("%(module)s")
_request = _entry.resolve_request({
    _entry.LOGIN_ENV: os.environ.get(_entry.LOGIN_ENV, ""),
    _entry.NAME_ENV: os.environ.get(_entry.NAME_ENV, ""),
    _entry.EVIDENCE_ENV: os.environ.get(_entry.EVIDENCE_ENV, ""),
    _entry.OUTPUT_ENV: _entry.DEFAULT_OUTPUT,
}, "readback")
_report = _entry.readback(env, _request)  # noqa: F821
_entry.bootstrap._assert_readable(_report, _request)
_report["writes"] = 0
_report["mode"] = "read_only"
print("%(marker)s" + json.dumps(_report, ensure_ascii=False, sort_keys=True, default=str))
"""

ENTRY_SCRIPT = """
import hashlib
import importlib
import json
import os
import sys

sys.path.insert(0, "__PLATFORM_SECURITY_ADMIN_CREDENTIAL_SCRIPTS_PARENT__")
_entry = importlib.import_module("%(module)s")
with open(_entry.__file__, "rb") as _source_file:
    _digest = hashlib.sha256(_source_file.read()).hexdigest()
_action = os.environ.get("%(action_env)s", "")
_result = _entry.run(env, os.environ, _action)  # noqa: F821
print("%(marker)s" + json.dumps(
    {"source_sha256": _digest, "result": _result},
    ensure_ascii=False,
    sort_keys=True,
    default=str,
))
"""


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=ACTIONS)
    parser.add_argument("--login", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--declaration", default=None)
    args = parser.parse_args(argv)
    declaration = Path(args.declaration) if args.declaration else None
    try:
        result = execute(
            action=args.action,
            login=args.login,
            name=args.name,
            evidence=args.evidence,
            declaration=declaration,
        )
    except (CredentialTransportError, duty_runtime.PayloadEntryError) as exc:
        print("[platform.security_admin.credential] FAILED: %s" % (exc,))
        return 2
    print(json.dumps(scrub(result), ensure_ascii=False, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
