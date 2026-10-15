#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Governed runtime binding for the platform security-administrator bootstrap.

Owner ruling (2026-10-16): an independent approving identity must exist as a
real, named administrator before the maintenance-authorization flow can be used
for real, and creating it is a separate governed bootstrap step rather than a
side effect of any maintenance request.  The immutable entry
(``scripts/ops/platform_security_admin_bootstrap.py``) owns the decision; this
transport is the governed runtime binding that gives it an exact control-plane
identity, because that entry needs a database, a cluster and a rendered stack to
run against and must not invent one.

Nothing here decides a database, a login, a name or an evidence string: the
control duty comes from ``config/ops/daily_runtime_database_duties.v1.json``,
and the login, the name and the evidence come from the operator.  The
confirmation string and the group identity come from the entry itself, loaded
from the same immutable tree this transport runs from, so a second copy cannot
drift.

Two properties are deliberate:

* the transport never approves a maintenance access and never fabricates one.
  The bootstrap entry asserts the authorization ledger is exactly as it found
  it, and this transport reads the ledger before and after in separate
  processes and stops when the row count moved;
* ``readback`` writes nothing and is safe before any write, so the identity is
  asserted from a fresh transaction rather than from the command that made it.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.util
import json
import os
import re
import sys
import tempfile
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import daily_runtime_duty_identity as duty_identity  # noqa: E402
import daily_runtime_duty_payload as duty_runtime  # noqa: E402


READBACK_MARKER = "PLATFORM_SECURITY_ADMIN_BOOTSTRAP_READBACK="
ENTRY_MARKER = "PLATFORM_SECURITY_ADMIN_BOOTSTRAP_ENTRY="

ACTIONS = ("readback", "bootstrap")
#: The control plane owns the registry and is the only duty this entry serves.
PLATFORM_CONTROL_DUTY = "platform_control"
PLATFORM_CONTROL_PURPOSE = "platform_control"

#: The immutable platform sources this transport drives and binds to.
BOOTSTRAP_ENTRY_SOURCE = "scripts/ops/platform_security_admin_bootstrap.py"
RECEIPT_SOURCE = "scripts/ops/platform_database_receipt.py"
#: The reviewed stack mounts the product's scripts tree read-only; the entry is
#: loaded from that mount, never from a baked image copy that could be older.
STACK_SCRIPTS_MOUNT = "${SC_PRODUCT_ROOT}/scripts:/mnt/scripts:ro"
PRODUCT_SCRIPTS_MOUNT = "/mnt/scripts"
BOOTSTRAP_ENTRY_MODULE = "scripts.ops.platform_security_admin_bootstrap"
MOUNT_TOKEN = "__PLATFORM_SECURITY_ADMIN_SCRIPTS_PARENT__"
#: A receipt path inside the throwaway container; the transport asserts the
#: returned result, not this file.
REMOTE_OUTPUT = "/tmp/platform_security_admin_bootstrap.json"

_MODULES: dict[str, object] = {}


class BootstrapTransportError(RuntimeError):
    """A stop: the transport refuses to continue rather than guess a fact."""


def _fail(message: str) -> None:
    raise BootstrapTransportError(message)


def _text(value) -> str:
    return str(value or "").strip()


def load_module(root: Path, relative: str, name: str):
    """Load one immutable platform source from this entry's own tree."""
    key = "%s:%s" % (name, root)
    if key in _MODULES:
        return _MODULES[key]
    source = root / relative
    if not source.is_file():
        _fail("the immutable platform source %s is unavailable" % relative)
    inserted = False
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
        inserted = True
    saved = {
        module_name: module
        for module_name, module in list(sys.modules.items())
        if module_name == "scripts" or module_name.startswith("scripts.")
    }
    for module_name in saved:
        sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(name, source)
    if spec is None or spec.loader is None:
        _fail("the immutable platform source %s cannot be loaded" % relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
        for module_name, value in saved.items():
            sys.modules[module_name] = value
        if inserted:
            sys.path.remove(str(root))
    _MODULES[key] = module
    return module


def bootstrap_entry(root: Path | None = None):
    return load_module(
        root or ROOT, BOOTSTRAP_ENTRY_SOURCE, "daily_runtime_duty_security_admin_entry"
    )


def resolve_control_duty(declaration: Path | None = None) -> dict:
    """Resolve the platform control duty this step must run against."""
    try:
        duty = duty_identity.resolve(PLATFORM_CONTROL_DUTY, declaration)
    except duty_identity.DutyIdentityError as exc:
        _fail(str(exc))
    if duty["data_purpose"] != PLATFORM_CONTROL_PURPOSE:
        _fail(
            "the platform control duty is declared %s, not %s: a security "
            "administrator bootstrap never runs inside a data space"
            % (duty["data_purpose"], PLATFORM_CONTROL_PURPOSE)
        )
    return duty


def declare_request(entry, *, login: str, name: str, evidence: str) -> dict:
    """Validate the operator's inputs with the entry's own rules, not a copy."""
    environ = {
        entry.CONFIRM_ENV: entry.CONFIRM_VALUE,
        entry.LOGIN_ENV: _text(login),
        entry.NAME_ENV: _text(name),
        entry.EVIDENCE_ENV: _text(evidence),
        entry.OUTPUT_ENV: REMOTE_OUTPUT,
    }
    try:
        return entry.resolve_request(environ)
    except entry.BootstrapError as exc:
        _fail(str(exc))


def confirmation(entry, action: str) -> str:
    """Only the write action needs the entry's own confirmation."""
    if action == "readback":
        return ""
    declared = _text(os.environ.get(entry.CONFIRM_ENV))
    if declared != entry.CONFIRM_VALUE:
        _fail(
            "the %s action requires its exact confirmation in %s"
            % (action, entry.CONFIRM_ENV)
        )
    return declared


def assert_scripts_mount(stack: Path) -> None:
    """The reviewed stack must expose the product's scripts tree read-only."""
    if stack.is_symlink() or not stack.is_file():
        _fail("the rendered duty stack is unavailable")
    if STACK_SCRIPTS_MOUNT not in stack.read_text(encoding="utf-8"):
        _fail(
            "the rendered duty stack does not mount the product scripts tree, so "
            "the bootstrap entry cannot be loaded from the deployed source"
        )


def readback_script(entry) -> str:
    if MOUNT_TOKEN not in READBACK_SCRIPT:
        _fail("the readback template lost its mount placeholder")
    parent = str(Path(PRODUCT_SCRIPTS_MOUNT).parent)
    script = READBACK_SCRIPT % {
        "module": BOOTSTRAP_ENTRY_MODULE,
        "marker": READBACK_MARKER,
        "login_env": entry.LOGIN_ENV,
        "name_env": entry.NAME_ENV,
        "evidence_env": entry.EVIDENCE_ENV,
    }
    return script.replace(MOUNT_TOKEN, parent)


def entry_script() -> str:
    if MOUNT_TOKEN not in ENTRY_SCRIPT:
        _fail("the bootstrap binding lost its mount placeholder")
    parent = str(Path(PRODUCT_SCRIPTS_MOUNT).parent)
    return (ENTRY_SCRIPT % {
        "module": BOOTSTRAP_ENTRY_MODULE,
        "marker": ENTRY_MARKER,
    }).replace(MOUNT_TOKEN, parent)


def entry_environment(entry, request: dict, execution_id: str) -> list[str]:
    """The declared inputs, plus the entry's own confirmation, and nothing else."""
    return [
        "-e", "%s=%s" % (entry.CONFIRM_ENV, entry.CONFIRM_VALUE),
        "-e", "%s=%s" % (entry.LOGIN_ENV, request["login"]),
        "-e", "%s=%s" % (entry.NAME_ENV, request["name"]),
        "-e", "%s=%s" % (entry.EVIDENCE_ENV, request["evidence"]),
        "-e", "%s=%s" % (entry.OUTPUT_ENV, REMOTE_OUTPUT),
        "-e", "PLATFORM_DATABASE_EXECUTION_ID=%s" % execution_id,
    ]


def one_off_command(duty: dict, base: list[str], extra_env: list[str]) -> list[str]:
    return base + [
        "run", "--rm", "--no-deps", "-T",
        "--label", "sc.daily-duty-security-admin-bootstrap=true",
        "--label", "sc.daily-duty=%s" % duty["duty"],
        *extra_env,
        "--entrypoint", duty_runtime.APPLICATION_ENTRY,
        "odoo", "shell", "-c", duty_runtime.ODOO_CONF,
        "-d", duty["database"],
        "--no-http", "--log-level=error",
    ]


def run_script(command: list[str], script: str, ops_root: Path) -> str:
    """Present one governed entry script to the duty's own definition on stdin."""
    with tempfile.TemporaryDirectory() as workspace:
        stub = Path(workspace) / "platform_security_admin_bootstrap_entry.py"
        stub.write_text(script, encoding="utf-8")
        try:
            with stub.open("r", encoding="utf-8") as source:
                return duty_runtime.run(command, stdin=source, cwd=str(ops_root))
        except duty_runtime.PayloadEntryError as exc:
            _fail(str(exc))


def _marked_report(output: str, marker: str, what: str) -> dict:
    for line in reversed(output.splitlines()):
        row = line.strip()
        if row.startswith(marker):
            try:
                report = json.loads(row[len(marker):])
            except json.JSONDecodeError as exc:
                _fail("the %s report is not JSON: %s" % (what, exc))
            if isinstance(report, dict):
                return report
            _fail("the %s report is not an object" % what)
    _fail("the %s emitted no report" % what)


def readback_report(output: str) -> dict:
    return _marked_report(output, READBACK_MARKER, "security administrator readback")


def entry_report(output: str) -> dict:
    return _marked_report(output, ENTRY_MARKER, "security administrator entry")


def assert_readback(report: dict, entry, request: dict, control: dict) -> dict:
    """The readback is a read fact about the declared identity, and nothing more."""
    if report.get("mode") != "read_only" or int(report.get("writes") or 0) != 0:
        _fail("the identity read did not declare itself read-only")
    if _text(report.get("database")) != control["database"]:
        _fail("the identity read ran against another control database")
    if _text(report.get("declared_login")) != request["login"]:
        _fail("the identity read covers another login than the declared one")
    if not report.get("security_admin_group_exists"):
        _fail("the control plane does not carry the security-administrator group")
    try:
        entry._assert_readable(report, request)
    except entry.BootstrapError as exc:
        _fail(str(exc))
    rows = int(report.get("maintenance_access_rows") or 0)
    if rows < 0:
        _fail("the authorization ledger reported an impossible size")
    return report


def assert_entry_result(envelope: dict, entry, request: dict, expected_digest: str, before: dict) -> dict:
    """The entry's own receipt must be this bootstrap and no other."""
    if envelope.get("source_sha256") != expected_digest:
        _fail("another security-administrator entry reported this bootstrap")
    result = envelope.get("result")
    if not isinstance(result, dict) or result.get("ok") is not True:
        _fail("the security-administrator bootstrap did not report a committed success")
    if result.get("status") != "passed":
        _fail("the security-administrator bootstrap did not pass")
    if _text(result.get("entry")) != entry.ENTRY:
        _fail("another platform entry reported this bootstrap")
    if _text(result.get("login")) != request["login"]:
        _fail("the bootstrap established another login")
    if _text(result.get("name")) != request["name"]:
        _fail("the bootstrap established another name")
    if _text(result.get("group_xmlid")) != entry.SECURITY_ADMIN_GROUP_XMLID:
        _fail("the bootstrap granted another group than the security-administrator one")
    if not isinstance(result.get("created"), bool):
        _fail("the bootstrap did not report whether it created or reused the identity")
    if result.get("approves_maintenance_access") is not False:
        _fail("the bootstrap claims it approved a maintenance access")
    closure = result.get("identity_groups_outside_allowed_closure")
    if not isinstance(closure, list):
        _fail("the bootstrap did not report the established identity's group closure")
    if closure:
        _fail("the bootstrap established an identity outside the approver closure")
    if int(result.get("maintenance_access_rows") or 0) != int(before["maintenance_access_rows"]):
        _fail("the bootstrap changed the maintenance authorization ledger")
    identity = result.get("identity_readback")
    if not isinstance(identity, dict):
        _fail("the bootstrap reported no identity readback")
    if identity.get("is_security_admin") is not True:
        _fail("the established identity is not a control-plane security administrator")
    if identity.get("has_stored_password") is not False:
        _fail("the established identity carries a stored credential")
    if _text(identity.get("name")) != request["name"]:
        _fail("the established identity is not the declared named person")
    if identity.get("groups_outside_allowed_closure"):
        _fail("the established identity carries groups outside the approver closure")
    if identity.get("active") is not True or identity.get("share") is not False:
        _fail("the established identity is not an active internal account")
    if int(result.get("writes") or 0) < 0:
        _fail("the bootstrap reported an impossible write count")
    if result["created"] and int(result.get("writes") or 0) < 1:
        _fail("the bootstrap reported a creation without a write")
    effects = result.get("effects")
    if not isinstance(effects, dict) or int(effects.get("uid") or 0) <= 0:
        _fail("the bootstrap reported no audited identity identity")
    return result


def assert_identity_after_creation(report: dict, entry, request: dict, result: dict) -> None:
    """A separate read must show the identity, and only the identity, changed."""
    identity = report.get("identity")
    if not isinstance(identity, dict):
        _fail("the identity is not readable after the bootstrap")
    if identity.get("login") != request["login"]:
        _fail("the readback after the bootstrap covers another identity")
    if _text(identity.get("name")) != request["name"]:
        _fail("the readback after the bootstrap covers another name")
    if identity.get("is_security_admin") is not True:
        _fail("the identity is not a security administrator after the bootstrap")
    if identity.get("has_stored_password") is not False:
        _fail("the identity carries a stored credential after the bootstrap")
    if identity.get("groups_outside_allowed_closure"):
        _fail("the identity carries groups outside the approver closure after the bootstrap")
    if identity.get("group_xmlids", []).count(entry.SECURITY_ADMIN_GROUP_XMLID) != 1:
        _fail("the identity does not carry the security-administrator group exactly once")


def tool_identity(root: Path) -> str:
    marker = root / "DEPLOYMENT_TOOL_SHA"
    if not marker.is_file():
        return ""
    tool_sha = marker.read_text(encoding="utf-8").strip()
    if tool_sha != root.name:
        _fail("the immutable deployment tool identity differs")
    return tool_sha


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
        _fail("unsupported security-administrator action: %s" % action)
    root = tool_root or ROOT
    entry = bootstrap_entry(root)
    request = declare_request(entry, login=login, name=name, evidence=evidence)
    confirmed = confirmation(entry, action)

    duty = resolve_control_duty(declaration)
    ops_root = Path(duty_identity.load_declaration(declaration).get("ops_root") or "")
    if not ops_root.is_absolute():
        _fail("the declaration must name an absolute ops root")
    env_path = ops_root / ("%s.env" % duty["duty"])
    values = duty_runtime.read_duty_env(env_path, duty)
    stack = duty_runtime.stack_compose_path(ops_root)
    assert_scripts_mount(stack)
    duty_runtime.inspect_odoo_container(duty, values)
    base = duty_runtime.compose_base(duty, ops_root, env_path, stack)

    entry_source = root / BOOTSTRAP_ENTRY_SOURCE
    if not entry_source.is_file():
        _fail("the immutable security-administrator entry is unavailable")
    entry_digest = hashlib.sha256(entry_source.read_bytes()).hexdigest()
    tool_sha = tool_identity(root)

    before = assert_readback(
        readback_report(run_script(one_off_command(duty, base, []), readback_script(entry), ops_root)),
        entry,
        request,
        duty,
    )
    if action == "readback":
        return {
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
            "readback": before,
        }

    execution_id = uuid.uuid4().hex
    envelope = entry_report(
        run_script(
            one_off_command(duty, base, entry_environment(entry, request, execution_id)),
            entry_script(),
            ops_root,
        )
    )
    result = assert_entry_result(envelope, entry, request, entry_digest, before)
    after = assert_readback(
        readback_report(run_script(one_off_command(duty, base, []), readback_script(entry), ops_root)),
        entry,
        request,
        duty,
    )
    assert_identity_after_creation(after, entry, request, result)
    if int(after["maintenance_access_rows"]) != int(before["maintenance_access_rows"]):
        _fail("the maintenance authorization ledger changed across the bootstrap")
    expected_members = int(before.get("security_admin_member_count") or 0) + (
        1 if result["created"] else 0
    )
    if int(after.get("security_admin_member_count") or 0) != expected_members:
        _fail("the security-administrator membership count is not the declared one")
    return {
        "ok": True,
        "action": "bootstrap",
        "entry": entry.ENTRY,
        "database": duty["database"],
        "target_login": request["login"],
        "confirmation": confirmed,
        "created": result["created"],
        "writes": int(result.get("writes") or 0),
        "execution_id": execution_id,
        "tool_sha": tool_sha,
        "entry_source_sha256": entry_digest,
        "identity": after.get("identity"),
        "security_admin_member_count": after.get("security_admin_member_count"),
        "maintenance_access_rows": after.get("maintenance_access_rows"),
        "readback_before": before,
        "entry_result": result,
    }


READBACK_SCRIPT = """
import importlib
import json
import os
import sys

sys.path.insert(0, "__PLATFORM_SECURITY_ADMIN_SCRIPTS_PARENT__")
_entry = importlib.import_module("%(module)s")
_request = {
    "login": os.environ.get("%(login_env)s", ""),
    "name": os.environ.get("%(name_env)s", ""),
    "evidence": os.environ.get("%(evidence_env)s", ""),
}
_report = _entry.readback(env, _request)  # noqa: F821
_entry._assert_readable(_report, _request)
print("%(marker)s" + json.dumps(_report, ensure_ascii=False, sort_keys=True, default=str))
"""

ENTRY_SCRIPT = """
import hashlib
import importlib
import json
import os
import sys

sys.path.insert(0, "__PLATFORM_SECURITY_ADMIN_SCRIPTS_PARENT__")
_entry = importlib.import_module("%(module)s")
with open(_entry.__file__, "rb") as _source_file:
    _digest = hashlib.sha256(_source_file.read()).hexdigest()
_result = _entry.run(env, os.environ)  # noqa: F821
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
    except (BootstrapTransportError, duty_runtime.PayloadEntryError) as exc:
        print("[platform.security_admin.bootstrap] FAILED: %s" % (exc,))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
