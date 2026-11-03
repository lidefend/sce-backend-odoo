# -*- coding: utf-8 -*-
"""Business scenario enablement; legacy entry keys never grant a scenario."""
from __future__ import annotations

from copy import deepcopy

BUSINESS_PREFIX = "business.v1:"
BUSINESS_SCOPE = "business.v1"
AUTHORITY_BUCKETS = ("primary_actions", "role_home_actions", "contextual_actions", "admin_actions", "menu_containers")


def business_key(scene_key):
    return BUSINESS_PREFIX + scene_key


def business_states(stored):
    return {key[len(BUSINESS_PREFIX):]: value is True for key, value in stored.items()
            if key.startswith(BUSINESS_PREFIX)}


def business_catalog(surface, release_states, stored, *, can_manage=False):
    from odoo.addons.smart_construction_core.services.scenario_surface_projection import build_menu_index

    index = build_menu_index(surface)
    enabled = business_states(stored)
    rows = []
    for scene in surface.get("scenarios") or []:
        key = scene["key"].strip()
        menus = [menu for menu, location in index.items() if location["location"] == "scenario" and location["scenario_key"] == key]
        released = [menu for menu in menus if release_states.get(menu) == "released"]
        is_enabled = enabled.get(key, False)
        actions = []
        if can_manage and (is_enabled or released):
            actions.append({"key": "disable" if is_enabled else "enable",
                            "label": "停用" if is_enabled else "启用",
                            "enabled": not is_enabled})
        rows.append({"scene_key": key, "name": scene.get("name") or key,
                     "enablement_scope": BUSINESS_SCOPE, "product_released": bool(released),
                     "tenant_enabled": is_enabled, "released_menu_count": len(released),
                     "status_label": "企业已启用" if is_enabled else "未启用",
                     "release_label": "已发布" if released else "未发布",
                     "actions": actions})
    return rows


def entry_business_enabled(entry, surface_index, enabled):
    menu = (entry.get("target") or {}).get("menu_xmlid")
    location = surface_index.get(menu)
    if not location:
        return False
    if location["location"] != "scenario":
        return True
    return enabled.get(location["scenario_key"]) is True


def filter_business_authority(authority, *, surface_index, enabled, entries, menu_xmlids_by_id,
                              menu_xmlids_by_action=None):
    """Only remove existing authority; never manufacture allowed routes.

    Legacy aliases resolve through their menu binding, never textual key equality.
    Unknown industry entry bindings fail closed; unrelated platform routes retain
    their existing authority. The caller supplies current native menu identities.
    """
    # Native membership is used only to restrict rows already published by P0.
    # A bare action shared by multiple delivery surfaces remains usable through
    # any enabled surface; an explicit menu/legacy route retains its own scope.
    action_menus = menu_xmlids_by_action or {}
    result = deepcopy(authority)
    entry_by_key = {entry["code"]: entry for entry in entries if entry.get("code")}
    denied = result.setdefault("denied_actions", [])
    for bucket in AUTHORITY_BUCKETS:
        kept = []
        for row in result.get(bucket) or []:
            menu = row.get("menu_xmlid") or menu_xmlids_by_id.get(row.get("menu_id"))
            location = surface_index.get(menu)
            legacy = entry_by_key.get(row.get("scene_key"))
            if not location and legacy:
                location = surface_index.get((legacy.get("target") or {}).get("menu_xmlid"))
            allowed = (enabled.get(location["scenario_key"]) is True
                       if location and location["location"] == "scenario"
                       else bool(location) or legacy is None)
            if not location and legacy is None and not menu and not row.get("menu_id"):
                locations = [surface_index[xmlid] for xmlid in action_menus.get(row.get("action_id"), ())
                             if xmlid in surface_index]
                if locations:
                    allowed = any(item["location"] != "scenario"
                                  or enabled.get(item["scenario_key"]) is True for item in locations)
            if allowed:
                kept.append(row)
            else:
                denied.append({**row, "route_kind": "DENIED", "allowed_operation": "none",
                               "reason_code": "BUSINESS_SCENARIO_NOT_ENABLED"})
        result[bucket] = kept
    return result
