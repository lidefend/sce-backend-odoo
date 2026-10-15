#!/usr/bin/env python3
"""Run the declared payload-import operator lifecycle on a daily duty.

Owner ruling (2026-10-15): the *unified onboarding mechanism* owns the import
operator's account lifecycle and the customer module must not create platform
operators.  The platform product therefore owns the mechanism (the account
lifecycle service in ``smart_core``), the duty declaration carries the tenant
difference, and this ops entry only *executes* and *reads back*: it presents
the declared facts to the duty's own definition, in the duty's own rendered
stack, as the duty's own application user.

Every runtime fact (database, role, container, volumes, compose project,
stack, environment) is resolved from
``config/ops/daily_runtime_database_duties.v1.json``; the operator contract --
including *which* identity is authorised, which company it serves and which
narrow group it may hold -- is resolved from the duty's own ``payload_operator``
declaration and validated by the platform's own policy module, so this entry
cannot drift from the mechanism it drives.

Four properties are deliberate and must not be "corrected" to make a check
pass:

* this entry carries no operator identity of its own.  Binding a generic
  administrator by default would put the narrow grant on the widest account in
  the database, so an undeclared or unusable identity is a stop, never a
  fallback;
* the approval is read from the platform control duty as a fact, never taken
  from a command-line string and never inferred from the declaration: the
  declaration is written by the side that benefits from it.  No approved,
  in-window maintenance access means no provision and no grant;
* the approval must be bound to the exact subject this run will import, so an
  approval for another payload cannot authorise this one;
* revocation is its own action: the temporary permission is removed when the
  import is done, and the account, its external id and the audit association
  stay behind.

``readback`` runs as a separate process and proves it wrote nothing.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
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
APPROVAL_MARKER = "DAILY_DUTY_OPERATOR_APPROVAL="
LIFECYCLE_MARKER = "DAILY_DUTY_OPERATOR_LIFECYCLE="

ACTIONS = ("readback", "provision", "grant", "revoke")
CONFIRMATIONS = {
    "provision": (
        "CONFIRM_DAILY_DUTY_OPERATOR_PROVISION",
        "PROVISION_DECLARED_PAYLOAD_IMPORT_OPERATOR_IN_DAILY_DUTY",
    ),
    "grant": (
        "CONFIRM_DAILY_DUTY_OPERATOR_GRANT",
        "GRANT_NARROW_PAYLOAD_IMPORT_OPERATOR_IN_DAILY_DUTY",
    ),
    "revoke": (
        "CONFIRM_DAILY_DUTY_OPERATOR_REVOKE",
        "REVOKE_TEMPORARY_DAILY_DUTY_IMPORT_OPERATOR_GRANT",
    ),
}
#: The actions that move a permission and therefore need an approved access.
APPROVAL_REQUIRED_ACTIONS = ("provision", "grant")
CUSTOMER_PURPOSE = "customer"
OPERATOR_CARRIER = "unified_onboarding_service_identity"
PLATFORM_CONTROL_DUTY = "platform_control"
GRANT_SCOPE_VERSION = 3
POLICY_SOURCE = "addons/smart_core/security/tenant_payload_operator_policy.py"
SAFE_DUTY_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
XMLID = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")
MODULE_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
CHECKSUM = re.compile(r"^[0-9a-f]{64}$")

IMPORTER_GROUP = "smart_core.group_smart_core_tenant_payload_importer"
DATA_OPERATOR_GROUP = "smart_core.group_smart_core_data_operator"
INTERNAL_USER_GROUP = "base.group_user"

APPLICATION_ENTRY = duty_runtime.APPLICATION_ENTRY
ODOO_CONF = duty_runtime.ODOO_CONF

_POLICY = None

# The readback reuses the platform's own reading of the operator instead of
# re-deriving the same facts here, and only adds the duty-level facts the grant
# depends on: the tenant binding, the released edition and the import history.
READBACK_SCRIPT = """
import json

from odoo.addons.smart_core.security import tenant_payload_operator as _lifecycle  # noqa: F821

_params = env["ir.config_parameter"].sudo()  # noqa: F821
_batch = env["sc.tenant.payload.import.batch"].sudo()  # noqa: F821
_snapshot = env["sc.edition.release.snapshot"].sudo()  # noqa: F821

_identity_key = "__DAILY_DUTY_OPERATOR_IDENTITY_KEY__"
_report = _lifecycle.read_operator(env, identity_xmlid=_identity_key)  # noqa: F821
_report["bound_tenant_key"] = str(_params.get_param("sc.tenant.bound_tenant_key", "") or "")
_report["released_editions"] = _snapshot.search_read(
    [("state", "=", "released"), ("is_active", "=", True), ("active", "=", True)],
    ["product_key", "version"],
    order="product_key, id",
)
_report["import_batch_count"] = _batch.search_count([])
print("%(marker)s" + json.dumps(_report, ensure_ascii=False, sort_keys=True, default=str))
""" % {"marker": READBACK_MARKER}

# The approval is read where the platform is the authority over the fact: the
# platform control database. This script only reads.
APPROVAL_SCRIPT = """
import json

_access = env["sc.platform.maintenance.access"].sudo()  # noqa: F821
_projection = _access._approved_access_projection(
    db_name="__DAILY_DUTY_DATABASE__", capability="__DAILY_DUTY_CAPABILITY__"
)
print("%(marker)s" + json.dumps(
    {"mode": "read_only", "writes": 0, "approval": _projection},
    ensure_ascii=False,
    sort_keys=True,
    default=str,
))
""" % {"marker": APPROVAL_MARKER}

# One entry for the three lifecycle writes. The decisions live in the platform
# mechanism; this script only presents the declared facts and the read approval.
LIFECYCLE_SCRIPT = """
import json
import os

from odoo.addons.smart_core.security import tenant_payload_operator as _lifecycle  # noqa: F821

_action = os.environ["SC_TENANT_PAYLOAD_OPERATOR_ACTION"]
_identity_key = "__DAILY_DUTY_OPERATOR_IDENTITY_KEY__"
if _action == "provision":
    _result = _lifecycle.provision(  # noqa: F821
        env,
        declaration=json.loads(os.environ["SC_TENANT_PAYLOAD_OPERATOR_DECLARATION"]),
        authorization=json.loads(os.environ["SC_TENANT_PAYLOAD_OPERATOR_AUTHORIZATION"]),
    )
elif _action == "grant":
    _grant = _lifecycle.grant_import_scope(  # noqa: F821
        env,
        identity_xmlid=_identity_key,
        authorization=json.loads(os.environ["SC_TENANT_PAYLOAD_OPERATOR_AUTHORIZATION"]),
    )
    _result = {"before": _grant["before"], "after": _grant["after"]}
elif _action == "revoke":
    _result = _lifecycle.revoke_import_scope(env, identity_xmlid=_identity_key)  # noqa: F821
else:
    raise SystemExit("SC_TENANT_PAYLOAD_OPERATOR_ACTION is not a lifecycle action")
_report = dict(_result)
# A membership change reports the state before and after; the database it ran
# against is the same fact the readback reports.
_report.setdefault("database", (_report.get("after") or {}).get("database", ""))
_report["schema_version"] = "tenant_payload_operator_lifecycle.v1"
_report["action"] = _action
_report["identity_key"] = _identity_key
env.cr.commit()  # noqa: F821
print("%(marker)s" + json.dumps(_report, ensure_ascii=False, sort_keys=True, default=str))
""" % {"marker": LIFECYCLE_MARKER}

IDENTITY_KEY_TOKEN = "__DAILY_DUTY_OPERATOR_IDENTITY_KEY__"
DATABASE_TOKEN = "__DAILY_DUTY_DATABASE__"
CAPABILITY_TOKEN = "__DAILY_DUTY_CAPABILITY__"


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


def operator_policy(root: Path | None = None):
    """Load the platform's own operator policy; it is the single source.

    The lifecycle rules are owned by ``smart_core``, so this entry validates the
    declaration with that module rather than restating the rules. The source is
    read from this entry's own root, which is the same immutable tree the
    deployment installs.
    """
    global _POLICY
    if _POLICY is not None:
        return _POLICY
    source = (root or ROOT) / POLICY_SOURCE
    if not source.is_file():
        _fail("the immutable platform operator policy is unavailable")
    spec = importlib.util.spec_from_file_location(
        "daily_runtime_duty_operator_policy", source
    )
    if spec is None or spec.loader is None:
        _fail("the immutable platform operator policy cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _POLICY = module
    return module


def resolve_grant_duty(duty_name: str, declaration: Path | None = None) -> dict:
    """Resolve a customer duty and its declared operator contract."""
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
            "duty %s does not declare that its payload operator is carried by the "
            "unified onboarding mechanism" % duty_name
        )
    policy = operator_policy()
    try:
        account = policy.validate_declaration(operator)
    except policy.OperatorPolicyError as exc:
        _fail("duty %s declares an unusable payload operator: %s" % (duty_name, exc))
    identity_type = _text(operator.get("identity_type"))
    identity_key = account["identity_key"]
    if identity_type != "external_xmlid" or not XMLID.fullmatch(identity_key):
        _fail(
            "duty %s does not declare a usable payload operator identity" % duty_name
        )
    if _text(operator.get("tenant_key")) != duty["tenant_key"]:
        _fail("the payload operator declaration names another tenant")
    if not _text(account.get("authorization_basis")):
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
    if list(account["expected_account_groups"]) != [INTERNAL_USER_GROUP]:
        _fail("the declared account group ceiling is not the narrow one")

    duty["payload_operator"] = {
        "carrier": account["carrier"],
        "identity_type": identity_type,
        "identity_key": identity_key,
        "login": account["login"],
        "name": account["name"],
        "company_xmlid": account["company_xmlid"],
        "authorization_basis": account["authorization_basis"],
        "import_capability": account["import_capability"],
        "declaration": account,
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


def subject_checksum(value: str) -> str:
    """The payload digest this run intends to import, as an explicit input."""
    text = _text(value)
    if not CHECKSUM.fullmatch(text):
        _fail(
            "the run must name the payload digest the approval is bound to "
            "(64 lowercase hex characters)"
        )
    return text


def approval_script(duty: dict, capability: str) -> str:
    if DATABASE_TOKEN not in APPROVAL_SCRIPT or CAPABILITY_TOKEN not in APPROVAL_SCRIPT:
        _fail("the approval read template lost its binding placeholders")
    return APPROVAL_SCRIPT.replace(DATABASE_TOKEN, duty["database"]).replace(
        CAPABILITY_TOKEN, capability
    )


def lifecycle_environment(duty: dict, action: str, authorization: dict | None) -> list[str]:
    operator = duty["payload_operator"]
    environment = [
        "-e", "SC_TENANT_PAYLOAD_OPERATOR_ACTION=%s" % action,
        "-e", "SC_TENANT_PAYLOAD_OPERATOR_IDENTITY_KEY=%s" % operator["identity_key"],
        "-e", "SC_TENANT_PAYLOAD_DB_ALLOWLIST=%s" % duty["database"],
    ]
    if action in APPROVAL_REQUIRED_ACTIONS:
        if not isinstance(authorization, dict):
            _fail("the %s action requires an approved maintenance access" % action)
        environment += [
            "-e",
            "SC_TENANT_PAYLOAD_OPERATOR_AUTHORIZATION=%s"
            % json.dumps(authorization, sort_keys=True, separators=(",", ":")),
        ]
    if action == "provision":
        environment += [
            "-e",
            "SC_TENANT_PAYLOAD_OPERATOR_DECLARATION=%s"
            % json.dumps(operator["declaration"], sort_keys=True, separators=(",", ":")),
        ]
    return environment


def lifecycle_command(duty: dict, base: list[str], extra_env: list[str]) -> list[str]:
    """A one-off run of the duty's own definition that performs one lifecycle step."""
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
    return lifecycle_command(duty, base, [])


def readback_script(duty: dict) -> str:
    """Bind the declared operator identity into the read-only reporter."""
    identity_key = duty["payload_operator"]["identity_key"]
    if not XMLID.fullmatch(identity_key):
        _fail("the declared payload operator identity is not usable")
    if IDENTITY_KEY_TOKEN not in READBACK_SCRIPT:
        _fail("the operator readback template lost its identity placeholder")
    return READBACK_SCRIPT.replace(IDENTITY_KEY_TOKEN, identity_key)


def lifecycle_script(duty: dict) -> str:
    identity_key = duty["payload_operator"]["identity_key"]
    if IDENTITY_KEY_TOKEN not in LIFECYCLE_SCRIPT:
        _fail("the operator lifecycle template lost its identity placeholder")
    return LIFECYCLE_SCRIPT.replace(IDENTITY_KEY_TOKEN, identity_key)


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
    return _marked_report(output, READBACK_MARKER, "operator readback")


def approval_report(output: str) -> dict:
    return _marked_report(output, APPROVAL_MARKER, "maintenance approval read")


def lifecycle_report(output: str) -> dict:
    return _marked_report(output, LIFECYCLE_MARKER, "operator lifecycle")


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
    if int(report.get("importer_group_member_count") or 0) < 0:
        _fail("the operator readback reported an impossible membership count")
    operator = report.get("operator")
    if operator is None:
        return
    if not isinstance(operator, dict):
        _fail("the operator readback reported an unusable operator")
    if _text(operator.get("login")) != duty["payload_operator"]["login"]:
        _fail("the operator readback resolved another login")
    if operator.get("active") is not True or bool(operator.get("share")):
        _fail("the declared operator is not an active internal account")
    if operator.get("has_stored_password"):
        _fail("the declared operator holds an interactive credential")
    if operator.get("has_native_api_keys"):
        _fail("the declared operator holds an unmanaged API key")
    if operator.get("is_data_operator"):
        _fail("the declared operator holds the general data operator group")
    groups = set(operator.get("group_xmlids") or ())
    allowed = {INTERNAL_USER_GROUP, IMPORTER_GROUP}
    if groups - allowed:
        _fail("the declared operator holds groups the declaration does not allow")
    if len(operator.get("company_ids") or ()) != duty["payload_operator"]["expected_company_scope"]:
        _fail("the declared operator company scope drifted")


def assert_approval(report: dict, duty: dict, expected_checksum: str, action: str) -> dict:
    """The approval is a read fact, and it must cover exactly this run."""
    if report.get("mode") != "read_only" or int(report.get("writes") or 0) != 0:
        _fail("the approval read did not declare itself read-only")
    approval = report.get("approval")
    if not isinstance(approval, dict) or not approval:
        _fail(
            "the platform control database holds no approved, in-window maintenance "
            "access for this duty: the lifecycle refuses to fabricate one"
        )
    operations = approval.get("authorized_operations")
    if not isinstance(operations, list) or not all(
        isinstance(operation, str) for operation in operations
    ):
        _fail("the maintenance access declares no operation set")
    if action not in [operation for operation in operations if operation]:
        # The capability is not the grant: an access that authorizes creating a
        # service identity must never be read as also authorizing the grant, and
        # the reverse is refused the same way.
        _fail("the maintenance access does not authorize the %s operation" % action)
    if _text(approval.get("db_name")) != duty["database"]:
        _fail("the approved access covers another database")
    if _text(approval.get("tenant_key")) != duty["tenant_key"]:
        _fail("the approved access covers another tenant")
    if _text(approval.get("operator_identity_key")) != duty["payload_operator"]["identity_key"]:
        _fail("the approved access names another operator identity")
    if _text(approval.get("capability")) != duty["payload_operator"]["import_capability"]:
        _fail("the approved access covers another capability")
    if _text(approval.get("state")) != "approved":
        _fail("the maintenance access is not approved")
    if not _text(approval.get("approved_by")):
        _fail("the maintenance access records no approver identity")
    if _text(approval.get("requested_by")) == _text(approval.get("approved_by")):
        # The entry keeps its own copy of the independence rule: the platform
        # policy already refuses a self-approval, and this entry must not rely
        # on that single check to keep an approval it asked for from covering
        # its own run.
        _fail("the maintenance access approver is its own requester")
    if int(approval.get("access_id") or 0) <= 0:
        _fail("the maintenance access has no usable identity")
    bound = _text(approval.get("subject_checksum"))
    if bound != expected_checksum:
        # An approval for another payload must never authorise this one.
        _fail("the approved access is bound to another subject than this run")
    return approval


def assert_lifecycle(report: dict, duty: dict, action: str, before: dict) -> None:
    """The lifecycle step must be the declared one, and only that one."""
    operator = duty["payload_operator"]
    if report.get("action") != action:
        _fail("the operator lifecycle reported another action")
    if _text(report.get("identity_key")) != operator["identity_key"]:
        _fail("the operator lifecycle ran on another identity")
    if report.get("database") != duty["database"]:
        _fail("the operator lifecycle ran against another database")
    state = report.get("operator") if action in ("provision", "revoke") else report.get("after", {}).get("operator")
    state = state or {}
    if not state:
        _fail("the operator lifecycle reported no operator state")
    if _text(state.get("login")) != operator["login"]:
        _fail("the operator lifecycle resolved another login")
    if state.get("active") is not True or bool(state.get("share")):
        _fail("the operator lifecycle left an unusable principal")
    if state.get("has_stored_password") or state.get("has_native_api_keys"):
        _fail("the operator lifecycle left an interactive or unmanaged credential")
    if state.get("is_data_operator"):
        _fail("the operator lifecycle touched the general data operator group")
    if action == "provision":
        if not isinstance(report.get("created"), bool):
            _fail("the operator provisioning did not report whether it created the account")
        if report.get("plan", {}).get("grantable_group_xmlids") != [IMPORTER_GROUP]:
            _fail("the operator provisioning planned a wider grant than declared")
        if state.get("is_importer") and not report.get("created"):
            _fail("the operator provisioning found an unrelated membership")
    if action == "grant":
        if report.get("after", {}).get("changed") not in (True, False):
            _fail("the operator grant did not report whether it changed anything")
        if state.get("is_importer") is not True:
            _fail("the declared operator is not a member of the narrow importer group")
        before_groups = set(
            ((before.get("operator") or {}).get("group_xmlids")) or []
        )
        after_groups = set(state.get("group_xmlids") or [])
        if before_groups - after_groups:
            _fail("the grant removed a group the operator already held")
        added = after_groups - before_groups
        if added != set(operator["expected_effective_group_additions"]):
            _fail("the grant added groups the declaration did not name")
    if action == "revoke":
        if report.get("changed") not in (True, False):
            _fail("the operator revocation did not report whether it changed anything")
        if state.get("is_importer"):
            _fail("the temporary import permission is still held after revocation")
        if not report.get("operator"):
            _fail("the revocation removed the account instead of the permission")


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
    subject: str = "",
    declaration: Path | None = None,
    tool_root: Path | None = None,
) -> dict:
    if action not in ACTIONS:
        _fail("unsupported operator lifecycle action: %s" % action)
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
    # Loading the policy proves the immutable tree carries the mechanism this
    # entry is about to drive.
    operator_policy(root)
    tool_sha = tool_identity(root)

    confirmation = ""
    approved_subject = ""
    if action in CONFIRMATIONS:
        variable, expected = CONFIRMATIONS[action]
        if os.environ.get(variable) != expected:
            _fail("%s must be set to the exact confirmation value" % variable)
        confirmation = expected
    if action in APPROVAL_REQUIRED_ACTIONS:
        approved_subject = subject_checksum(subject)

    before = readback_report(
        run_script(readback_command(duty, base), readback_script(duty), ops_root)
    )
    assert_readback(before, duty)

    approval: dict | None = None
    approval_read: dict = {}
    if action in APPROVAL_REQUIRED_ACTIONS:
        control = duty_identity.resolve(PLATFORM_CONTROL_DUTY, declaration)
        control_ops_root = ops_root
        control_env_path = control_ops_root / ("%s.env" % control["duty"])
        control_values = duty_runtime.read_duty_env(control_env_path, control)
        control_stack = duty_runtime.stack_compose_path(control_ops_root)
        control_base = duty_runtime.compose_base(
            control, control_ops_root, control_env_path, control_stack
        )
        approval_read = approval_report(
            run_script(
                readback_command(control, control_base),
                approval_script(duty, duty["payload_operator"]["import_capability"]),
                control_ops_root,
            )
        )
        approval = assert_approval(approval_read, duty, approved_subject, action)

    entry_report: dict = {}
    if action in ("provision", "grant", "revoke"):
        output = run_script(
            lifecycle_command(
                duty, base, lifecycle_environment(duty, action, approval)
            ),
            lifecycle_script(duty),
            ops_root,
        )
        entry_report = lifecycle_report(output)
        assert_lifecycle(entry_report, duty, action, before)
        after = readback_report(
            run_script(readback_command(duty, base), readback_script(duty), ops_root)
        )
        assert_readback(after, duty)
    else:
        after = readback_report(
            run_script(readback_command(duty, base), readback_script(duty), ops_root)
        )
        assert_readback(after, duty)
        if before != after:
            _fail("the operator readback changed the duty's operator state")

    return {
        "schema_version": "daily_runtime_duty_operator_lifecycle.v1",
        "action": action,
        "duty": duty["duty"],
        "database": duty["database"],
        "database_role": duty["database_role"],
        "environment_id": duty["environment_id"],
        "tenant_key": duty["tenant_key"],
        "data_purpose": duty["data_purpose"],
        "operator_identity_type": duty["payload_operator"]["identity_type"],
        "operator_identity_key": duty["payload_operator"]["identity_key"],
        "operator_login": duty["payload_operator"]["login"],
        "operator_company_xmlid": duty["payload_operator"]["company_xmlid"],
        "authorization_basis": duty["payload_operator"]["authorization_basis"],
        "confirmed": confirmation,
        "approved_subject_checksum": approved_subject,
        "approval_access_id": (approval or {}).get("access_id", 0),
        "approval_approved_by_fingerprint": (
            hashlib.sha256(_text((approval or {}).get("approved_by")).encode("utf-8"))
            .hexdigest()[:12]
            if (approval or {}).get("approved_by")
            else ""
        ),
        "declared_direct_grant_targets": duty["payload_operator"]["direct_grant_targets"],
        "declared_customer_modules": duty["payload_operator"]["customer_modules"],
        "declared_company_scope": duty["payload_operator"]["expected_company_scope"],
        "application": application,
        "stack_compose": str(stack),
        "duty_environment": str(env_path),
        "entry_report": entry_report,
        "operator_state_before": before,
        "operator_state_after": after,
        "tool_sha": tool_sha,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=list(ACTIONS))
    parser.add_argument("--duty", required=True)
    parser.add_argument("--subject-checksum", default="")
    parser.add_argument("--declaration", default="")
    parser.add_argument("--evidence", default="")
    args = parser.parse_args(argv)
    try:
        evidence = execute(
            args.duty,
            action=args.action,
            subject=args.subject_checksum,
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
