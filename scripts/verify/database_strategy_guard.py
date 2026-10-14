#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fail-closed guard for the declarative platform/industry initialization strategy.

Owns one question only: is the database strategy of each environment role
declared, known, and policy-compliant? The database architecture policy stays
authoritative; this guard refuses to let a role run without a strategy, with an
unknown strategy, with the platform bootstrap company carrying business data, or
with industry initialization running before the data space is onboarded.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DECLARATION = "config/tenant/database_strategy.v1.json"

CANONICAL_INITIALIZATION_ORDER = [
    "platform_technical_baseline",
    "platform_mechanisms",
    "bootstrap_company_marker",
    "database_strategy_declaration",
    "data_space_onboarding",
    "industry_initialization",
    "customer_differentiation",
]
CUSTOMER_DATABASE_EXCLUSIVE_STRATEGY = "database_per_customer_tenant"
CUSTOMER_PRODUCTION_ROLE = "customer_production"
REQUIRED_INVARIANTS = {
    "business_data_never_in_platform_bootstrap_company",
    "onboarding_precedes_industry_initialization",
    "one_formal_customer_owns_one_business_database",
    "unregistered_company_ownership_fails_closed",
    "strategy_is_declared_per_environment_role",
}


def check(root: Path = ROOT, declaration_path: str = DECLARATION) -> list[str]:
    failures: list[str] = []
    path = root / declaration_path
    if not path.is_file():
        return [f"{declaration_path}: missing declaration"]
    try:
        declaration = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return [f"{declaration_path}: invalid JSON ({error})"]

    if declaration.get("schema_version") != 1:
        failures.append("schema_version must be 1")

    strategies = declaration.get("strategies") or {}
    if not strategies:
        failures.append("strategies must declare at least one strategy")
    purposes = set(declaration.get("data_purposes") or [])
    if purposes != {"customer", "demo", "test"}:
        failures.append("data_purposes must be exactly customer/demo/test")

    for name, entry in strategies.items():
        if not isinstance(entry, dict):
            failures.append(f"strategy {name}: must be an object")
            continue
        if entry.get("allows_multiple_customers_in_one_business_database") is not False:
            # Sharing one business database between two formal customers is the
            # one boundary the policy never allows, in any strategy.
            failures.append(
                f"strategy {name}: allows_multiple_customers_in_one_business_database must be false"
            )

    invariants = set(declaration.get("invariants") or [])
    for missing in sorted(REQUIRED_INVARIANTS - invariants):
        failures.append(f"invariants: missing required invariant {missing}")

    roles = declaration.get("environment_roles") or {}
    if not roles:
        failures.append("environment_roles must declare at least one role")
    for role, entry in roles.items():
        if not isinstance(entry, dict):
            failures.append(f"role {role}: must be an object")
            continue
        strategy = entry.get("strategy")
        if not strategy:
            failures.append(f"role {role}: strategy is required")
        elif strategy not in strategies:
            failures.append(f"role {role}: unknown strategy {strategy!r}")
        purpose = entry.get("data_purpose")
        if purpose not in purposes:
            failures.append(f"role {role}: data_purpose must be one of {sorted(purposes)}")
        if entry.get("bootstrap_company_carries_business_data") is not False:
            failures.append(
                f"role {role}: the platform bootstrap company must never carry business data"
            )
        if entry.get("onboarded_company_required") is not True:
            failures.append(f"role {role}: an onboarded business company is required")
        order = entry.get("initialization_order")
        if order != CANONICAL_INITIALIZATION_ORDER:
            failures.append(
                f"role {role}: initialization_order must be the canonical order "
                f"{CANONICAL_INITIALIZATION_ORDER}"
            )

    production = roles.get(CUSTOMER_PRODUCTION_ROLE)
    if not isinstance(production, dict):
        failures.append(f"environment_roles: {CUSTOMER_PRODUCTION_ROLE} is required")
    else:
        if production.get("strategy") != CUSTOMER_DATABASE_EXCLUSIVE_STRATEGY:
            failures.append(
                f"{CUSTOMER_PRODUCTION_ROLE}: a formal customer company owns a dedicated "
                f"database, so strategy must be {CUSTOMER_DATABASE_EXCLUSIVE_STRATEGY}"
            )
        if production.get("dedicated_database_per_customer") is not True:
            failures.append(
                f"{CUSTOMER_PRODUCTION_ROLE}: dedicated_database_per_customer must be true"
            )
        if production.get("data_purpose") != "customer":
            failures.append(f"{CUSTOMER_PRODUCTION_ROLE}: data_purpose must be customer")
    return failures


def main() -> int:
    failures = check()
    if failures:
        print("DATABASE_STRATEGY_GUARD=FAIL")
        for failure in failures:
            print(f" - {failure}")
        return 1
    declaration = json.loads((ROOT / DECLARATION).read_text(encoding="utf-8"))
    print("DATABASE_STRATEGY_GUARD=PASS roles=%s strategies=%s"
          % (",".join(sorted(declaration["environment_roles"])),
             ",".join(sorted(declaration["strategies"]))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
