"""Product-neutral platform database governance vocabulary and decisions.

Owner ruling (2026-10-14): the database architecture policy and the data-space
onboarding mechanism stay the single declaration source, and their platform
product capability is exactly four responsibilities:

    platform_database_management  database role, tenant ownership, provisioning,
                                  initialization order, upgrade, backup/restore,
                                  suspension/retirement and database audit
    company_data_space            company ownership, customer/demo/test purpose,
                                  company and project access boundary
    business_model                business fact, state transition, approval and
                                  operation permission
    demo                          consumes an onboarded data space and runs the
                                  formal business flow as a formal identity

Two boundaries this module exists to keep true:

* database isolation never replaces record permission -- a dedicated customer
  database still enforces company, role, project and shared-material rules;
* platform database management never grants business data read -- provisioning,
  upgrade and backup capabilities are separated from business record access and
  a special maintenance access needs explicit authorization plus audit.

The module deliberately imports nothing from ``odoo`` so a pure decision test
can load it directly; every ORM access happens in the model layer.
"""

from __future__ import annotations

import json
from pathlib import Path

RESPONSIBILITY_LAYERS = (
    "platform_database_management",
    "company_data_space",
    "business_model",
    "demo",
)

#: Responsibilities a layer may own. A layer that is not listed here may not be
#: claimed by it, which is what keeps "谁负责" from drifting back into prose.
LAYER_RESPONSIBILITIES = {
    "platform_database_management": (
        "database_role",
        "tenant_ownership",
        "provisioning",
        "initialization_order",
        "upgrade",
        "backup_restore",
        "suspension_retirement",
        "database_audit",
    ),
    "company_data_space": (
        "company_ownership",
        "data_purpose",
        "company_scope",
        "project_scope",
        "data_space_registration",
    ),
    "business_model": (
        "business_fact",
        "state_transition",
        "approval",
        "operation_permission",
    ),
    "demo": (),
}

#: Never owned by these layers, whatever else they may claim.
LAYER_FORBIDDEN_RESPONSIBILITIES = {
    "platform_database_management": (
        "business_record_read",
        "business_state_transition",
        "company_project_scope",
    ),
    "company_data_space": ("business_state_transition", "database_lifecycle"),
    "business_model": ("database_lifecycle", "company_ownership"),
    "demo": (
        "database_lifecycle",
        "company_ownership",
        "guard_bypass",
        "terminal_state_write",
    ),
}

DATABASE_LIFECYCLE_STATES = ("declared", "provisioned", "active", "suspended", "retired")
DATABASE_LIFECYCLE_INITIAL_STATE = "declared"
DATABASE_LIFECYCLE_TERMINAL_STATES = ("retired",)
DATABASE_LIFECYCLE_STATE_LABELS = {
    "declared": "已声明",
    "provisioned": "已分配",
    "active": "运行中",
    "suspended": "已暂停",
    "retired": "已退役",
}
DATABASE_DATA_PURPOSE_LABELS = {
    "customer": "客户业务",
    "demo": "演示数据",
    "test": "测试数据",
}
DATABASE_LIFECYCLE_TRANSITIONS = {
    "declared": ("provisioned", "retired"),
    "provisioned": ("active", "retired"),
    "active": ("suspended", "retired"),
    "suspended": ("active", "retired"),
    "retired": (),
}

#: Managed operation entry -> the lifecycle state it must land on. Transition
#: legality is still decided from the current state, so ``activate`` and
#: ``resume`` are two distinct entries onto the same state.
DATABASE_OPERATION_TARGET_STATE = {
    "provision": "provisioned",
    "activate": "active",
    "suspend": "suspended",
    "resume": "active",
    "retire": "retired",
    "abandon": "retired",
}

#: Which lifecycle state each managed entry may be invoked from. ``activate``
#: and ``resume`` land on the same state on purpose: they are two distinct
#: operator intents, so an operator cannot "activate" a suspended database by
#: picking the wrong entry.
DATABASE_OPERATION_SOURCE_STATES = {
    "provision": ("declared",),
    "activate": ("provisioned",),
    "suspend": ("active",),
    "resume": ("suspended",),
    "retire": ("provisioned", "active", "suspended"),
    "abandon": ("declared",),
}

DATABASE_OPERATIONS = tuple(sorted(DATABASE_OPERATION_TARGET_STATE))

MAINTENANCE_ACCESS_CAPABILITIES = ("backup", "restore", "upgrade", "inspect", "migrate")
MAINTENANCE_ACCESS_CAPABILITY_LABELS = {
    "backup": "备份",
    "restore": "恢复",
    "upgrade": "升级",
    "inspect": "巡检",
    "migrate": "迁移",
}
MAINTENANCE_ACCESS_STATE_LABELS = {
    "requested": "待审批",
    "approved": "已批准",
    "rejected": "已拒绝",
    "expired": "已过期",
    "revoked": "已撤销",
}
#: Which maintenance operations a maintenance access may authorize.  These are
#: the operation names the governed duty entries actually execute, so an
#: authorization and its consumer read one vocabulary instead of two: an access
#: that names only one of them cannot cover the other, and approving "the
#: import" can never implicitly authorize creating a service identity.
MAINTENANCE_ACCESS_OPERATIONS = ("provision", "grant")
MAINTENANCE_ACCESS_MAX_VALIDITY_HOURS = 24
#: A maintenance authorization has to cite the authority it rests on, so one
#: ledger row answers "who allowed this, and under which decision" without a
#: second lookup.  The bounds and the refused characters are deliberately the
#: same vocabulary the identity bootstrap's ``--evidence`` argument already
#: uses: both name the same thing, a reference to the owner's decision, and two
#: dialects of it would let one entry accept a reference the other refuses.
MAINTENANCE_ACCESS_EVIDENCE_MIN_LENGTH = 10
MAINTENANCE_ACCESS_EVIDENCE_MAX_LENGTH = 200
MAINTENANCE_ACCESS_EVIDENCE_FORBIDDEN_CHARACTERS = '"`$\\;|<>&()'
#: The boundary anchor: holding an authorized maintenance access never widens
#: the caller's business company scope. Kept as a decision function so the
#: runtime consumer and the fail-closed test read the same single fact.
MAINTENANCE_ACCESS_GRANTS_BUSINESS_DATA_SCOPE = False

DECLARATION_PATH = "data/tenant/database_strategy.v1.json"
DECLARATION_SCHEMA_VERSION = 1
MODULE_ROOT = Path(__file__).resolve().parents[1]


def maintenance_access_grants_business_data_scope():
    """A maintenance access authorizes operations, never business record read."""
    return MAINTENANCE_ACCESS_GRANTS_BUSINESS_DATA_SCOPE


def validate_database_governance_principal(*, uid, superuser_id, su):
    """The governed maintenance principal owns every platform database write."""
    if uid != superuser_id or not su:
        raise PermissionError("DATABASE_GOVERNANCE_MAINTENANCE_PRINCIPAL_REQUIRED")


def validate_lifecycle_state(state):
    if state not in DATABASE_LIFECYCLE_STATES:
        raise ValueError("DATABASE_GOVERNANCE_UNKNOWN_LIFECYCLE_STATE:%s" % (state,))
    return state


def validate_lifecycle_transition(current, target):
    """Fail closed on any transition the declaration does not authorize."""
    validate_lifecycle_state(current)
    validate_lifecycle_state(target)
    allowed = DATABASE_LIFECYCLE_TRANSITIONS[current]
    if target not in allowed:
        raise ValueError(
            "DATABASE_GOVERNANCE_ILLEGAL_TRANSITION:%s->%s" % (current, target)
        )
    return target


def resolve_operation_target_state(current, operation):
    """Resolve one managed entry against the current state, or fail closed."""
    if operation not in DATABASE_OPERATION_TARGET_STATE:
        raise ValueError("DATABASE_GOVERNANCE_UNKNOWN_OPERATION:%s" % (operation,))
    validate_lifecycle_state(current)
    if current not in DATABASE_OPERATION_SOURCE_STATES[operation]:
        raise ValueError(
            "DATABASE_GOVERNANCE_OPERATION_NOT_ALLOWED_FROM_STATE:%s:%s"
            % (operation, current)
        )
    return validate_lifecycle_transition(current, DATABASE_OPERATION_TARGET_STATE[operation])


def validate_maintenance_capability(capability):
    if capability not in MAINTENANCE_ACCESS_CAPABILITIES:
        raise ValueError("DATABASE_GOVERNANCE_UNKNOWN_MAINTENANCE_CAPABILITY:%s" % (capability,))
    return capability


def validate_maintenance_operations(operations):
    """Resolve one declared maintenance operation set, or fail closed.

    A maintenance access authorizes an explicit operation set.  An empty set is
    refused rather than read as "whatever the capability implies": the whole
    point of naming the operations is that a capability like ``migrate`` may no
    longer silently cover both creating a service identity and granting it.
    """
    values = operations if isinstance(operations, (list, tuple)) else None
    if not values:
        raise ValueError("DATABASE_GOVERNANCE_MAINTENANCE_OPERATIONS_REQUIRED")
    resolved = []
    for value in values:
        name = value if isinstance(value, str) else None
        if name not in MAINTENANCE_ACCESS_OPERATIONS:
            raise ValueError("DATABASE_GOVERNANCE_UNKNOWN_MAINTENANCE_OPERATION:%s" % (value,))
        if name not in resolved:
            resolved.append(name)
    return tuple(resolved)


def validate_maintenance_evidence(evidence):
    """Resolve one declared evidence reference, or fail closed.

    The reference is what binds an authorization to the decision it rests on,
    so an authorization that cites nothing is refused instead of recorded with
    an empty field: "no evidence" and "evidence nobody can read" would
    otherwise be the same row, and an approver would be signing off on a claim
    that carries no authority.  The refused characters are the transport
    characters that would break the ssh payload carrying the request, and
    control characters are refused so one reference stays one printable line.
    """
    text = evidence.strip() if isinstance(evidence, str) else ""
    if not text:
        raise ValueError("DATABASE_GOVERNANCE_MAINTENANCE_EVIDENCE_REQUIRED")
    if any(
        character in text
        for character in MAINTENANCE_ACCESS_EVIDENCE_FORBIDDEN_CHARACTERS
    ) or any(character < " " or character == "\x7f" for character in text):
        raise ValueError("DATABASE_GOVERNANCE_MAINTENANCE_EVIDENCE_INVALID_CHARACTERS")
    if not (
        MAINTENANCE_ACCESS_EVIDENCE_MIN_LENGTH
        <= len(text)
        <= MAINTENANCE_ACCESS_EVIDENCE_MAX_LENGTH
    ):
        raise ValueError(
            "DATABASE_GOVERNANCE_MAINTENANCE_EVIDENCE_OUT_OF_RANGE:%s:%s"
            % (
                MAINTENANCE_ACCESS_EVIDENCE_MIN_LENGTH,
                MAINTENANCE_ACCESS_EVIDENCE_MAX_LENGTH,
            )
        )
    return text


def validate_layer_responsibilities(layer, owned):
    """Refuse a responsibility the layer may not hold, in either direction."""
    if layer not in RESPONSIBILITY_LAYERS:
        raise ValueError("DATABASE_GOVERNANCE_UNKNOWN_RESPONSIBILITY_LAYER:%s" % (layer,))
    allowed = set(LAYER_RESPONSIBILITIES[layer])
    forbidden = set(LAYER_FORBIDDEN_RESPONSIBILITIES[layer])
    for name in owned or ():
        if name in forbidden:
            raise ValueError(
                "DATABASE_GOVERNANCE_FORBIDDEN_RESPONSIBILITY:%s:%s" % (layer, name)
            )
        if name not in allowed:
            raise ValueError(
                "DATABASE_GOVERNANCE_UNKNOWN_RESPONSIBILITY:%s:%s" % (layer, name)
            )
    return True


def load_declaration(path=None):
    target = Path(path) if path else MODULE_ROOT / DECLARATION_PATH
    if not target.is_file():
        raise ValueError("DATABASE_GOVERNANCE_DECLARATION_MISSING:%s" % (DECLARATION_PATH,))
    try:
        declaration = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("DATABASE_GOVERNANCE_DECLARATION_INVALID:%s" % (error,))
    if not isinstance(declaration, dict):
        raise ValueError("DATABASE_GOVERNANCE_DECLARATION_INVALID:not_an_object")
    return declaration


def validate_governance_declaration(declaration):
    """Every reason the declaration cannot govern a platform database."""
    failures = []
    if declaration.get("schema_version") != DECLARATION_SCHEMA_VERSION:
        failures.append("schema_version must be %s" % DECLARATION_SCHEMA_VERSION)

    layers = declaration.get("responsibility_layers") or {}
    for layer in RESPONSIBILITY_LAYERS:
        entry = layers.get(layer)
        if not isinstance(entry, dict):
            failures.append("responsibility_layers: %s is not declared" % (layer,))
            continue
        owned = entry.get("owns")
        if not isinstance(owned, list):
            failures.append("responsibility_layers %s: owns must be a list" % (layer,))
            continue
        try:
            validate_layer_responsibilities(layer, owned)
        except ValueError as error:
            failures.append(str(error))
        forbidden = set(entry.get("must_not_own") or ())
        expected = set(LAYER_FORBIDDEN_RESPONSIBILITIES[layer])
        for missing in sorted(expected - forbidden):
            failures.append(
                "responsibility_layers %s: must_not_own must keep %s" % (layer, missing)
            )
        for extra in sorted(forbidden & set(owned)):
            failures.append(
                "responsibility_layers %s: %s cannot be both owned and forbidden" % (layer, extra)
            )

    lifecycle = declaration.get("database_lifecycle") or {}
    if lifecycle.get("initial_state") != DATABASE_LIFECYCLE_INITIAL_STATE:
        failures.append("database_lifecycle: initial_state must be %s" % DATABASE_LIFECYCLE_INITIAL_STATE)
    if tuple(lifecycle.get("terminal_states") or ()) != DATABASE_LIFECYCLE_TERMINAL_STATES:
        failures.append(
            "database_lifecycle: terminal_states must be %s" % (list(DATABASE_LIFECYCLE_TERMINAL_STATES),)
        )
    if tuple(lifecycle.get("states") or ()) != DATABASE_LIFECYCLE_STATES:
        failures.append("database_lifecycle: states must be %s" % (list(DATABASE_LIFECYCLE_STATES),))
    transitions = lifecycle.get("transitions") or {}
    for state in DATABASE_LIFECYCLE_STATES:
        declared = tuple(transitions.get(state) or ())
        if declared != DATABASE_LIFECYCLE_TRANSITIONS[state]:
            failures.append(
                "database_lifecycle %s: transitions must be %s"
                % (state, list(DATABASE_LIFECYCLE_TRANSITIONS[state]))
            )
    for state in transitions:
        if state not in DATABASE_LIFECYCLE_STATES:
            failures.append("database_lifecycle: unknown state %s" % (state,))

    for operation, target in DATABASE_OPERATION_TARGET_STATE.items():
        for source in DATABASE_OPERATION_SOURCE_STATES[operation]:
            declared = tuple((declaration.get("database_lifecycle") or {}).get("transitions", {}).get(source) or ())
            if target not in declared:
                failures.append(
                    "database_lifecycle: managed operation %s needs the declared "
                    "transition %s->%s" % (operation, source, target)
                )

    maintenance = declaration.get("maintenance_access") or {}
    if maintenance.get("requires_explicit_grant") is not True:
        failures.append("maintenance_access: requires_explicit_grant must be true")
    if maintenance.get("requires_independent_approver") is not True:
        failures.append("maintenance_access: requires_independent_approver must be true")
    if maintenance.get("requires_audit") is not True:
        failures.append("maintenance_access: requires_audit must be true")
    if maintenance.get("grants_business_data_scope") is not False:
        failures.append("maintenance_access: grants_business_data_scope must be false")
    if maintenance.get("max_validity_hours") != MAINTENANCE_ACCESS_MAX_VALIDITY_HOURS:
        failures.append(
            "maintenance_access: max_validity_hours must be %s" % MAINTENANCE_ACCESS_MAX_VALIDITY_HOURS
        )
    if tuple(maintenance.get("capabilities") or ()) != MAINTENANCE_ACCESS_CAPABILITIES:
        failures.append(
            "maintenance_access: capabilities must be %s" % (list(MAINTENANCE_ACCESS_CAPABILITIES),)
        )
    if tuple(maintenance.get("operations") or ()) != MAINTENANCE_ACCESS_OPERATIONS:
        failures.append(
            "maintenance_access: operations must be %s" % (list(MAINTENANCE_ACCESS_OPERATIONS),)
        )

    invariants = set(declaration.get("invariants") or ())
    for required in (
        "database_isolation_never_replaces_record_permission",
        "platform_database_management_never_grants_business_data_read",
        "maintenance_access_requires_explicit_authorization_and_audit",
    ):
        if required not in invariants:
            failures.append("invariants: missing required invariant %s" % (required,))
    return failures


def assert_governance_declared(declaration=None):
    resolved = declaration if declaration is not None else load_declaration()
    failures = validate_governance_declaration(resolved)
    if failures:
        raise ValueError("DATABASE_GOVERNANCE_DECLARATION_INVALID:%s" % ("; ".join(failures),))
    return resolved
