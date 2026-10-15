#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fail-closed guard for the platform database governance product capability.

Owns one question only: is the database governance declaration still the single
source, and does the platform capability still implement the two boundaries the
owner named?

* database isolation never replaces record permission;
* platform database management never grants customer business data read, and a
  special maintenance access needs explicit authorization plus audit.

A missing layer, a lifecycle state without a legal entry, a maintenance access
that could grant business scope, or a capability that hardcodes its own role or
purpose vocabulary instead of consuming the declaration all fail here.

The managed lifecycle entry must also keep exactly one production caller: the
governed ops tool under ``scripts/ops/``. A registration row that only the model
tests ever move is a declared fact without an environment fact, which is the
gap this guard closes.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOVERNANCE_MODULE = "addons/smart_core/security/database_governance.py"
PROVISIONING_MODULE = "addons/smart_core/security/data_space_provisioning.py"
REGISTRY_MODEL = "addons/smart_core/models/platform_database_registry.py"
DECLARATION = "addons/smart_core/data/tenant/database_strategy.v1.json"

REQUIRED_MANAGED_ENTRIES = ("_register_database", "_apply_operation")
REQUIRED_MAINTENANCE_ENTRIES = (
    "_request_access",
    "_approve_access",
    "_revoke_access",
    "_assert_access_authorized",
)

#: The governed ops entries are the only production callers of the managed
#: entries: registration resolves role/purpose from the onboarding declaration,
#: and the lifecycle entry turns a declared state into a real environment fact.
MANAGED_ENTRY_CALLERS = {
    "_register_database": "scripts/ops/platform_database_register.py",
    "_apply_operation": "scripts/ops/platform_database_lifecycle_apply.py",
}
OPS_ENTRY_VOCABULARY = {
    "scripts/ops/platform_database_register.py": "odoo.addons.smart_core.security.data_space_provisioning",
    "scripts/ops/platform_database_lifecycle_apply.py": "odoo.addons.smart_core.security.database_governance",
}
REGISTRATION_MODEL_ACCESS = '["sc.platform.database.registration"]'
CALLER_SCAN_ROOTS = ("addons", "demo_addons", "scripts")


def _load(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _is_test_path(path: Path) -> bool:
    return any(part in ("tests", "__pycache__") for part in path.parts) or path.name.startswith(
        "test_"
    )


def _production_callers(root: Path, managed_entry: str) -> list[str]:
    """Every non-test caller of one managed entry, relative to the repository."""
    callers: list[str] = []
    for scan_root in CALLER_SCAN_ROOTS:
        directory = root / scan_root
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*.py")):
            if _is_test_path(path):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if f".{managed_entry}(" in text:
                callers.append(path.relative_to(root).as_posix())
    return callers


def check(root: Path = ROOT) -> list[str]:
    failures: list[str] = []
    governance = _load(GOVERNANCE_MODULE, "governance_under_guard")

    declaration = governance.load_declaration(root / DECLARATION)
    failures.extend(governance.validate_governance_declaration(declaration))

    provisioning = _load(PROVISIONING_MODULE, "provisioning_under_guard")
    # The onboarding declaration stays the single source: the governance layer
    # consumes it instead of restating roles, purposes or strategies.
    for purpose in provisioning.PURPOSE_STRATEGY:
        role = provisioning.PURPOSE_ENVIRONMENT_ROLE[purpose]
        if role not in (declaration.get("environment_roles") or {}):
            failures.append(
                f"environment_roles: {role} is used by onboarding but not declared"
            )

    registry_path = root / REGISTRY_MODEL
    if not registry_path.is_file():
        failures.append(f"{REGISTRY_MODEL}: missing platform database registry model")
        return failures
    source = registry_path.read_text(encoding="utf-8")

    for entry in REQUIRED_MANAGED_ENTRIES + REQUIRED_MAINTENANCE_ENTRIES:
        if f"def {entry}" not in source:
            failures.append(f"{REGISTRY_MODEL}: managed entry {entry} is missing")

    if "resolve_operation_target_state" not in source:
        failures.append(
            f"{REGISTRY_MODEL}: the lifecycle entry must resolve through the declared transitions"
        )
    if "maintenance_access_grants_business_data_scope" not in source:
        failures.append(
            f"{REGISTRY_MODEL}: the maintenance access must read the declared scope fact"
        )
    if "grants_business_data_scope" not in source:
        failures.append(
            f"{REGISTRY_MODEL}: the maintenance access must expose grants_business_data_scope"
        )
    # The capability consumes the declared vocabulary instead of restating it,
    # which is what keeps one declaration source true over time.
    for symbol in (
        "DATABASE_LIFECYCLE_STATES",
        "DATABASE_LIFECYCLE_INITIAL_STATE",
        "MAINTENANCE_ACCESS_CAPABILITIES",
        "MAINTENANCE_ACCESS_MAX_VALIDITY_HOURS",
    ):
        if symbol not in source:
            failures.append(f"{REGISTRY_MODEL}: must consume the declared {symbol} vocabulary")
    if "security.database_governance" not in source:
        failures.append(
            f"{REGISTRY_MODEL}: must import its vocabulary from security.database_governance"
        )

    # The managed entries must be reachable from a governed ops entry, and from
    # nothing else: an ops tool the platform never wired is a declaration with no
    # environment fact, and a second caller would be an unaudited writer.
    for managed_entry, ops_entry in MANAGED_ENTRY_CALLERS.items():
        ops_path = root / ops_entry
        if not ops_path.is_file():
            failures.append(f"{ops_entry}: governed ops entry for {managed_entry} is missing")
            continue
        ops_source = ops_path.read_text(encoding="utf-8")
        if REGISTRATION_MODEL_ACCESS not in ops_source:
            failures.append(f"{ops_entry}: must run through the governed registration model")
        if f".{managed_entry}(" not in ops_source:
            failures.append(f"{ops_entry}: must call the managed entry {managed_entry}")
        vocabulary = OPS_ENTRY_VOCABULARY[ops_entry]
        if f'"{vocabulary}"' not in ops_source:
            failures.append(f"{ops_entry}: must consume the declaration through {vocabulary}")
        if "addons/smart_core/security/" in ops_source:
            failures.append(f"{ops_entry}: must not reach the declaration by filesystem path")
        second_callers = [
            caller
            for caller in _production_callers(root, managed_entry)
            if caller != ops_entry
        ]
        if second_callers:
            failures.append(
                f"managed entry {managed_entry} has a second production caller: {second_callers}"
            )
    # The platform layer must never decide a tenant, a purpose or an
    # initialization rule for itself.
    for forbidden in ("in initialization_order", 'data_purpose = "'):
        if forbidden in source:
            failures.append(
                f"{REGISTRY_MODEL}: the platform layer restates an onboarding rule ({forbidden})"
            )
    return failures


def main() -> int:
    failures = check()
    if failures:
        print("PLATFORM_DATABASE_GOVERNANCE_GUARD=FAIL")
        for failure in failures:
            print(f" - {failure}")
        return 1
    governance = _load(GOVERNANCE_MODULE, "governance_under_guard")
    print(
        "PLATFORM_DATABASE_GOVERNANCE_GUARD=PASS layers=%s states=%s capabilities=%s"
        % (
            len(governance.RESPONSIBILITY_LAYERS),
            len(governance.DATABASE_LIFECYCLE_STATES),
            len(governance.MAINTENANCE_ACCESS_CAPABILITIES),
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
