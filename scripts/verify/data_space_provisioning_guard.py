#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fail-closed structure check for business data-space onboarding.

One question only: can this repository onboard a business company before any
industry/demo initialization writes business rows, with the declared database
strategy proven first? The guard reads source and the strategy declaration; it
never touches a database.

Checked invariants:

* ``smart_core.security.data_space_provisioning`` exposes the onboarding entry,
  the fail-closed readiness gate and the strategy resolver;
* a formal customer company cannot be onboarded through the in-database
  maintenance entry; it keeps using the signed tenant payload import lane;
* each declared data purpose resolves to its declared environment role and
  strategy, and the declaration carries no unknown role/purpose;
* the registration authority still refuses the platform bootstrap company
  (registration row) and never relabels an existing company;
* industry initialization is bound to onboarding: a non-platform module
  implements the ``_after_tenant_company_registration`` extension point, so
  industry rows land after the data space exists, not before.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PROVISIONING = REPO_ROOT / "addons" / "smart_core" / "security" / "data_space_provisioning.py"
REGISTRATION_MODEL = REPO_ROOT / "addons" / "smart_core" / "models" / "tenant_payload_import_batch.py"
DECLARATION = REPO_ROOT / "addons" / "smart_core" / "data" / "tenant" / "database_strategy.v1.json"

REQUIRED_ENTRYPOINTS = (
    "onboard_business_company",
    "adopt_business_company",
    "assert_business_data_space_ready",
    "strategy_for_purpose",
    "validate_strategy_declaration",
    "bootstrap_company_business_data_violations",
    "environment_role",
    "declare_environment_role",
    "main_company_onboarding_purpose",
    "onboard_environment_main_company",
    "environment_role_data_purpose",
    "onboard_environment_business_company",
    "enroll_data_space_identities",
    "assert_data_space_identities_enrolled",
    "data_space_operators_pending_enrollment",
    "business_data_company_ids",
    "assert_business_data_ownership_registered",
    "unregistered_business_companies",
)
#: The environment onboarding entry reads the purpose from the declared role and
#: picks the shape from the database's own fact. Both halves must stay wired: a
#: hard-coded purpose would let an operator onboard a customer database, and a
#: missing adoption branch makes a database that already onboarded a business
#: company (an acceptance fixture space, for example) un-onboardable.
ENVIRONMENT_ONBOARDING_TOKENS = (
    "environment_role_data_purpose",
    "DATA_SPACE_ENVIRONMENT_ROLE_HAS_NO_DATA_PURPOSE",
    "DATA_SPACE_ENVIRONMENT_ROLE_PURPOSE_MISMATCH",
    "DATA_SPACE_ENVIRONMENT_MAIN_COMPANY_IS_STILL_A_CARRIER",
    "onboard_environment_main_company",
    "adopt_business_company",
)
INDUSTRY_HOOK_TOKEN = "_after_tenant_company_registration"
PLATFORM_MODULE_PREFIXES = ("addons/smart_core/",)

#: The upgrade-time gate. Onboarding was only proven before *new* writes, so a
#: database whose business rows predate the data-space declaration upgraded
#: silently and then served an empty product. The industry layer owns the probe
#: list; the platform owns the meaning of an unregistered owner. Both halves
#: must stay wired: a gate nobody calls is not a gate.
OWNERSHIP_GATE_ENTRYPOINTS = (
    "addons/smart_construction_core/services/business_data_ownership.py",
)
OWNERSHIP_GATE_CALL_TOKEN = "assert_existing_business_data_ownership"
OWNERSHIP_GATE_FAILURE_TOKEN = "DATA_SPACE_UNREGISTERED_BUSINESS_DATA_OWNER"
OWNERSHIP_PROBE_DECLARATION = (
    "addons/smart_construction_core/data/tenant/scoped_business_models.v1.json"
)

#: Onboarding owns the operator identity realm, not just the registration row.
#: The consumer lane must call the platform entry: a registration whose
#: operators were never enrolled is readable by nobody.
ENROLLMENT_PLATFORM_TOKENS = (
    "DATA_SPACE_IDENTITY_ENROLLMENT_INCOMPLETE",
    "DATA_SPACE_ONBOARDING_REQUIRED_BEFORE_IDENTITY_ENROLLMENT",
)
ENROLLMENT_LANE_TOKENS = (
    "enroll_data_space_identities",
    "assert_data_space_identities_enrolled",
)
ENROLLMENT_CONSUMER_LANES = (
    "demo_addons/smart_construction_demo/hooks.py",
)


def load(relative, name):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / relative)
    assert spec and spec.loader, relative
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _industry_hook_owners():
    owners = []
    for path in sorted((REPO_ROOT / "addons").glob("*/models/**/*.py")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "def %s(" % INDUSTRY_HOOK_TOKEN not in text:
            continue
        relative = path.relative_to(REPO_ROOT).as_posix()
        if relative.startswith(("addons/smart_core/models/",)):
            continue
        owners.append(relative)
    return owners


def _ownership_gate_owners():
    """Industry migrations that refuse a data-carrying upgrade with no owner."""
    owners = []
    for path in sorted((REPO_ROOT / "addons").glob("*/migrations/*/*.py")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if OWNERSHIP_GATE_CALL_TOKEN not in text:
            continue
        relative = path.relative_to(REPO_ROOT).as_posix()
        if relative.startswith(PLATFORM_MODULE_PREFIXES):
            continue
        owners.append(relative)
    return owners


def _ownership_gate_failures(provisioning):
    failures = []
    provisioning_text = PROVISIONING.read_text(encoding="utf-8")
    if OWNERSHIP_GATE_FAILURE_TOKEN not in provisioning_text:
        failures.append(
            "ownership gate: the platform decision lost its fail-closed token %s"
            % OWNERSHIP_GATE_FAILURE_TOKEN
        )
    for relative in OWNERSHIP_GATE_ENTRYPOINTS:
        lane = REPO_ROOT / relative
        if not lane.is_file():
            failures.append("ownership gate: %s is missing" % relative)
            continue
        text = lane.read_text(encoding="utf-8")
        for token in (OWNERSHIP_GATE_CALL_TOKEN, "probe_models"):
            if token not in text:
                failures.append("ownership gate: %s does not expose %s" % (relative, token))
        if "smart_core" not in text:
            failures.append(
                "ownership gate: %s must delegate the decision to the platform entry" % relative
            )
    declaration = REPO_ROOT / OWNERSHIP_PROBE_DECLARATION
    if not declaration.is_file():
        failures.append(
            "ownership gate: %s is missing, so the industry probe list cannot ride "
            "inside the module that the container actually mounts"
            % OWNERSHIP_PROBE_DECLARATION
        )
    else:
        document = json.loads(declaration.read_text(encoding="utf-8"))
        models = document.get("models")
        if not isinstance(models, list) or not models:
            failures.append("ownership gate: the probe declaration declares no model")
        elif document.get("authority") != "scripts/verify/data_scope_declarations.json":
            failures.append(
                "ownership gate: the probe declaration must name the company-ceiling "
                "declaration as its authority"
            )
    owners = _ownership_gate_owners()
    if not owners:
        failures.append(
            "ownership gate: no non-platform migration calls %s, so a database whose "
            "business rows predate the data-space declaration still upgrades silently "
            "into an empty product" % OWNERSHIP_GATE_CALL_TOKEN
        )
    return failures, owners


def check():
    failures = []
    if not PROVISIONING.is_file():
        return ["%s: missing governed onboarding module" % PROVISIONING.relative_to(REPO_ROOT)], []

    provisioning = load("addons/smart_core/security/data_space_provisioning.py", "provisioning_under_test")
    for name in REQUIRED_ENTRYPOINTS:
        if not hasattr(provisioning, name):
            failures.append("provisioning: missing entrypoint %s" % name)

    for purpose in ("demo", "test", "customer"):
        resolved = provisioning.strategy_for_purpose(purpose)
        if resolved["strategy"] != provisioning.PURPOSE_STRATEGY[purpose]:
            failures.append("provisioning: %s strategy mapping is inconsistent" % purpose)
        if resolved["environment_role"] != provisioning.PURPOSE_ENVIRONMENT_ROLE[purpose]:
            failures.append("provisioning: %s environment role mapping is inconsistent" % purpose)
    try:
        provisioning.strategy_for_purpose("unknown")
        failures.append("provisioning: an unknown data purpose must be refused")
    except ValueError:
        pass

    if provisioning.PROVISIONABLE_PURPOSES != ("demo", "test"):
        failures.append("provisioning: only demo/test may onboard through the maintenance entry")
    try:
        provisioning.onboard_business_company(
            {}, tenant_key="guard-probe", purpose="customer", company_name="probe",
        )
        failures.append(
            "provisioning: a customer company must not onboard without the signed import lane"
        )
    except ValueError as error:
        if "SIGNED_IMPORT" not in str(error):
            failures.append(
                "provisioning: customer onboarding refusal must name the signed import lane (%s)"
                % (error,)
            )

    provisioning_text = PROVISIONING.read_text(encoding="utf-8")
    entry_body = provisioning_text.split(
        "def onboard_environment_business_company", 1
    )[-1].split("\ndef ", 1)[0]
    for token in ENVIRONMENT_ONBOARDING_TOKENS:
        if token not in entry_body:
            failures.append(
                "provisioning: environment onboarding entry is missing %s" % (token,)
            )

    class _RoleParameter:
        """Minimal stand-in so the guard can prove the refusal without a database."""

        def __init__(self, role):
            self._role = role

        def sudo(self):
            return self

        def get_param(self, key, default=None):
            return self._role

    try:
        provisioning.onboard_environment_business_company(
            {"ir.config_parameter": _RoleParameter("customer_production")},
            tenant_key="guard-probe-environment",
        )
        failures.append(
            "provisioning: a customer production role must never onboard its environment "
            "main company through the maintenance entry"
        )
    except ValueError as error:
        if "SIGNED_IMPORT" not in str(error):
            failures.append(
                "provisioning: environment onboarding refusal must name the signed import "
                "lane (%s)" % (error,)
            )

    declaration = provisioning.load_declaration()
    declaration_failures = provisioning.validate_strategy_declaration(declaration)
    if declaration_failures:
        failures.append("declaration: %s" % ("; ".join(declaration_failures)))

    purpose = declaration.get("data_purposes") or []
    if sorted(purpose) != ["customer", "demo", "test"]:
        failures.append("declaration: data_purposes must be exactly customer/demo/test")
    for role, entry in sorted((declaration.get("environment_roles") or {}).items()):
        expected = provisioning.strategy_for_purpose(entry.get("data_purpose"))
        if expected["strategy"] != entry.get("strategy"):
            failures.append(
                "declaration: role %s strategy %r contradicts data_purpose %s"
                % (role, entry.get("strategy"), entry.get("data_purpose"))
            )

    registration_text = REGISTRATION_MODEL.read_text(encoding="utf-8")
    for token in (
        "TPV1_PLATFORM_BOOTSTRAP_COMPANY_CANNOT_REGISTER",
        '"is_platform_bootstrap_company": False',
        "validate_non_customer_creation",
        "validate_customer_registration",
    ):
        if token not in registration_text:
            failures.append("registration authority: missing token %s" % token)

    owners = _industry_hook_owners()
    if not owners:
        failures.append(
            "industry initialization: no non-platform module implements %s, so industry rows "
            "cannot be proven to land after onboarding" % INDUSTRY_HOOK_TOKEN
        )
    provisioning_text = PROVISIONING.read_text(encoding="utf-8")
    for token in ENROLLMENT_PLATFORM_TOKENS:
        if token not in provisioning_text:
            failures.append("identity enrollment: platform entry lost fail-closed token %s" % token)
    for relative in ENROLLMENT_CONSUMER_LANES:
        lane = REPO_ROOT / relative
        if not lane.is_file():
            failures.append("identity enrollment: %s is missing" % relative)
            continue
        lane_text = lane.read_text(encoding="utf-8")
        for token in ENROLLMENT_LANE_TOKENS:
            if token not in lane_text:
                failures.append(
                    "identity enrollment: %s does not consume %s, so its onboarded space "
                    "can exist with every operator outside the realm" % (relative, token)
                )
    gate_failures, gate_owners = _ownership_gate_failures(provisioning)
    failures.extend(gate_failures)
    return failures, owners, gate_owners


def main() -> int:
    failures, owners, gate_owners = check()
    if failures:
        print("DATA_SPACE_PROVISIONING_GUARD=FAIL")
        for failure in failures:
            print(" - %s" % failure)
        return 1
    declaration = json.loads(DECLARATION.read_text(encoding="utf-8"))
    print(
        "DATA_SPACE_PROVISIONING_GUARD=PASS roles=%s industry_hooks=%s "
        "ownership_gate=%s invariants=%s"
        % (
            ",".join(sorted(declaration["environment_roles"])),
            ",".join(owners),
            ",".join(gate_owners),
            len(declaration.get("invariants") or []),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
