# -*- coding: utf-8 -*-
"""Pure projection of the enterprise scenario activation catalog.

Combines the product scene registry, product publication state and the
tenant's enablement decisions into the rows the enterprise.setup UI renders.
It never fabricates fields that have no reliable source (description, target
users, dependencies) and never stores USER_ACCESSIBLE: reachability stays a
runtime Navigation Authority + ACL/Record Rules result.
"""
from __future__ import annotations

from typing import Any

from odoo.addons.smart_construction_scene.services.tenant_scene_activation import resolve_entry_release_state, resolve_entry_surface


def build_scenario_activation_catalog(
    *,
    entries: list[dict[str, Any]],
    release_state_by_menu: dict[str, str],
    product_release_by_scene: dict[str, str] | None = None,
    tenant_enablement_by_scene: dict[str, bool] | None = None,
    role_candidates_by_scene: dict[str, list[str]] | None = None,
    surface_index: dict | None = None,
) -> dict[str, Any]:
    """Project menu qualification and scene lifecycle without conflating them.

    ``product_release_by_scene`` contains active scene-version enum values. They
    are reported separately and never override standard menu qualification.
    """
    enabled_map = {str(k): bool(v) for k, v in (tenant_enablement_by_scene or {}).items()}
    roles_map = {str(k): [str(x) for x in (v or [])] for k, v in (role_candidates_by_scene or {}).items()}
    product_release_map = {str(k): str(v or "").strip() for k, v in (product_release_by_scene or {}).items()}
    rows: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        scene_key = str(entry.get("code") or entry.get("key") or "").strip()
        if not scene_key:
            continue
        target = entry.get("target") if isinstance(entry.get("target"), dict) else {}
        menu_xmlid = str(target.get("menu_xmlid") or "").strip()
        release_state = resolve_entry_release_state(entry, release_state_by_menu)
        rows.append(
            {
                "scene_key": scene_key,
                "product_surface": resolve_entry_surface(entry, surface_index),
                "name": str(entry.get("name") or scene_key).strip(),
                "menu_xmlid": menu_xmlid,
                "release_state": release_state or "preview",
                "product_released": release_state == "released",
                "scene_version_release_state": product_release_map.get(scene_key, ""),
                "tenant_enabled": enabled_map.get(scene_key, False),
                "applicable_roles": roles_map.get(scene_key, []),
            }
        )
    return {
        "contract_version": "scenario_activation_catalog.v1",
        "rows": rows,
        "row_count": len(rows),
    }
