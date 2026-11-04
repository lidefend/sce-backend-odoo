#!/usr/bin/env python3
"""CAP-02C-04 D4: module change impact report.

Organizes D1/D2 (technical change) and D3 (impact propagation) results into a
management/executor-facing report. No new propagation logic here: this module
only classifies risk and lays out evidence paths. Risk is an impact-analysis
result, never a maturity qualification.
"""
from __future__ import annotations

import json
from typing import Any

from scripts.verify import capability_impact_propagation as d3

REPORT_SCHEMA = "module.change.impact.report.v1"
_RISK_ORDER = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}


def classify_risk(propagation: dict) -> str:
    """Overall risk: Unresolved wins, else the max per-capability band."""
    if propagation.get("has_unresolved_impact"):
        return "Unresolved"
    capabilities = propagation.get("impacted_capabilities", [])
    if not capabilities:
        return "Low"
    ranks: list[str] = []
    for cap in capabilities:
        providers = cap.get("providers", [])
        if any(not p.get("provider_refs") for p in providers):
            ranks.append("Critical")
        elif not cap.get("contract"):
            ranks.append("High")
        elif cap.get("product_scenes"):
            ranks.append("Medium")
        else:
            ranks.append("Low")
    return max(ranks, key=lambda r: _RISK_ORDER[r])


def _unique(items: list[Any]) -> list[Any]:
    seen: set[str] = set()
    out: list[Any] = []
    for item in items:
        key = json.dumps(item, sort_keys=True, ensure_ascii=False, default=str)
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def build_report(module_summary: dict, technical_changes: list[dict],
                 propagation: dict) -> dict:
    """Build the five-section impact report."""
    added = [c for c in technical_changes if c.get("change") == "added"]
    removed = [c for c in technical_changes if c.get("change") == "removed"]
    changed = [c for c in technical_changes if c.get("change") == "changed"]
    content_unresolved = [c for c in technical_changes
                          if c.get("semantics", {}).get("content_unresolved")]
    impacted_caps = propagation.get("impacted_capabilities", [])
    impacted_contracts = propagation.get("impacted_contracts", [])
    impacted_scenes = propagation.get("impacted_product_scenes", [])
    unresolved = propagation.get("unresolved", [])
    providers = _unique([
        {"module": p["module"], "provider_refs": p.get("provider_refs", [])}
        for cap in impacted_caps for p in cap.get("providers", [])
    ])

    confirmed_capabilities = [c for c in impacted_caps if c.get("contract") and c.get("scenes")]
    unresolved_capabilities = [c for c in impacted_caps
                               if not (c.get("contract") and c.get("scenes"))]
    confirmed_contracts = impacted_contracts
    unresolved_contracts = [u for u in unresolved if u.get("reason") == "contract_missing"]
    confirmed_scenes = impacted_scenes
    unresolved_scenes = [u for u in unresolved if u.get("reason") == "scene_missing"]
    association_coverage = propagation.get("association_coverage", {})
    risk = classify_risk(propagation)
    if any(c.get("semantics", {}).get("content_unresolved") for c in technical_changes):
        risk = "Unresolved"

    recommendations: list[str] = []
    if impacted_caps:
        recommendations.append(f"对 {len(impacted_caps)} 项受影响能力执行定向检查")
    if impacted_contracts:
        recommendations.append(f"对 {len(impacted_contracts)} 项验收契约执行定向复核")
    if impacted_scenes:
        recommendations.append(f"关注 {len(impacted_scenes)} 个产品场景")
    if propagation.get("has_unresolved_impact"):
        recommendations.append("补齐未验证关联证据后重新评估")
    if not impacted_caps and not propagation.get("has_unresolved_impact"):
        recommendations.append("保留无关能力现有资格，无业务影响")
    recommendations.append("不修改能力资格与产品发布状态")

    return {
        "schema": REPORT_SCHEMA,
        "module_summary": module_summary,
        "technical_assets": {
            "added": added,
            "removed": removed,
            "changed": changed,
            "source_only_change": not technical_changes,
            "content_unresolved": content_unresolved,
        },
        "business_impact": {
            "providers": providers,
            "capabilities": impacted_caps,
            "contracts": impacted_contracts,
            "scenes": impacted_scenes,
            "product_entries": impacted_scenes,
        },
        "impact_summary": {
            "confirmed_capabilities": confirmed_capabilities,
            "unresolved_capabilities": unresolved_capabilities,
            "confirmed_contracts": confirmed_contracts,
            "unresolved_contracts": unresolved_contracts,
            "confirmed_scenes": confirmed_scenes,
            "unresolved_scenes": unresolved_scenes,
            "association_coverage": association_coverage,
        },
        "risk": risk,
        "recommendations": recommendations,
        "unresolved": unresolved,
    }


def sample_assets(module_key: str) -> list[dict]:
    """Representative changed assets for the three CAP-02C sample modules."""
    if module_key == "smart_construction_core":
        return [{"fact_identity": "field:project.boq.version:name", "asset_type": "field",
                 "asset_modules": ["smart_construction_core"], "model_owner": "project",
                 "model_extensions": ["smart_construction_core"], "change": "changed"}]
    if module_key == "base_tier_validation":
        return [{"fact_identity": "mechanism:tier.validation", "asset_type": "mechanism",
                 "asset_modules": ["base_tier_validation"], "model_owner": "",
                 "model_extensions": [], "change": "changed"}]
    if module_key == "project":
        return [{"fact_identity": "model:project.project", "asset_type": "model",
                 "asset_modules": [], "model_owner": "project",
                 "model_extensions": ["smart_construction_core"], "change": "changed"}]
    raise ValueError(f"unknown sample module: {module_key}")


def sample_report(module_key: str, source: str, change_type: str,
                  runtime_snapshot: dict | None = None) -> dict:
    """Produce a real-data impact report for one sample module."""
    context = d3.build_context(runtime_snapshot=runtime_snapshot)
    assets = sample_assets(module_key)
    propagation = d3.propagate(assets, **context)
    return build_report(
        {"module": module_key, "source": source, "change_type": change_type,
         "fact_source": "runtime_registry"},
        assets,
        propagation,
    )


def main() -> int:
    samples = [
        ("smart_construction_core", "sce", "field_change"),
        ("base_tier_validation", "oca", "mechanism_change"),
        ("project", "odoo_native", "extension_change"),
    ]
    for module, source, change_type in samples:
        print(json.dumps(sample_report(module, source, change_type),
                         ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
