"""Governed onboarding of a business data space into the current database.

Owner ruling (2026-10-14): platform initialization and industry initialization
are straightened into exactly one order::

    platform_technical_baseline
      -> platform_mechanisms
      -> bootstrap_company_marker
      -> database_strategy_declaration
      -> data_space_onboarding          <- this module
      -> industry_initialization
      -> customer_differentiation

Industry initialization (menus, taxes, dictionaries, project stages, demo
records) must never run before a business company has been onboarded, because
a record created under ``base.main_company`` has no registered owner. Once the
bootstrap company carries business data, no consumer can tell "unknown
ownership" from "platform data", and every scope decision fails open or closed
by accident.

This module owns exactly two questions:

* which database strategy a data purpose must run under, and is that strategy
  declared for the environment role (``strategy_for_purpose`` /
  ``validate_strategy_declaration``);
* is a business data space onboarded in this database before industry or demo
  initialization is allowed to write (``assert_business_data_space_ready``).

The persisted authorization authority stays ``sc.tenant.company.registration``
and the maintenance principal rule stays ``data_space.validate_non_customer_creation``.
This module never creates an alternative permission engine, and it never
implements the customer onboarding lane: a formal customer company is onboarded
only through the signed tenant payload import boundary.

The module deliberately imports nothing from ``odoo`` so that a pure decision
test can load it directly; every ORM access happens through the ``env`` mapping
the caller passes in.
"""

from __future__ import annotations

import json
from pathlib import Path

CUSTOMER_PURPOSE = "customer"
DEMO_PURPOSE = "demo"
TEST_PURPOSE = "test"

#: Purposes the in-database maintenance entry may onboard. A formal customer
#: company is not here on purpose: it requires the signed import lane.
PROVISIONABLE_PURPOSES = (DEMO_PURPOSE, TEST_PURPOSE)
CUSTOMER_ONBOARDING_LANE = "smart_core.tenant_payload_import"

PURPOSE_ENVIRONMENT_ROLE = {
    DEMO_PURPOSE: "platform_internal_demo",
    TEST_PURPOSE: "industry_acceptance",
    CUSTOMER_PURPOSE: "customer_production",
}

#: A formal customer owns one dedicated database; demo and test space use a
#: single business database with company + data-purpose isolation.
PURPOSE_STRATEGY = {
    DEMO_PURPOSE: "single_db_multi_company",
    TEST_PURPOSE: "single_db_multi_company",
    CUSTOMER_PURPOSE: "database_per_customer_tenant",
}

DECLARATION_PATH = "config/tenant/database_strategy.v1.json"
DECLARATION_SCHEMA_VERSION = 1

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def strategy_for_purpose(purpose):
    """Return the declared strategy and environment role a purpose must use."""
    role = PURPOSE_ENVIRONMENT_ROLE.get(purpose)
    strategy = PURPOSE_STRATEGY.get(purpose)
    if role is None or strategy is None:
        raise ValueError("DATA_SPACE_UNKNOWN_DATA_PURPOSE:%s" % (purpose,))
    return {"data_purpose": purpose, "environment_role": role, "strategy": strategy}


def load_declaration(path=None):
    """Read the declared database strategy. Missing or invalid is fail closed."""
    target = Path(path) if path else REPOSITORY_ROOT / DECLARATION_PATH
    if not target.is_file():
        raise ValueError("DATA_SPACE_STRATEGY_DECLARATION_MISSING:%s" % (DECLARATION_PATH,))
    try:
        declaration = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("DATA_SPACE_STRATEGY_DECLARATION_INVALID:%s" % (error,))
    if not isinstance(declaration, dict):
        raise ValueError("DATA_SPACE_STRATEGY_DECLARATION_INVALID:not_an_object")
    return declaration


def validate_strategy_declaration(declaration):
    """Return every reason the declaration cannot authorize a data space."""
    failures = []
    if declaration.get("schema_version") != DECLARATION_SCHEMA_VERSION:
        failures.append("schema_version must be %s" % DECLARATION_SCHEMA_VERSION)
    strategies = declaration.get("strategies") or {}
    roles = declaration.get("environment_roles") or {}
    if not strategies:
        failures.append("strategies must declare at least one strategy")
    if not roles:
        failures.append("environment_roles must declare at least one role")
    for purpose in sorted(PURPOSE_STRATEGY):
        expected = strategy_for_purpose(purpose)
        role = roles.get(expected["environment_role"])
        if not isinstance(role, dict):
            failures.append(
                "data_purpose %s: environment role %s is not declared"
                % (purpose, expected["environment_role"])
            )
            continue
        if role.get("data_purpose") != purpose:
            failures.append(
                "environment role %s: data_purpose must be %s"
                % (expected["environment_role"], purpose)
            )
        if role.get("strategy") != expected["strategy"]:
            failures.append(
                "environment role %s: strategy must be %s for data_purpose %s"
                % (expected["environment_role"], expected["strategy"], purpose)
            )
        if role.get("strategy") not in strategies:
            failures.append(
                "environment role %s: strategy %r is not declared"
                % (expected["environment_role"], role.get("strategy"))
            )
        if role.get("bootstrap_company_carries_business_data") is not False:
            failures.append(
                "environment role %s: the platform bootstrap company must never carry business data"
                % (expected["environment_role"],)
            )
    return failures


def assert_strategy_declared_for_purpose(purpose, declaration=None):
    """Fail closed unless the purpose's strategy is declared for its role."""
    expected = strategy_for_purpose(purpose)
    resolved = declaration if declaration is not None else load_declaration()
    failures = validate_strategy_declaration(resolved)
    if failures:
        raise ValueError("DATA_SPACE_STRATEGY_DECLARATION_INVALID:%s" % ("; ".join(failures),))
    return expected


def _registration_model(env):
    return env["sc.tenant.company.registration"]


def _company_model(env):
    return env["res.company"]


def bootstrap_company_ids(env):
    """Companies that are technical carriers and can never own business data."""
    company = _company_model(env).sudo().search([("is_platform_bootstrap_company", "=", True)])
    return list(company.ids)


def onboarded_registrations(env, purpose=None):
    """Active registrations of real business companies in this database."""
    domain = [
        ("active", "=", True),
        ("company_id.is_platform_bootstrap_company", "=", False),
    ]
    if purpose is not None:
        domain.append(("data_purpose", "=", purpose))
    return _registration_model(env).sudo().search(domain)


def assert_business_data_space_ready(env, purpose=None):
    """Fail closed until a business company is onboarded for this database.

    Industry initialization, demo seeding and any module that writes business
    rows call this first. Writing those rows under the bootstrap company would
    create business data with unknown ownership.
    """
    registrations = onboarded_registrations(env, purpose=purpose)
    if not registrations:
        raise ValueError("DATA_SPACE_ONBOARDING_REQUIRED_BEFORE_INITIALIZATION")
    return registrations


def unregistered_business_companies(env, company_ids):
    """Company ids with no active registration; unknown ownership never passes."""
    candidates = sorted({int(company_id) for company_id in company_ids if company_id})
    if not candidates:
        return []
    registrations = _registration_model(env).sudo().search([
        ("active", "=", True),
        ("company_id", "in", candidates),
    ])
    registered = set(registrations.company_id.ids)
    return [company_id for company_id in candidates if company_id not in registered]


def bootstrap_company_business_data_violations(env, probe_models):
    """Report bootstrap-company rows for the caller-supplied business models.

    The probe list is owned by the industry/ops layer, never by this platform
    module: platform core must not encode construction-industry model names.
    """
    violations = []
    for company_id in bootstrap_company_ids(env):
        for model_name in probe_models:
            model = env[model_name]
            fields = model._fields if hasattr(model, "_fields") else {}
            if "company_id" not in fields:
                continue
            count = model.sudo().search_count([("company_id", "=", company_id)])
            if count:
                violations.append(
                    "bootstrap_company_carries_business_data:%s:%s:%s"
                    % (company_id, model_name, count)
                )
    return violations


def onboard_business_company(env, *, tenant_key, purpose, company_name, declaration=None):
    """Onboard this database's business company for demo/test purposes.

    The strategy is proven declared before any company row is created, and the
    maintenance principal rule stays the one enforced by
    ``data_space.validate_non_customer_creation``. A customer company is
    refused here and must use :data:`CUSTOMER_ONBOARDING_LANE`.
    """
    if purpose == CUSTOMER_PURPOSE:
        raise ValueError("DATA_SPACE_CUSTOMER_ONBOARDING_REQUIRES_SIGNED_IMPORT")
    if purpose not in PROVISIONABLE_PURPOSES:
        raise ValueError("DATA_SPACE_UNKNOWN_DATA_PURPOSE:%s" % (purpose,))
    assert_strategy_declared_for_purpose(purpose, declaration=declaration)
    return _registration_model(env)._create_non_customer_space(
        tenant_key=tenant_key,
        purpose=purpose,
        company_name=company_name,
    )
