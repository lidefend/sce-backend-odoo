#!/usr/bin/env python3
"""Compare every runtime primary-center surface with delivered domain evidence."""

from __future__ import annotations

import json
import importlib.util
import os
from pathlib import Path


def _load_shared_runtime():
    try:
        from scripts.verify import frontend_project_domain_rollout as runtime
        return runtime
    except ModuleNotFoundError:
        mounted = Path("/mnt/scripts/verify/frontend_project_domain_rollout.py")
        spec = importlib.util.spec_from_file_location(
            "frontend_project_domain_rollout_shared", mounted
        )
        if spec is None or spec.loader is None:
            raise RuntimeError(f"shared domain rollout runtime is unavailable: {mounted}")
        runtime = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runtime)
        return runtime


shared = _load_shared_runtime()


OUTPUT_PATH = Path(
    os.getenv(
        "FRONTEND_SYSTEMWIDE_COVERAGE_AUDIT_PATH",
        "/tmp/frontend_systemwide_coverage_audit_v1.json",
    )
)
REPORT_ROOT = Path("/mnt/docs/frontend_productization/domain-rollout")
OWNER_MODULE = "smart_construction_core"
CENTER_ROOTS = {
    "workbench": "smart_construction_core.menu_sc_workspace_center",
    "project": "smart_construction_core.menu_sc_project_center",
    "contract": "smart_construction_core.menu_sc_contract_center",
    "cost": "smart_construction_core.menu_sc_cost_center",
    "finance": "smart_construction_core.menu_sc_finance_center",
    "tax": "smart_construction_core.menu_sc_tax_center",
    "accounting": "smart_construction_core.menu_sc_accounting_center",
    "reporting": "smart_construction_core.menu_sc_data_center",
    "administration": "smart_construction_core.menu_sc_hr_admin_center",
    "product_configuration": "smart_construction_core.menu_sc_business_config_center",
}
DELIVERED_REPORTS = (
    "project-domain-coverage-v1.json",
    "contract-domain-coverage-v1.json",
    "payment-domain-coverage-v1.json",
    "settlement-domain-coverage-v1.json",
    "cost-domain-coverage-v1.json",
    "material-domain-coverage-v1.json",
    "quality-safety-domain-coverage-v1.json",
    "collaboration-domain-coverage-v1.json",
    "base-configuration-domain-coverage-v1.json",
    "administration-domain-coverage-v1.json",
)


def _formal_identity_status(menu_xmlid: str, action_xmlid: str) -> str:
    if not menu_xmlid or not action_xmlid:
        return "missing"
    prefix = f"{OWNER_MODULE}."
    if not menu_xmlid.startswith(prefix) or not action_xmlid.startswith(prefix):
        return "foreign"
    return "formal"


def _load_evidence(root: Path = REPORT_ROOT) -> tuple[list[dict], set[tuple[str, str]], list[dict]]:
    reports: list[dict] = []
    covered: set[tuple[str, str]] = set()
    gaps: list[dict] = []
    for name in DELIVERED_REPORTS:
        path = root / name
        if not path.is_file():
            gaps.append({"report": name, "reason": "DELIVERED_REPORT_MISSING"})
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        reports.append({
            "file": name,
            "domain": payload.get("domain"),
            "status": payload.get("status"),
            "actionCount": payload.get("summary", {}).get("action_count"),
            "gapCount": payload.get("summary", {}).get("gap_count"),
        })
        if payload.get("status") != "PASS" or payload.get("summary", {}).get("gap_count") != 0:
            gaps.append({"report": name, "reason": "DELIVERED_REPORT_NOT_PASS"})
        for row in payload.get("actions", []):
            covered.add((str(row.get("menuXmlid") or ""), str(row.get("actionXmlid") or "")))
    return reports, covered, gaps


def _runtime_surface(env, center: str, root_xmlid: str) -> tuple[list[dict], list[dict], list[dict]]:
    root = env.ref(root_xmlid)
    Menu = env["ir.ui.menu"].sudo().with_context(active_test=False)
    menu_ids = (root.id, *shared._active_descendant_ids(env, root.id))
    rows: list[dict] = []
    excluded: list[dict] = []
    gaps: list[dict] = []
    for menu in Menu.browse(menu_ids):
        action = menu.action
        if not action or action._name != "ir.actions.act_window":
            continue
        action = env["ir.actions.act_window"].sudo().browse(action.id).exists()
        menu_xmlid = shared._xmlid(menu)
        action_xmlid = shared._xmlid(action)
        identity_status = _formal_identity_status(menu_xmlid, action_xmlid)
        if identity_status == "missing":
            gaps.append({
                "center": center,
                "menuXmlid": menu_xmlid,
                "actionXmlid": action_xmlid,
                "reason": "FORMAL_XMLID_MISSING",
            })
            continue
        if identity_status == "foreign":
            excluded.append({
                "center": center,
                "menuXmlid": menu_xmlid,
                "actionXmlid": action_xmlid,
                "reason": "OUTSIDE_FORMAL_PRODUCT_MODULE",
            })
            continue
        if not action or action.res_model not in env:
            gaps.append({"center": center, "actionXmlid": action_xmlid, "reason": "ACTION_MODEL_NOT_AVAILABLE"})
            continue
        try:
            semantics = shared._assembly_semantics(env, action)
            views = shared._resolved_views(env, action, semantics)
        except Exception as exc:  # pragma: no cover - governed runtime evidence
            views = []
            gaps.append({
                "center": center,
                "actionXmlid": action_xmlid,
                "reason": f"PAGE_ASSEMBLY_FAILED:{type(exc).__name__}:{exc}",
            })
        authority = shared._authority_contract(menu, action)
        rows.append({
            "center": center,
            "rootMenuXmlid": root_xmlid,
            "menuId": menu.id,
            "menuXmlid": menu_xmlid,
            "menuName": shared._text(menu.name),
            "actionId": action.id,
            "actionXmlid": action_xmlid,
            "actionName": shared._text(action.name),
            "actionOwner": action_xmlid.split(".", 1)[0] if "." in action_xmlid else "",
            "model": action.res_model,
            "viewMode": shared._text(action.view_mode),
            "authority": authority,
            "surfaces": views,
        })
        gaps.extend(
            {"center": center, **gap}
            for gap in shared._authority_gaps(action_xmlid, authority)
        )
        if not views:
            gaps.append({"center": center, "actionXmlid": action_xmlid, "reason": "ACTION_VIEW_MODE_MISSING"})
        for view in views:
            if view["readiness"] == "fail_closed":
                gaps.append({"center": center, "actionXmlid": action_xmlid, "reason": shared._text(view["reason"])})
    return rows, excluded, gaps


def collect(env, report_root: Path = REPORT_ROOT) -> dict[str, object]:
    reports, covered, gaps = _load_evidence(report_root)
    centers: list[dict] = []
    all_rows: list[dict] = []
    excluded: list[dict] = []
    for center, root_xmlid in CENTER_ROOTS.items():
        rows, runtime_excluded, runtime_gaps = _runtime_surface(env, center, root_xmlid)
        excluded.extend(runtime_excluded)
        gaps.extend(runtime_gaps)
        for row in rows:
            identity = (str(row["menuXmlid"]), str(row["actionXmlid"]))
            row["coverageStatus"] = "covered" if identity in covered else "uncovered"
        uncovered = [row for row in rows if row["coverageStatus"] == "uncovered"]
        centers.append({
            "center": center,
            "rootMenuXmlid": root_xmlid,
            "surfaceCount": len(rows),
            "coveredCount": len(rows) - len(uncovered),
            "uncoveredCount": len(uncovered),
        })
        all_rows.extend(rows)
    uncovered = [row for row in all_rows if row["coverageStatus"] == "uncovered"]
    gaps.extend({
        "center": row["center"],
        "menuXmlid": row["menuXmlid"],
        "actionXmlid": row["actionXmlid"],
        "reason": "FORMAL_RUNTIME_SURFACE_UNQUALIFIED",
    } for row in uncovered)
    summary = {
        "primaryCenterCount": len(centers),
        "deliveredReportCount": len(reports),
        "runtimeSurfaceCount": len(all_rows),
        "excludedSurfaceCount": len(excluded),
        "coveredSurfaceCount": len(all_rows) - len(uncovered),
        "uncoveredSurfaceCount": len(uncovered),
        "runtimeGapCount": sum(gap.get("reason") != "FORMAL_RUNTIME_SURFACE_UNQUALIFIED" for gap in gaps),
        "gapCount": len(gaps),
    }
    return {
        "schemaVersion": "frontend_systemwide_coverage_audit.v1",
        "status": "PASS" if not gaps and len(centers) == 10 and len(reports) == 10 else "FAIL",
        "database": env.cr.dbname,
        "formalProductLayer": "P0_P1_systemwide_frontend",
        "primaryCenterAuthority": "config/product_primary_center_baseline_v1.json",
        "excludedScopes": ["demo_addons", "external_customer_addons", "internal_system_management"],
        "summary": summary,
        "deliveredReports": reports,
        "centers": centers,
        "surfaces": all_rows,
        "excluded": excluded,
        "gaps": gaps,
    }


if "env" in globals():  # pragma: no branch - Odoo shell execution contract
    payload = collect(env)  # type: ignore[name-defined]  # noqa: F821
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "summary": payload["summary"], "output": str(OUTPUT_PATH)}, ensure_ascii=False))
