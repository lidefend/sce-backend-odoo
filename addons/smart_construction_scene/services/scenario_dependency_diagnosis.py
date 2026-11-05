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


_COMPOSITION_KEYS = ("zone_blocks", "zones", "blocks", "tiles", "related_scenes", "action_specs", "next_scene", "data_sources", "role_variants")


def _has_composition(payload):
    if not isinstance(payload, dict):
        return False
    page = payload.get("page") if isinstance(payload.get("page"), dict) else {}
    return any(row.get(key) for row in (payload, page) for key in _COMPOSITION_KEYS)


def _declares_native_delivery(entry, effective, provider):
    """Positive native evidence only; compatibility actions never erase composition."""
    target = entry.get("target") or {}
    if not target.get("action_xmlid") or target.get("intent") or not effective:
        return False
    if _has_composition(effective) or _has_composition(provider):
        return False
    effective_target = effective.get("target") or {}
    if effective_target.get("intent") or effective_target.get("entry_intent"):
        return False
    if any(effective_target.get(key) and effective_target[key] != target.get(key)
           for key in ("action_xmlid", "menu_xmlid")):
        return False
    if effective.get("source") == "native_fact_projection":
        return (effective_target.get("action_xmlid") == target["action_xmlid"]
                and effective_target.get("menu_xmlid") == target.get("menu_xmlid"))
    handoff = provider.get("delivery_handoff") or {}
    fallback = provider.get("fallback_strategy") or {}
    primary = provider.get("primary_action") or {}
    handoff_primary = handoff.get("primary_action") or {}
    return (handoff.get("consume_mode") == "direct"
            and handoff.get("final_scene") == entry.get("code")
            and primary.get("action_xmlid") == target["action_xmlid"]
            and handoff_primary.get("action_xmlid") == target["action_xmlid"]
            and fallback.get("type") == "native_menu_action_compat"
            and fallback.get("action_xmlid") == target["action_xmlid"]
            and fallback.get("menu_xmlid") == target.get("menu_xmlid"))


def _is_native_entry(env, entry):
    from odoo.addons.smart_core.core.scene_provider import (
        load_scenes_from_db_or_fallback, _resolve_scene_provider_payload,
    )
    key = entry.get("code")
    # Publication is not principal-specific: a hidden tile must not erase the
    # composition's own release requirement from a user-filtered projection.
    scene = env["sc.scene"].sudo().search([("code", "=", key)], limit=1)
    if scene and scene.state == "published" and scene.active_version_id:
        if _has_composition(scene.active_version_id.payload_json):
            return False
    scenes = load_scenes_from_db_or_fallback(env).get("scenes") or []
    effective = next((row for row in scenes if row.get("code") == key), {})
    provider = _resolve_scene_provider_payload(key)
    return _declares_native_delivery(entry, effective, provider)


def diagnose_scenario_dependencies(env, *, scene_key: str, company_id: int) -> dict[str, Any]:
    from odoo.addons.smart_construction_scene.profiles.scene_registry_content import list_scene_entries
    from odoo.addons.smart_construction_scene.services.business_scene_enablement import BUSINESS_PREFIX

    entries = list_scene_entries()
    product_released = resolve_product_released(scene_key, env=env, entries=entries)
    entry = next((row for row in entries if row.get("code") == scene_key), {})
    target = entry.get("target") or {}
    scene = False
    scene_published = None
    composition_version = False
    composition_released = None
    if scene_key.startswith(BUSINESS_PREFIX):
        # The business catalog already checks the maintained scenario's active
        # state and released members. It does not require a second sc.scene.
        readiness_kind = "business_scenario"
        source = "product_menu_source + sc.product.scenario + sc.product.scenario.entry"
        structure_ready = product_released
    elif target.get("action_xmlid") and not target.get("intent") and _is_native_entry(env, entry):
        # A declared native action is a page entry, not an orchestration version.
        # Its existence never substitutes for menu publication or user access.
        readiness_kind = "native_action"
        source = "product_menu_source + ir.actions.act_window + ir.ui.menu"
        action = env.ref(target["action_xmlid"], raise_if_not_found=False)
        menu = env.ref(target.get("menu_xmlid"), raise_if_not_found=False) if target.get("menu_xmlid") else False
        structure_ready = bool(action and action._name == "ir.actions.act_window"
                               and menu and menu._name == "ir.ui.menu"
                               and menu.action == action)
    else:
        readiness_kind = "orchestration"
        source = "product_menu_source + sc.scene + sc.scene.version"
        scene = env["sc.scene"].sudo().search([("code", "=", scene_key)], limit=1)
        composition_version = scene.active_version_id if scene else False
        scene_published = bool(scene and scene.state == "published" and composition_version
                               and composition_version.scene_id == scene)
        composition_released = bool(scene_published and
                                    composition_version.product_release_state == "STANDARD_RELEASE"
                                    and composition_version.product_edition == "construction.standard")
        structure_ready = composition_released
    product_ready = product_released and structure_ready
    publication = {
        "native_capability": {
            "entry_qualified": product_released,
            "authority": "product_menu_source",
            "coverage": "business_scenario_released_members" if readiness_kind == "business_scenario" else "entry_menu_only",
        },
        "scene_composition": {
            "applicable": readiness_kind == "orchestration",
            "snapshot_published": scene_published,
            "standard_released": composition_released,
            "active_version_id": composition_version.id if composition_version else None,
            "release_state": composition_version.product_release_state if composition_version else None,
            "edition": composition_version.product_edition if composition_version else None,
            "authority": "sc.scene + sc.scene.version" if readiness_kind == "orchestration" else None,
        },
    }
    company = env["res.company"].browse(company_id).exists()

    dependencies = [
        _dep(
            dependency_type="PRODUCT_DEPENDENCY",
            applicability=True,
            status="VERIFIED" if product_ready else "NOT_CONFIGURED",
            blocking=not product_ready,
            authoritative_source=source,
            evidence={
                "scene_id": scene.id if scene else 0,
                "state": scene.state if scene else "",
                "product_released": product_released,
                "scene_published": scene_published,
                "readiness_kind": readiness_kind,
                "structure_ready": structure_ready,
            },
            failure_reason=(
                "" if product_ready
                else "产品能力未获标准版发布资格" if not product_released
                else "原生入口的菜单与动作绑定无效" if readiness_kind == "native_action"
                else "场景组合尚未发布标准版产品版本"
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
        "publication": publication,
        "blocking_dependencies": [d.get("dependency_type") for d in blocking],
        "dependencies": dependencies,
        "checked_at": env.cr.now(),
    }
