#!/usr/bin/env python3
"""Register one declared daily duty in the platform database registry (P4).

Owner ruling (2026-10-15): the platform model owns the registration fact, and
the unified onboarding mechanism must be the only writer.  The registration
entry (``scripts/ops/platform_database_register.py``) already exists and already
refuses whatever the declaration does not authorize, but it has no governed
runtime binding: it needs an exact control-plane/target/cluster identity, which
is exactly what a *duty* is.  This entry is that binding -- it resolves every
runtime fact from ``config/ops/daily_runtime_database_duties.v1.json``, drives
the immutable registration entry inside the platform control duty's own
rendered stack, and reads the registration back in a separate process.

Nothing here decides a tenant, a purpose, an environment role or a strategy:

* the target database, its data purpose, its tenant key and its filter come
  from the duty declaration;
* the environment role and the strategy come from the platform's own
  declaration vocabulary (``data_space_provisioning``), loaded from the same
  immutable tree this entry runs from, so a second copy cannot drift;
* the lifecycle state vocabulary comes from ``database_governance``.

Three properties are deliberate:

* the platform control plane is not a data space.  It carries no data purpose
  and is therefore refused here instead of being registered as one;
* registering is idempotent in the safe direction only: an existing row that
  matches the declaration is reused and the entry does not write, while an
  existing row that names another tenant, purpose, role, strategy or filter is
  a stop.  A registration identity is never taken over or rewritten;
* ``readback`` runs as a separate process and proves it wrote nothing, so the
  registration is asserted from a fresh transaction rather than from the
  command that made it.
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
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import daily_runtime_duty_identity as duty_identity  # noqa: E402
import daily_runtime_duty_payload as duty_runtime  # noqa: E402


MARKER = "DAILY_DUTY_DATABASE_REGISTRATION="
READBACK_MARKER = "DAILY_DUTY_DATABASE_REGISTRATION_READBACK="
ENTRY_MARKER = "DAILY_DUTY_DATABASE_REGISTRATION_ENTRY="

ACTIONS = ("readback", "register")
CONFIRMATIONS = {
    "register": (
        "CONFIRM_DAILY_DUTY_DATABASE_REGISTRATION",
        "REGISTER_DECLARED_DAILY_DUTY_IN_PLATFORM_REGISTRY",
    ),
}
#: The control plane owns the registry; it is not a data space of its own.
PLATFORM_CONTROL_DUTY = "platform_control"
#: The immutable platform sources this entry drives and binds to.
REGISTER_ENTRY_SOURCE = "scripts/ops/platform_database_register.py"
RECEIPT_SOURCE = "scripts/ops/platform_database_receipt.py"
PROVISIONING_SOURCE = "addons/smart_core/security/data_space_provisioning.py"
GOVERNANCE_SOURCE = "addons/smart_core/security/database_governance.py"
#: The reviewed stack mounts the product's scripts tree read-only; the
#: registration entry is loaded from that mount, never from a baked image copy
#: that could be older than the deployed tree.
STACK_SCRIPTS_MOUNT = "${SC_PRODUCT_ROOT}/scripts:/mnt/scripts:ro"
PRODUCT_SCRIPTS_MOUNT = "/mnt/scripts"
REGISTER_ENTRY_MODULE = "scripts.ops.platform_database_register"

SAFE_DUTY_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
REASON = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 .,;:_-]{9,199}$")

DATABASE_TOKEN = "__DAILY_DUTY_DATABASE__"
MOUNT_TOKEN = "__DAILY_DUTY_PRODUCT_SCRIPTS_PARENT__"

#: The registration read runs in the platform control plane and only reads.
READBACK_SCRIPT = """
import json

_Registry = env["sc.platform.database.registration"].sudo()  # noqa: F821
_row = _Registry.search([("db_name", "=", "__DAILY_DUTY_DATABASE__")], limit=1)
_report = {
    "mode": "read_only",
    "writes": 0,
    "database": env.cr.dbname,  # noqa: F821
    "target_database": "__DAILY_DUTY_DATABASE__",
    "registered": bool(_row),
    "registration": _row.readback() if _row else None,
    "operations": [
        {
            "operation": _operation.operation,
            "from_state": _operation.from_state or "",
            "to_state": _operation.to_state or "",
            "actor_login": _operation.actor_id.login or "",
        }
        for _operation in (_row.operation_ids.sorted("id") if _row else [])
    ],
}
print("%(marker)s" + json.dumps(_report, ensure_ascii=False, sort_keys=True, default=str))
""" % {"marker": READBACK_MARKER}

#: One write path: the immutable platform registration entry, driven with the
#: declared facts.  The entry commits its own transaction; this stub only
#: presents the reviewed source and reports its digest back, so a container that
#: carries another copy of the entry is refused instead of trusted.
REGISTER_SCRIPT = """
import hashlib
import importlib
import json
import os
import sys

sys.path.insert(0, "__DAILY_DUTY_PRODUCT_SCRIPTS_PARENT__")
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
""" % {"marker": ENTRY_MARKER, "module": REGISTER_ENTRY_MODULE}

_MODULES: dict[str, object] = {}


class RegistrationEntryError(RuntimeError):
    """A stop: the entry refuses to continue rather than guess a fact."""


def _fail(message: str) -> None:
    raise RegistrationEntryError(message)


def _text(value) -> str:
    return str(value or "").strip()


def load_module(root: Path, relative: str, name: str):
    """Load one immutable platform source from this entry's own tree.

    The platform owns the rules, so this entry validates the declaration with
    the platform's modules instead of restating them.  The sources are read
    from ``root`` -- the same immutable tree the deployment installs -- so the
    entry cannot drift onto a second, filesystem copy of a declaration.
    """
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


def provisioning_policy(root: Path | None = None):
    return load_module(
        root or ROOT, PROVISIONING_SOURCE, "daily_runtime_duty_registration_provisioning"
    )


def governance_policy(root: Path | None = None):
    return load_module(
        root or ROOT, GOVERNANCE_SOURCE, "daily_runtime_duty_registration_governance"
    )


def register_entry(root: Path | None = None):
    return load_module(
        root or ROOT, REGISTER_ENTRY_SOURCE, "daily_runtime_duty_registration_entry"
    )


def resolve_registration_target(duty_name: str, declaration: Path | None = None) -> dict:
    """Resolve a duty that the platform registry may carry, or stop."""
    if not SAFE_DUTY_NAME.fullmatch(duty_name or ""):
        _fail("duty name is not a safe identifier")
    try:
        duty = duty_identity.resolve(duty_name, declaration)
    except duty_identity.DutyIdentityError as exc:
        _fail(str(exc))
    provisioning = provisioning_policy()
    purpose = duty["data_purpose"]
    if purpose not in provisioning.PURPOSE_STRATEGY:
        _fail(
            "duty %s is declared %s, which is not a registered data purpose: the "
            "platform control plane owns the registry and is not a data space"
            % (duty_name, purpose)
        )
    role = provisioning.PURPOSE_ENVIRONMENT_ROLE[purpose]
    strategy = provisioning.PURPOSE_STRATEGY[purpose]
    if purpose == provisioning.CUSTOMER_PURPOSE and not duty["tenant_key"]:
        _fail("a customer duty must declare the tenant key its database is registered for")
    duty["environment_role"] = role
    duty["strategy"] = strategy
    return duty


def registration_reason(value: str) -> str:
    """The operator's justification for this registration, as an input."""
    text = _text(value)
    if not REASON.fullmatch(text):
        _fail(
            "the register action must state why this database is being registered "
            "(10-200 characters, one printable line)"
        )
    return text


def assert_scripts_mount(stack: Path) -> None:
    """The reviewed stack must expose the product's scripts tree read-only."""
    if stack.is_symlink() or not stack.is_file():
        _fail("the rendered duty stack is unavailable")
    if STACK_SCRIPTS_MOUNT not in stack.read_text(encoding="utf-8"):
        _fail(
            "the rendered duty stack does not mount the product scripts tree, so "
            "the registration entry cannot be loaded from the deployed source"
        )


def readback_script(duty: dict) -> str:
    if DATABASE_TOKEN not in READBACK_SCRIPT:
        _fail("the registry read template lost its binding placeholder")
    return READBACK_SCRIPT.replace(DATABASE_TOKEN, duty["database"])


def register_script() -> str:
    if MOUNT_TOKEN not in REGISTER_SCRIPT:
        _fail("the registration binding lost its mount placeholder")
    parent = str(Path(PRODUCT_SCRIPTS_MOUNT).parent)
    return REGISTER_SCRIPT.replace(MOUNT_TOKEN, parent)


def readback_command(duty: dict, base: list[str]) -> list[str]:
    return base + [
        "run", "--rm", "--no-deps", "-T",
        "--label", "sc.daily-duty-database-registration=true",
        "--label", "sc.daily-duty=%s" % duty["duty"],
        "--entrypoint", duty_runtime.APPLICATION_ENTRY,
        "odoo", "shell", "-c", duty_runtime.ODOO_CONF,
        "-d", duty["database"],
        "--no-http", "--log-level=error",
    ]


def register_environment(duty: dict, entry, reason: str) -> list[str]:
    """The declared facts, plus the entry's own confirmation, and nothing else."""
    return [
        "-e", "%s=%s" % (entry.CONFIRM_ENV, entry.CONFIRM_VALUE),
        "-e", "%s=%s" % (entry.TARGET_ENV, duty["database"]),
        "-e", "%s=%s" % (entry.ROLE_ENV, duty["environment_role"]),
        "-e", "%s=%s" % (entry.PURPOSE_ENV, duty["data_purpose"]),
        "-e", "%s=%s" % (entry.TENANT_ENV, duty["tenant_key"]),
        "-e", "%s=%s" % (entry.DBFILTER_ENV, duty["dbfilter"]),
        "-e", "%s=%s" % (entry.REASON_ENV, reason),
    ]


def register_command(duty: dict, base: list[str], extra_env: list[str]) -> list[str]:
    return base + [
        "run", "--rm", "--no-deps", "-T",
        "--label", "sc.daily-duty-database-registration=true",
        "--label", "sc.daily-duty=%s" % duty["duty"],
        *extra_env,
        "--entrypoint", duty_runtime.APPLICATION_ENTRY,
        "odoo", "shell", "-c", duty_runtime.ODOO_CONF,
        "-d", duty["database"],
        "--no-http", "--log-level=error",
    ]


def run_script(command: list[str], script: str, ops_root: Path) -> str:
    """Present one governed entry script to the duty's own definition on stdin."""
    import tempfile

    with tempfile.TemporaryDirectory() as workspace:
        stub = Path(workspace) / "database_registration_entry.py"
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
    _fail("the %s emitted no report" % what)


def readback_report(output: str) -> dict:
    return _marked_report(output, READBACK_MARKER, "registration readback")


def register_report(output: str) -> dict:
    return _marked_report(output, ENTRY_MARKER, "registration entry")


def assert_readback(report: dict, duty: dict, control: dict, *, registered: bool | None = None) -> bool:
    """The registration is a read fact about the declared duty, and nothing more."""
    governance = governance_policy()
    if report.get("mode") != "read_only" or int(report.get("writes") or 0) != 0:
        _fail("the registry read did not declare itself read-only")
    if _text(report.get("database")) != control["database"]:
        _fail("the registry read ran against another control database")
    if _text(report.get("target_database")) != duty["database"]:
        _fail("the registry read covers another database than the duty's")
    found = report.get("registered")
    if not isinstance(found, bool):
        _fail("the registry read did not report whether the database is registered")
    if registered is not None and found != registered:
        _fail(
            "the database is %s in the registry, not %s"
            % ("registered" if found else "absent", "registered" if registered else "absent")
        )
    if not found:
        return False
    registration = report.get("registration")
    if not isinstance(registration, dict):
        _fail("the registry read reported no registration facts")
    expected = {
        "db_name": duty["database"],
        "dbfilter": duty["dbfilter"],
        "data_purpose": duty["data_purpose"],
        "environment_role": duty["environment_role"],
        "strategy": duty["strategy"],
        "tenant_key": duty["tenant_key"],
    }
    for key, value in expected.items():
        if _text(registration.get(key)) != value:
            _fail("the registered %s is not the declared one" % key)
    state = _text(registration.get("lifecycle_state"))
    if state not in governance.DATABASE_LIFECYCLE_STATES:
        _fail("the registered lifecycle state is not a declared one")
    if registration.get("grants_business_data_scope") is not False:
        _fail("the registration claims a business data scope")
    operations = report.get("operations")
    if not isinstance(operations, list):
        _fail("the registry read reported no operation history")
    register_operations = [
        operation
        for operation in operations
        if isinstance(operation, dict) and _text(operation.get("operation")) == "register"
    ]
    if len(register_operations) != 1:
        _fail("the registration does not carry exactly one audited register operation")
    if _text(register_operations[0].get("from_state")) or _text(
        register_operations[0].get("to_state")
    ) != governance.DATABASE_LIFECYCLE_INITIAL_STATE:
        _fail("the audited register operation did not create the declared initial state")
    return True


def assert_register_entry(result: dict, duty: dict, entry, reason: str) -> None:
    """The entry's own receipt must be this registration and no other."""
    if not isinstance(result, dict) or result.get("ok") is not True:
        _fail("the platform registration entry did not report a committed success")
    if result.get("status") != "passed":
        _fail("the platform registration entry did not pass")
    if _text(result.get("entry")) != entry.ENTRY:
        _fail("another platform entry reported this registration")
    for key, value in (
        ("db_name", duty["database"]),
        ("environment_role", duty["environment_role"]),
        ("data_purpose", duty["data_purpose"]),
    ):
        if _text(result.get(key)) != value:
            _fail("the platform entry registered another %s" % key)
    readback = result.get("registration_readback")
    if not isinstance(readback, dict) or _text(readback.get("db_name")) != duty["database"]:
        _fail("the platform entry reported another registration readback")
    request = readback.get("operation_request")
    if not isinstance(request, dict) or _text(request.get("reason")) != reason:
        _fail("the audited register operation does not carry this run's reason")
    if int(result.get("operation_id") or 0) <= 0:
        _fail("the platform entry reported no audited operation identity")


def tool_identity(root: Path) -> str:
    marker = root / "DEPLOYMENT_TOOL_SHA"
    if not marker.is_file():
        return ""
    tool_sha = marker.read_text(encoding="utf-8").strip()
    if tool_sha != root.name:
        _fail("the immutable deployment tool identity differs")
    return tool_sha


def execute(
    duty_name: str,
    *,
    action: str,
    reason: str = "",
    declaration: Path | None = None,
    tool_root: Path | None = None,
) -> dict:
    if action not in ACTIONS:
        _fail("unsupported registration action: %s" % action)
    duty = resolve_registration_target(duty_name, declaration)
    control = duty_identity.resolve(PLATFORM_CONTROL_DUTY, declaration)
    if duty["database"] == control["database"]:
        _fail("a duty never registers the platform control plane as a data space")
    ops_root = Path(duty_identity.load_declaration(declaration).get("ops_root") or "")
    if not ops_root.is_absolute():
        _fail("the declaration must name an absolute ops root")
    env_path = ops_root / ("%s.env" % control["duty"])
    values = duty_runtime.read_duty_env(env_path, control)
    stack = duty_runtime.stack_compose_path(ops_root)
    assert_scripts_mount(stack)
    application = duty_runtime.inspect_odoo_container(control, values)
    base = duty_runtime.compose_base(control, ops_root, env_path, stack)

    root = tool_root or ROOT
    entry = register_entry(root)
    provisioning_policy(root)
    governance_policy(root)
    entry_source = root / REGISTER_ENTRY_SOURCE
    if not entry_source.is_file():
        _fail("the immutable platform registration entry is unavailable")
    entry_source_sha256 = hashlib.sha256(entry_source.read_bytes()).hexdigest()
    tool_sha = tool_identity(root)

    confirmation = ""
    checked_reason = ""
    if action in CONFIRMATIONS:
        variable, expected = CONFIRMATIONS[action]
        if os.environ.get(variable) != expected:
            _fail("%s must be set to the exact confirmation value" % variable)
        confirmation = expected
    if action == "register":
        checked_reason = registration_reason(reason)

    before = readback_report(
        run_script(readback_command(control, base), readback_script(duty), ops_root)
    )
    assert_readback(before, duty, control)
    registered_before = bool(before["registered"])

    created = False
    entry_report: dict = {}
    if action == "register" and registered_before:
        entry_report = {"reused": True, "reason": "the declared database is already registered"}
    elif action == "register":
        output = run_script(
            register_command(
                control, base, register_environment(duty, entry, checked_reason)
            ),
            register_script(),
            ops_root,
        )
        entry_report = register_report(output)
        if _text(entry_report.get("source_sha256")) != entry_source_sha256:
            _fail("the registration entry that ran is not the immutable one this tree carries")
        assert_register_entry(entry_report.get("result"), duty, entry, checked_reason)
        created = True

    after = readback_report(
        run_script(readback_command(control, base), readback_script(duty), ops_root)
    )
    if action == "register":
        # A registration that did not write must leave the registry exactly as
        # it found it; a registry that moved is a stop, not a new fact to read.
        # Only then is the resulting registration interpreted.
        if after != before and not created:
            _fail("the registry changed although this run refused to write")
        assert_readback(after, duty, control, registered=True)
    else:
        # A read-only action proves it stayed read-only before anything else is
        # believed about the second read: a registry that moved between the two
        # reads is a stop, not a new fact to interpret.
        if before != after:
            _fail("the registration readback changed the duty's registry state")
        assert_readback(after, duty, control)

    return {
        "schema_version": "daily_runtime_duty_database_registration.v1",
        "action": action,
        "duty": duty["duty"],
        "database": duty["database"],
        "database_role": duty["database_role"],
        "control_duty": control["duty"],
        "control_database": control["database"],
        "environment_id": duty["environment_id"],
        "tenant_key": duty["tenant_key"],
        "data_purpose": duty["data_purpose"],
        "environment_role": duty["environment_role"],
        "strategy": duty["strategy"],
        "dbfilter": duty["dbfilter"],
        "confirmed": confirmation,
        "reason": checked_reason,
        "created": created,
        "registered_before": registered_before,
        "entry_source_sha256": entry_source_sha256,
        "entry_report": entry_report,
        "registration_before": before,
        "registration_after": after,
        "application": application,
        "stack_compose": str(stack),
        "control_environment": str(env_path),
        "tool_sha": tool_sha,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=list(ACTIONS))
    parser.add_argument("--duty", required=True)
    parser.add_argument("--reason", default="")
    parser.add_argument("--declaration", default="")
    parser.add_argument("--evidence", default="")
    args = parser.parse_args(argv)
    try:
        evidence = execute(
            args.duty,
            action=args.action,
            reason=args.reason,
            declaration=Path(args.declaration) if args.declaration else None,
        )
    except (
        RegistrationEntryError,
        duty_identity.DutyIdentityError,
        duty_runtime.PayloadEntryError,
        OSError,
    ) as exc:
        print(MARKER + json.dumps({"status": "BLOCKED", "rule": str(exc)}, ensure_ascii=False))
        return 2
    if args.evidence:
        Path(args.evidence).write_text(
            json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
    print(MARKER + json.dumps(evidence, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
