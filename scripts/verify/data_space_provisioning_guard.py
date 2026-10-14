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
)
INDUSTRY_HOOK_TOKEN = "_after_tenant_company_registration"
PLATFORM_MODULE_PREFIXES = ("addons/smart_core/",)


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
    return failures, owners


def main() -> int:
    failures, owners = check()
    if failures:
        print("DATA_SPACE_PROVISIONING_GUARD=FAIL")
        for failure in failures:
            print(" - %s" % failure)
        return 1
    declaration = json.loads(DECLARATION.read_text(encoding="utf-8"))
    print(
        "DATA_SPACE_PROVISIONING_GUARD=PASS roles=%s industry_hooks=%s invariants=%s"
        % (
            ",".join(sorted(declaration["environment_roles"])),
            ",".join(owners),
            len(declaration.get("invariants") or []),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
