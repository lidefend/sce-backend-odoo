#!/usr/bin/env python3
"""Reconcile isolated acceptance tenant scene enablement without broad fixture writes."""

from __future__ import annotations

import json
import os


DATABASE = "sc_frontend_acceptance"
CONFIRM_PHRASE = "RECONCILE_ACCEPTANCE_BUSINESS_SCENES_132"
MODULE = "smart_construction_acceptance_fixture"

LEGACY_BUSINESS_SCENARIOS = (
    "accounting.management",
    "administration.office",
    "analytics.decision",
    "contract.performance",
    "cost.budget",
    "equipment.management",
    "governance.organization",
    "labor.management",
    "material.management",
    "payment.capital",
    "procurement.supplier",
    "project.management",
    "quality.management",
    "receipt.payment.ledger",
    "safety.management",
    "subcontract.management",
    "tax.management",
)


def _truthy(value) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _scenario_key(value) -> str:
    key = str(value or "").strip()
    return key[len("business.v1:"):] if key.startswith("business.v1:") else key


def build_plan(*, company_ids, desired_keys, legacy_keys, rows, released_by_key=None):
    desired = tuple(sorted({_scenario_key(key) for key in desired_keys if _scenario_key(key)}))
    legacy = tuple(sorted({_scenario_key(key) for key in legacy_keys if _scenario_key(key)}))
    errors = []
    warnings = []
    if set(desired) & set(legacy):
        errors.append("desired and legacy scenario keys overlap")
    released_by_key = released_by_key or {}
    for key in desired:
        if released_by_key and released_by_key.get(key) is False:
            errors.append(f"desired scenario is not product-released: {key}")

    by_company = {}
    for row in rows:
        company_id = int(row.get("company_id") or 0)
        key = _scenario_key(row.get("scene_key"))
        if company_id <= 0 or not key:
            errors.append("enablement row has no company/key identity")
            continue
        company_rows = by_company.setdefault(company_id, {})
        if key in company_rows:
            errors.append(f"duplicate enablement row: company={company_id} key={key}")
        company_rows[key] = bool(row.get("enabled"))

    companies = []
    for company_id in sorted({int(value) for value in company_ids}):
        current = by_company.get(company_id, {})
        desired_enabled = [key for key in desired if current.get(key) is True]
        desired_disabled = [key for key in desired if current.get(key) is False]
        missing = [key for key in desired if key not in current]
        legacy_enabled = [key for key in legacy if current.get(key) is True]
        legacy_missing_or_disabled = [key for key in legacy if current.get(key) is not True]
        if legacy_missing_or_disabled:
            errors.append(
                f"company {company_id} is missing enabled legacy keys required for preservation: "
                f"{legacy_missing_or_disabled}"
            )
        other_enabled = sorted(
            key for key, enabled in current.items()
            if enabled and key not in desired and key not in legacy
        )
        if other_enabled:
            errors.append(
                f"company {company_id} has enabled keys outside the authorized scope: {other_enabled}"
            )
        companies.append({
            "company_id": company_id,
            "before_enabled": sorted(key for key, enabled in current.items() if enabled),
            "create_and_enable": missing,
            "enable_existing": desired_disabled,
            "preserved_legacy": legacy_enabled,
            "already_enabled": desired_enabled,
            "other_enabled_outside_scope": other_enabled,
        })
    if len(companies) != 2:
        errors.append(f"expected exactly two fixture companies, got {len(companies)}")
    expected_enabled = (len(desired) + len(legacy)) * len(companies)
    planned_writes = sum(
        len(company["create_and_enable"])
        + len(company["enable_existing"])
        for company in companies
    )
    return {
        "schema": "acceptance.business_scene_enablement_plan.v1",
        "database": DATABASE,
        "desired_keys": list(desired),
        "legacy_keys": list(legacy),
        "companies": companies,
        "expected_enabled_per_company": len(desired) + len(legacy),
        "expected_enabled_total": expected_enabled,
        "planned_writes": planned_writes,
        "errors": errors,
        "warnings": warnings,
        "ok": not errors,
    }


def _guard(apply):
    database = str(env.cr.dbname or "")  # noqa: F821
    if database != DATABASE:
        raise RuntimeError(f"ACCEPTANCE_BUSINESS_SCENES_DATABASE_DENIED:{database}")
    if str(os.environ.get("SC_ENVIRONMENT") or "") != "acceptance":
        raise RuntimeError("ACCEPTANCE_BUSINESS_SCENES_ENVIRONMENT_DENIED")
    if str(os.environ.get("SC_ALLOW_DEMO_DATA") or "") != "1":
        raise RuntimeError("ACCEPTANCE_BUSINESS_SCENES_FIXTURE_FLAG_REQUIRED")
    if str(os.environ.get("SC_ACCEPTANCE_RUNTIME_PROFILE") or "") != "local":
        raise RuntimeError("ACCEPTANCE_BUSINESS_SCENES_PROFILE_DENIED")
    if apply and str(os.environ.get("SC_ACCEPTANCE_BUSINESS_SCENES_CONFIRM") or "") != CONFIRM_PHRASE:
        raise RuntimeError("ACCEPTANCE_BUSINESS_SCENES_CONFIRM_REQUIRED")
    return apply


def _fixture_companies():
    companies = []
    for suffix in ("a", "b"):
        company = env.ref(f"{MODULE}.fe_company_{suffix}", raise_if_not_found=False)  # noqa: F821
        if not company or company._name != "res.company":
            raise RuntimeError(f"missing fixture company {suffix}")
        companies.append(company)
    return companies


def _rows(companies):
    records = env["sc.scene.company.enablement"].sudo().with_context(active_test=False).search([  # noqa: F821
        ("company_id", "in", [company.id for company in companies])
    ])
    return [
        {
            "company_id": record.company_id.id,
            "scene_key": record.scene_key,
            "enabled": bool(record.enabled),
        }
        for record in records
    ]


def _released_map(desired):
    from odoo.addons.smart_construction_scene.services.tenant_scene_activation import (  # noqa: F821
        resolve_product_released,
    )
    return {
        key: bool(resolve_product_released(f"business.v1:{key}", env=env))  # noqa: F821
        for key in desired
    }


def _desired_scenarios():
    from odoo.addons.smart_construction_core.services.scenario_surface_projection import (  # noqa: F821
        load_runtime_surface,
    )
    surface = load_runtime_surface(env)  # noqa: F821
    return tuple(sorted(
        _scenario_key(row.get("key"))
        for row in surface.get("scenarios") or []
        if _scenario_key(row.get("key")) not in LEGACY_BUSINESS_SCENARIOS
    ))


def main():
    from odoo.addons.smart_construction_acceptance_fixture.tools.frontend_productization_fixture import (  # noqa: F821
        _upsert,
    )

    apply = _guard(_truthy(os.environ.get("APPLY")))
    companies = _fixture_companies()
    desired = _desired_scenarios()
    plan = build_plan(
        company_ids=[company.id for company in companies],
        desired_keys=desired,
        legacy_keys=LEGACY_BUSINESS_SCENARIOS,
        rows=_rows(companies),
        released_by_key=_released_map(desired),
    )
    print("ACCEPTANCE_BUSINESS_SCENES_PLAN=" + json.dumps(plan, ensure_ascii=False, sort_keys=True))
    if not plan["ok"]:
        raise RuntimeError("ACCEPTANCE_BUSINESS_SCENES_PLAN_BLOCKED")
    if not apply:
        print("[acceptance.business_scenes.reconcile] DRY-RUN PASS; no writes")
        env.cr.rollback()  # noqa: F821
        return

    Enablement = env["sc.scene.company.enablement"].sudo()  # noqa: F821
    for company in companies:
        for key in desired:
            scene_key = f"business.v1:{key}"
            xmlid = "fe_business_scene_%s_%s" % (company.id, key.replace(".", "_"))
            record = _upsert(
                env,  # noqa: F821
                "sc.scene.company.enablement",
                xmlid,
                [("company_id", "=", company.id), ("scene_key", "=", scene_key)],
                {
                    "company_id": company.id,
                    "scene_key": scene_key,
                    "provenance": MODULE,
                },
            )
            record.set_enabled(True)

    readback = build_plan(
        company_ids=[company.id for company in companies],
        desired_keys=desired,
        legacy_keys=LEGACY_BUSINESS_SCENARIOS,
        rows=_rows(companies),
        released_by_key=_released_map(desired),
    )
    if not readback["ok"]:
        raise RuntimeError("ACCEPTANCE_BUSINESS_SCENES_READBACK_BLOCKED")
    for company in readback["companies"]:
        if len(company["already_enabled"]) != len(desired):
            raise RuntimeError(
                f"ACCEPTANCE_BUSINESS_SCENES_ENABLED_COUNT_MISMATCH:{company['company_id']}"
            )
        if len(company["preserved_legacy"]) != len(LEGACY_BUSINESS_SCENARIOS):
            raise RuntimeError(
                f"ACCEPTANCE_BUSINESS_SCENES_LEGACY_PRESERVATION_MISMATCH:{company['company_id']}"
            )
        if company["create_and_enable"] or company["enable_existing"]:
            raise RuntimeError(
                f"ACCEPTANCE_BUSINESS_SCENES_NOT_CONVERGED:{company['company_id']}"
            )
    env.cr.commit()  # noqa: F821
    print("ACCEPTANCE_BUSINESS_SCENES_READBACK=" + json.dumps(readback, ensure_ascii=False, sort_keys=True))
    print("[acceptance.business_scenes.reconcile] APPLY PASS")


if __name__ == "__main__":
    main()
