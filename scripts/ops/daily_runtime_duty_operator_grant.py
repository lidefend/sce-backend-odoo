#!/usr/bin/env python3
"""Issue the narrow tenant-payload import grant on a declared daily duty.

A signed payload may only enter a customer duty through an operator that the
product itself recognises: the importer group exists in ``smart_core`` and the
governed entry that grants it (``scripts/tenant_payload/provision_operator.py``)
already exists and already refuses to widen its own contract.  What the daily
development server lacked was the *transport*: the only invocations of that
entry were the local compose face (which passes the superseded v1 environment)
and the production release set (which reads a locked production release file),
so a daily customer duty could not be issued the grant at all.

This entry is the daily-duty transport.  It resolves every runtime fact
(database, role, container, volumes, compose project, stack, environment) from
``config/ops/daily_runtime_database_duties.v1.json`` through the shared
identity module, and it resolves the operator contract -- including *which*
identity is authorised -- from the duty's own ``payload_operator`` declaration.
Two properties are deliberate and must not be "corrected" to make a check pass:

* this entry carries no operator identity of its own.  Binding a generic
  administrator by default would put the narrow grant on the widest account in
  the database, so an undeclared or unusable identity is a stop, never a
  fallback;
* the approver is an explicit input.  The product records it as an audit
  fingerprint (``approval_fingerprint``), so this entry refuses an empty or
  guessed approver rather than fabricating a formal approval identity; the
  authorisation basis is recorded in the declaration.

The grant is the *only* write this entry performs, and it is issued inside the
duty's own rendered definition by the duty's own application user, so the
process that writes the membership is the process that already owns the data.
``readback`` runs as a separate process and proves it wrote nothing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import daily_runtime_duty_identity as duty_identity  # noqa: E402
import daily_runtime_duty_payload as duty_runtime  # noqa: E402


MARKER = "DAILY_DUTY_OPERATOR_GRANT="
READBACK_MARKER = "DAILY_DUTY_OPERATOR_READBACK="
ACTIONS = ("readback", "grant")
CONFIRMATIONS = {
    "grant": (
        "CONFIRM_DAILY_DUTY_OPERATOR_GRANT",
        "GRANT_NARROW_PAYLOAD_IMPORT_OPERATOR_IN_DAILY_DUTY",
    )
}
CUSTOMER_PURPOSE = "customer"
OPERATOR_CARRIER = "narrow_import_grant"
GRANT_SCOPE_VERSION = 3
SAFE_DUTY_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
XMLID = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")
MODULE_NAME = re.compile(r"^[a-z][a-z0-9_]*$")

IMPORTER_GROUP = "smart_core.group_smart_core_tenant_payload_importer"
DATA_OPERATOR_GROUP = "smart_core.group_smart_core_data_operator"
INTERNAL_USER_GROUP = "base.group_user"

PROVISION_SCRIPT = "scripts/tenant_payload/provision_operator.py"
APPLICATION_ENTRY = duty_runtime.APPLICATION_ENTRY
ODOO_CONF = duty_runtime.ODOO_CONF

# The readback script proves it wrote nothing and reports the facts the grant
# depends on: the operator identity itself, the importer group's implied
# closure, the tenant binding and the released edition the duty serves.
READBACK_SCRIPT = """
import json

_params = env["ir.config_parameter"].sudo()  # noqa: F821
_importer = env.ref("%(importer)s", raise_if_not_found=False)  # noqa: F821
_data_operator = env.ref("%(data_operator)s", raise_if_not_found=False)  # noqa: F821
_batch = env["sc.tenant.payload.import.batch"].sudo()  # noqa: F821
_snapshot = env["sc.edition.release.snapshot"].sudo()  # noqa: F821


def _xmlids(group_ids):
    if not group_ids:
        return []
    rows = env["ir.model.data"].sudo().search(  # noqa: F821
        [("model", "=", "res.groups"), ("res_id", "in", sorted(group_ids))]
    )
    return sorted(row.module + "." + row.name for row in rows)


_identity_key = "__DAILY_DUTY_OPERATOR_IDENTITY_KEY__"
_operator = env.ref(_identity_key, raise_if_not_found=False)  # noqa: F821
_report = {
    "mode": "read_only",
    "writes": 0,
    "database": env.cr.dbname,  # noqa: F821
    "bound_tenant_key": str(_params.get_param("sc.tenant.bound_tenant_key", "") or ""),
    "identity_key": _identity_key,
    "importer_group_id": _importer.id if _importer else 0,
    "importer_group_member_count": len(_importer.users) if _importer else 0,
    "importer_implied_xmlids": _xmlids(_importer.implied_ids.ids) if _importer else [],
    "data_operator_group_id": _data_operator.id if _data_operator else 0,
    "released_editions": _snapshot.search_read(
        [("state", "=", "released"), ("is_active", "=", True), ("active", "=", True)],
        ["product_key", "version"],
        order="product_key, id",
    ),
    "import_batch_count": _batch.search_count([]),
    "operator": None,
}
if _operator:
    _report["operator"] = {
        "id": _operator.id,
        "login": _operator.login,
        "active": bool(_operator.active),
        "company_count": len(_operator.company_ids),
        "company_ids": sorted(_operator.company_ids.ids),
        "group_xmlids": _xmlids(_operator.groups_id.ids),
        "is_importer": bool(_importer and _importer.id in _operator.groups_id.ids),
        "is_data_operator": bool(
            _data_operator and _data_operator.id in _operator.groups_id.ids
        ),
    }
print("%(marker)s" + json.dumps(_report, ensure_ascii=False, sort_keys=True, default=str))
""" % {
    "marker": READBACK_MARKER,
    "importer": IMPORTER_GROUP,
    "data_operator": DATA_OPERATOR_GROUP,
}
IDENTITY_KEY_TOKEN = "__DAILY_DUTY_OPERATOR_IDENTITY_KEY__"


class OperatorGrantEntryError(RuntimeError):
    """A stop: the entry refuses to continue rather than guess a fact."""


def _fail(message: str) -> None:
    raise OperatorGrantEntryError(message)


def _text(value) -> str:
    return str(value or "").strip()


def _xmlid_list(contract: dict, key: str) -> list[str]:
    values = contract.get(key)
    if not isinstance(values, list):
        _fail("the payload operator contract declares no %s list" % key)
    for value in values:
        if not isinstance(value, str) or not XMLID.fullmatch(value):
            _fail("the payload operator contract declares an unusable %s entry" % key)
    if len(values) != len(set(values)):
        _fail("the payload operator contract repeats a %s entry" % key)
    return list(values)


def _modules(operator: dict) -> list[str]:
    values = operator.get("customer_modules")
    if not isinstance(values, list) or not values:
        _fail("the payload operator declaration names no customer modules")
    for value in values:
        if not isinstance(value, str) or not MODULE_NAME.fullmatch(value):
            _fail("the payload operator declaration names an unusable customer module")
    if len(values) != len(set(values)):
        _fail("the payload operator declaration repeats a customer module")
    return list(values)


def resolve_grant_duty(duty_name: str, declaration: Path | None = None) -> dict:
    """Resolve a customer duty and its declared narrow operator contract."""
    if not SAFE_DUTY_NAME.fullmatch(duty_name or ""):
        _fail("duty name is not a safe identifier")
    try:
        duty = duty_identity.resolve(duty_name, declaration)
        declared = (duty_identity.load_duties(declaration) or {}).get(duty_name) or {}
    except duty_identity.DutyIdentityError as exc:
        _fail(str(exc))
    if duty["data_purpose"] != CUSTOMER_PURPOSE:
        _fail(
            "duty %s is declared %s, not customer: only a customer duty may be "
            "issued the payload import grant" % (duty_name, duty["data_purpose"])
        )
    if not duty["tenant_key"]:
        _fail("customer duty %s declares no tenant_key" % duty_name)

    operator = declared.get("payload_operator")
    if not isinstance(operator, dict):
        _fail("duty %s declares no payload_operator block" % duty_name)
    if _text(operator.get("carrier")) != OPERATOR_CARRIER:
        _fail(
            "duty %s does not declare that its payload operator carries the "
            "narrow import grant" % duty_name
        )
    identity_type = _text(operator.get("identity_type"))
    identity_key = _text(operator.get("identity_key"))
    if identity_type != "external_xmlid" or not XMLID.fullmatch(identity_key):
        _fail(
            "duty %s does not declare a usable payload operator identity" % duty_name
        )
    if _text(operator.get("tenant_key")) != duty["tenant_key"]:
        _fail("the payload operator declaration names another tenant")
    if not _text(operator.get("authorization_basis")):
        _fail("the payload operator declaration carries no authorization basis")

    contract = operator.get("contract")
    if not isinstance(contract, dict):
        _fail("the payload operator declaration carries no narrow contract")
    direct = _xmlid_list(contract, "direct_grant_targets")
    closure = _xmlid_list(contract, "transitive_implied_closure")
    required = _xmlid_list(contract, "required_existing_groups")
    expected_direct = _xmlid_list(contract, "expected_direct_grant_additions")
    expected_effective = _xmlid_list(contract, "expected_effective_group_additions")
    expected_undeclared = _xmlid_list(contract, "expected_undeclared_group_additions")
    company_scope = contract.get("expected_company_scope")
    if (
        direct != [IMPORTER_GROUP]
        or expected_direct != direct
        or expected_effective != direct
        or required != [INTERNAL_USER_GROUP]
        or closure
        or expected_undeclared
        or DATA_OPERATOR_GROUP
        in {
            *direct,
            *closure,
            *required,
            *expected_effective,
            *expected_undeclared,
        }
    ):
        _fail(
            "duty %s declares a payload operator contract that is not the narrow "
            "import grant" % duty_name
        )
    if contract.get("grant_scope_version") != GRANT_SCOPE_VERSION:
        _fail("the payload operator contract declares another scope version")
    if not isinstance(company_scope, int) or isinstance(company_scope, bool) or company_scope < 1:
        _fail("the payload operator contract declares no positive company scope")

    duty["payload_operator"] = {
        "identity_type": identity_type,
        "identity_key": identity_key,
        "authorization_basis": _text(operator.get("authorization_basis")),
        "customer_modules": _modules(operator),
        "direct_grant_targets": direct,
        "transitive_implied_closure": closure,
        "required_existing_groups": required,
        "expected_direct_grant_additions": expected_direct,
        "expected_effective_group_additions": expected_effective,
        "expected_undeclared_group_additions": expected_undeclared,
        "grant_scope_version": GRANT_SCOPE_VERSION,
        "expected_company_scope": company_scope,
    }
    return duty


def grant_environment(duty: dict, approved_by: str) -> list[str]:
    """The narrow grant contract, exactly as the product entry requires it."""
    operator = duty["payload_operator"]
    return [
        "-e", "SC_TENANT_PAYLOAD_OPERATOR_IDENTITY_TYPE=%s" % operator["identity_type"],
        "-e", "SC_TENANT_PAYLOAD_OPERATOR_IDENTITY_KEY=%s" % operator["identity_key"],
        "-e", "SC_TENANT_PAYLOAD_TENANT_KEY=%s" % duty["tenant_key"],
        "-e", "SC_PRODUCTION_CUSTOMER_MODULES=%s" % ",".join(operator["customer_modules"]),
        "-e", "SC_TENANT_PAYLOAD_DIRECT_GRANT_TARGETS=%s"
        % json.dumps(operator["direct_grant_targets"], separators=(",", ":")),
        "-e", "SC_TENANT_PAYLOAD_TRANSITIVE_IMPLIED_CLOSURE=%s"
        % json.dumps(operator["transitive_implied_closure"], separators=(",", ":")),
        "-e", "SC_TENANT_PAYLOAD_REQUIRED_EXISTING_GROUPS=%s"
        % json.dumps(operator["required_existing_groups"], separators=(",", ":")),
        "-e", "SC_TENANT_PAYLOAD_EXPECTED_DIRECT_ADDITIONS=%s"
        % json.dumps(operator["expected_direct_grant_additions"], separators=(",", ":")),
        "-e", "SC_TENANT_PAYLOAD_EXPECTED_EFFECTIVE_ADDITIONS=%s"
        % json.dumps(operator["expected_effective_group_additions"], separators=(",", ":")),
        "-e", "SC_TENANT_PAYLOAD_EXPECTED_UNDECLARED_ADDITIONS=%s"
        % json.dumps(operator["expected_undeclared_group_additions"], separators=(",", ":")),
        "-e", "SC_TENANT_PAYLOAD_EXPECTED_COMPANY_SCOPE=%d" % operator["expected_company_scope"],
        "-e", "SC_TENANT_PAYLOAD_GRANT_SCOPE_VERSION=%d" % operator["grant_scope_version"],
        "-e", "SC_TENANT_PAYLOAD_DB_ALLOWLIST=%s" % duty["database"],
        "-e", "SC_TENANT_PAYLOAD_APPROVED_BY=%s" % approved_by,
    ]


def grant_command(duty: dict, base: list[str], extra_env: list[str]) -> list[str]:
    """A one-off run of the duty's own definition that issues the grant."""
    return base + [
        "run", "--rm", "--no-deps", "-T",
        "--label", "sc.daily-duty-operator-grant=true",
        "--label", "sc.daily-duty=%s" % duty["duty"],
        *extra_env,
        "--entrypoint", APPLICATION_ENTRY,
        "odoo", "shell", "-c", ODOO_CONF,
        "-d", duty["database"],
        "--no-http", "--log-level=error",
    ]


def readback_command(duty: dict, base: list[str]) -> list[str]:
    return grant_command(duty, base, [])


def readback_script(duty: dict) -> str:
    """Bind the declared operator identity into the read-only reporter."""
    identity_key = duty["payload_operator"]["identity_key"]
    if not XMLID.fullmatch(identity_key):
        _fail("the declared payload operator identity is not usable")
    if IDENTITY_KEY_TOKEN not in READBACK_SCRIPT:
        _fail("the operator readback template lost its identity placeholder")
    return READBACK_SCRIPT.replace(IDENTITY_KEY_TOKEN, identity_key)


def run_script(command: list[str], script: str, ops_root: Path) -> str:
    """Present one governed entry script to the duty's own definition on stdin."""
    with tempfile.TemporaryDirectory() as workspace:
        stub = Path(workspace) / "operator_entry.py"
        stub.write_text(script, encoding="utf-8")
        try:
            with stub.open("r", encoding="utf-8") as source:
                return duty_runtime.run(command, stdin=source, cwd=str(ops_root))
        except duty_runtime.PayloadEntryError as exc:
            _fail(str(exc))


def readback_report(output: str) -> dict:
    for line in reversed(output.splitlines()):
        row = line.strip()
        if row.startswith(READBACK_MARKER):
            try:
                report = json.loads(row[len(READBACK_MARKER):])
            except json.JSONDecodeError as exc:
                _fail("the operator readback report is not JSON: %s" % exc)
            if isinstance(report, dict):
                return report
            _fail("the operator readback report is not an object")
    _fail("the operator readback emitted no report")


def grant_report(output: str) -> dict:
    found = []
    for line in output.splitlines():
        row = line.strip()
        if not row.startswith("{") or not row.endswith("}"):
            continue
        try:
            parsed = json.loads(row)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and parsed.get("schema_version"):
            found.append(parsed)
    if not found:
        _fail("the governed operator entry emitted no audit report")
    report = found[-1]
    if report.get("status") != "PASS":
        reason = report.get("status_reason") or report.get("rule") or report.get("status")
        _fail("the governed operator entry did not pass: %s" % reason)
    return report


def assert_readback(report: dict, duty: dict) -> None:
    """The readback must describe this duty, and must have written nothing."""
    if report.get("database") != duty["database"]:
        _fail("the operator readback targeted another database")
    if report.get("mode") != "read_only" or int(report.get("writes") or 0) != 0:
        _fail("the operator readback did not declare itself read-only")
    bound = _text(report.get("bound_tenant_key"))
    if bound and duty["tenant_key"] and bound != duty["tenant_key"]:
        _fail(
            "the duty binds another tenant (%s) than %s"
            % (bound, duty["tenant_key"])
        )
    if _text(report.get("identity_key")) != duty["payload_operator"]["identity_key"]:
        _fail("the operator readback resolved another identity")
    if report.get("importer_implied_xmlids"):
        _fail("the narrow importer group has grown an implied closure")
    if int(report.get("importer_group_id") or 0) <= 0:
        _fail("the narrow importer group is not present on this duty")


def assert_grant(report: dict, duty: dict, before: dict, after: dict) -> None:
    """The grant must be the only change, and it must be the declared one."""
    operator = duty["payload_operator"]
    if report.get("database") != duty["database"]:
        _fail("the governed operator entry ran against another database")
    if _text(report.get("operator_identity_type")) != operator["identity_type"]:
        _fail("the governed operator entry reported another operator identity type")
    if _text(report.get("operator_identity_key")) != operator["identity_key"]:
        _fail("the governed operator entry reported another operator identity")
    for report_key, declared_key in (
        ("direct_grant_targets", "direct_grant_targets"),
        ("transitive_implied_closure", "transitive_implied_closure"),
        ("required_existing_groups", "required_existing_groups"),
        ("undeclared_group_additions", "expected_undeclared_group_additions"),
    ):
        if report.get(report_key) != operator[declared_key]:
            _fail("the governed operator entry reported another %s" % report_key)
    changed = report.get("changed")
    effective = report.get("effective_group_additions") or []
    if changed is True:
        if effective != list(operator["expected_effective_group_additions"]):
            _fail("the governed operator entry reported an undeclared effective addition")
    elif changed is False:
        if effective:
            _fail("the governed operator entry reported additions it did not make")
    else:
        _fail("the governed operator entry did not report whether it changed anything")
    if report.get("data_operator_added") is not False:
        _fail("the governed operator entry touched the general data operator group")
    if int(report.get("company_scope_count") or 0) != operator["expected_company_scope"]:
        _fail("the governed operator entry reported another company scope")

    operator_state = after.get("operator") or {}
    if not operator_state:
        _fail("the granted operator identity is missing after the grant")
    if operator_state.get("is_importer") is not True:
        _fail("the declared operator is not a member of the narrow importer group")
    if operator_state.get("is_data_operator") is not False:
        _fail("the declared operator is a member of the general data operator group")
    if operator_state.get("active") is not True:
        _fail("the declared operator identity is not active")
    if int(operator_state.get("company_count") or 0) != operator["expected_company_scope"]:
        _fail("the declared operator company scope drifted")

    before_groups = set((before.get("operator") or {}).get("group_xmlids") or [])
    after_groups = set(operator_state.get("group_xmlids") or [])
    if before_groups - after_groups:
        _fail("the grant removed a group the operator already held")
    added = after_groups - before_groups
    if added != set(operator["expected_effective_group_additions"]):
        _fail("the grant added groups the declaration did not name")
    if DATA_OPERATOR_GROUP in added:
        _fail("the grant added the general data operator group")


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
    approved_by: str = "",
    declaration: Path | None = None,
    tool_root: Path | None = None,
) -> dict:
    if action not in ACTIONS:
        _fail("unsupported operator grant action: %s" % action)
    duty = resolve_grant_duty(duty_name, declaration)
    ops_root = Path(duty_identity.load_declaration(declaration).get("ops_root") or "")
    if not ops_root.is_absolute():
        _fail("the declaration must name an absolute ops root")
    env_path = ops_root / ("%s.env" % duty["duty"])
    values = duty_runtime.read_duty_env(env_path, duty)
    stack = duty_runtime.stack_compose_path(ops_root)
    application = duty_runtime.inspect_odoo_container(duty, values)
    base = duty_runtime.compose_base(duty, ops_root, env_path, stack)

    root = tool_root or ROOT
    provision_script = root / PROVISION_SCRIPT
    if not provision_script.is_file():
        _fail("the immutable tenant payload operator entry is unavailable")
    tool_sha = tool_identity(root)

    approver = ""
    if action == "grant":
        variable, expected = CONFIRMATIONS[action]
        if os.environ.get(variable) != expected:
            _fail("%s must be set to the exact confirmation value" % variable)
        approver = _text(approved_by)
        if not approver:
            _fail(
                "the grant requires the real approving subject that authorises it; "
                "this entry never fabricates an approver"
            )

    before = readback_report(
        run_script(readback_command(duty, base), readback_script(duty), ops_root)
    )
    assert_readback(before, duty)

    entry_report: dict = {}
    if action == "grant":
        output = run_script(
            grant_command(duty, base, grant_environment(duty, approver)),
            provision_script.read_text(encoding="utf-8"),
            ops_root,
        )
        entry_report = grant_report(output)

    after = readback_report(
        run_script(readback_command(duty, base), readback_script(duty), ops_root)
    )
    assert_readback(after, duty)

    if action == "grant":
        assert_grant(entry_report, duty, before, after)
    elif before != after:
        _fail("the operator readback changed the duty's operator state")

    return {
        "schema_version": "daily_runtime_duty_operator_grant.v1",
        "action": action,
        "duty": duty["duty"],
        "database": duty["database"],
        "database_role": duty["database_role"],
        "environment_id": duty["environment_id"],
        "tenant_key": duty["tenant_key"],
        "data_purpose": duty["data_purpose"],
        "operator_identity_type": duty["payload_operator"]["identity_type"],
        "operator_identity_key": duty["payload_operator"]["identity_key"],
        "authorization_basis": duty["payload_operator"]["authorization_basis"],
        "approved_by_fingerprint": (
            hashlib.sha256(approver.encode("utf-8")).hexdigest()[:12] if approver else ""
        ),
        "declared_direct_grant_targets": duty["payload_operator"]["direct_grant_targets"],
        "declared_customer_modules": duty["payload_operator"]["customer_modules"],
        "declared_company_scope": duty["payload_operator"]["expected_company_scope"],
        "application": application,
        "stack_compose": str(stack),
        "duty_environment": str(env_path),
        "provision_entry_sha256": hashlib.sha256(
            provision_script.read_bytes()
        ).hexdigest(),
        "tool_sha": tool_sha,
        "entry_report": entry_report,
        "operator_state_before": before,
        "operator_state_after": after,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=list(ACTIONS))
    parser.add_argument("--duty", required=True)
    parser.add_argument("--approved-by", default="")
    parser.add_argument("--declaration", default="")
    parser.add_argument("--evidence", default="")
    args = parser.parse_args(argv)
    try:
        evidence = execute(
            args.duty,
            action=args.action,
            approved_by=args.approved_by,
            declaration=Path(args.declaration) if args.declaration else None,
        )
    except (
        OperatorGrantEntryError,
        duty_identity.DutyIdentityError,
        duty_runtime.PayloadEntryError,
        OSError,
    ) as exc:
        print(
            MARKER
            + json.dumps({"status": "BLOCKED", "rule": str(exc)}, ensure_ascii=False)
        )
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
