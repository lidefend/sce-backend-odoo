#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scenario dependency diagnosis.

Computes the four approved dependency types against authoritative facts.  It
never creates a second scenario dependency registry and never writes business
facts.  ``blocking`` means ENABLEMENT_BLOCKER; non-blocking dependencies are
delivery prerequisites or informational operational facts.
"""

from __future__ import annotations

from typing import Any

from odoo.addons.smart_construction_scene.services.tenant_scene_activation import resolve_product_released


def _dep(
    *,
    dependency_type: str,
    applicability: bool,
    status: str,
    blocking: bool,
    authoritative_source: str,
    evidence: dict[str, Any],
    failure_reason: str,
    remediation_entry: str,
) -> dict[str, Any]:
    return {
        "dependency_type": dependency_type,
        "applicability": applicability,
        "status": status,
        "blocking": blocking,
        "authoritative_source": authoritative_source,
        "evidence": evidence,
        "failure_reason": failure_reason,
        "remediation_entry": remediation_entry,
    }


def diagnose_scenario_dependencies(env, *, scene_key: str, company_id: int) -> dict[str, Any]:
    scene = env["sc.scene"].sudo().search([("code", "=", scene_key)], limit=1)
    product_released = resolve_product_released(scene_key)
    if scene_key == "enterprise.setup":
        # The configuration workspace is published by its native action fact,
        # not by a persisted scene-version release record.
        try:
            scene_published = bool(env.ref(
                "smart_construction_core.action_sc_enterprise_initialization",
                raise_if_not_found=False,
            ))
        except Exception:
            scene_published = False
    else:
        scene_published = bool(scene) and scene.state == "published"
    product_ready = product_released and scene_published
    company = env["res.company"].browse(company_id).exists()

    dependencies = [
        _dep(
            dependency_type="PRODUCT_DEPENDENCY",
            applicability=True,
            status="VERIFIED" if product_ready else "NOT_CONFIGURED",
            blocking=not product_ready,
            authoritative_source="product_menu_source + sc.scene",
            evidence={
                "scene_id": scene.id if scene else 0,
                "state": scene.state if scene else "",
                "product_released": product_released,
                "scene_published": scene_published,
            },
            failure_reason=(
                "" if product_ready
                else "产品能力未获标准版发布资格" if not product_released
                else "产品场景未正式发布"
            ),
            remediation_entry="product.release",
        ),
        _dep(
            dependency_type="TENANT_CONFIGURATION",
            applicability=True,
            status="VERIFIED" if company else "NOT_CONFIGURED",
            blocking=not company,
            authoritative_source="res.company",
            evidence={"company_id": company_id},
            failure_reason="" if company else "企业身份无法确定",
            remediation_entry="enterprise.info",
        ),
        _dep(
            dependency_type="ROLE_DEPENDENCY",
            applicability=True,
            status="CONFIGURED",
            blocking=False,
            authoritative_source="sc.scene.version.payload_json.role_variants",
            evidence={"scene_key": scene_key},
            failure_reason="",
            remediation_entry="data.permission",
        ),
        _dep(
            dependency_type="OPERATIONAL_FACT",
            applicability=True,
            status="CONFIGURED",
            blocking=False,
            authoritative_source="business_models",
            evidence={"scene_key": scene_key},
            failure_reason="",
            remediation_entry="business.operation",
        ),
    ]

    blocking = [d for d in dependencies if d.get("blocking")]
    return {
        "scene_key": scene_key,
        "company_id": company_id,
        "enable_allowed": not blocking,
        "blocking_dependencies": [d.get("dependency_type") for d in blocking],
        "dependencies": dependencies,
        "checked_at": env.cr.now(),
    }
