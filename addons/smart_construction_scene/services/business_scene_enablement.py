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
        is_enabled = bool(scene.get("active", True)) and enabled.get(key, False)
        if not scene.get("active", True):
            released = []
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


def location_business_enabled(location, enabled):
    if not location or location["location"] == "missing":
        return False
    if location["location"] == "scenario":
        return location.get("scenario_active", True) and enabled.get(location["scenario_key"]) is True
    return location["location"] in ("exempt", "horizontal", "platform")


def entry_business_enabled(entry, surface_index, enabled):
    menu = (entry.get("target") or {}).get("menu_xmlid")
    return location_business_enabled(surface_index.get(menu), enabled)


def filter_business_authority(authority, *, surface_index, enabled, entries, menu_xmlids_by_id,
                              menu_xmlids_by_action=None):
    """Only remove existing authority; never manufacture allowed routes.

    Legacy aliases resolve through their menu binding, never textual key equality.
    Missing bindings fail closed, including bare actions without an authorized
    menu carrier. Only the explicit initialization lifecycle exception below is
    menu-less. The caller supplies current native menu identities.
    """
    # Native membership is used only to restrict rows already published by P0.
    # A bare action shared by multiple delivery surfaces remains usable through
    # any enabled surface; an explicit menu/legacy route retains its own scope.
    action_menus = menu_xmlids_by_action or {}
    published_menu_pairs = set()
    for bucket in AUTHORITY_BUCKETS:
        for row in authority.get(bucket) or []:
            menu = row.get("menu_xmlid") or menu_xmlids_by_id.get(row.get("menu_id"))
            if menu and row.get("action_id") and row.get("allowed") is not False:
                published_menu_pairs.add((row["action_id"], menu))
    result = deepcopy(authority)
    entry_by_key = {entry["code"]: entry for entry in entries if entry.get("code")}
    denied = result.setdefault("denied_actions", [])
    for bucket in AUTHORITY_BUCKETS:
        kept = []
        for row in result.get(bucket) or []:
            menu = row.get("menu_xmlid") or menu_xmlids_by_id.get(row.get("menu_id"))
            location = surface_index.get(menu)
            legacy = entry_by_key.get(row.get("scene_key"))
            if not location and legacy and not menu and not row.get("menu_id"):
                location = surface_index.get((legacy.get("target") or {}).get("menu_xmlid"))
            allowed = location_business_enabled(location, enabled)
            if not location and legacy is None and not row.get("scene_key") and not menu and not row.get("menu_id"):
                locations = [surface_index[xmlid] for xmlid in action_menus.get(row.get("action_id"), ())
                             if xmlid in surface_index and (row.get("action_id"), xmlid) in published_menu_pairs]
                if locations:
                    allowed = any(location_business_enabled(item, enabled) for item in locations)
            # Initialization precedes business-scene enablement. This lifecycle
            # declaration preserves already-authorized internal actions only;
            # it neither adds routes nor overrides an explicit business menu.
            if (not location and legacy and not menu and not row.get("menu_id")
                    and legacy.get("enablement_scope") == "enterprise_initialization"
                    and row.get("source") == "scene_internal_action_authority"
                    and row.get("allowed") is True):
                allowed = True
            if bucket == "menu_containers" and location and location["location"] == "container" and not row.get("action_id"):
                allowed = True
            if allowed:
                kept.append(row)
            else:
                denied.append({**row, "route_kind": "DENIED", "allowed_operation": "none",
                               "reason_code": ("BUSINESS_SCENARIO_CONFIGURATION_MISSING"
                                               if not location or location["location"] == "missing"
                                               else "BUSINESS_SCENARIO_NOT_ENABLED")})
        result[bucket] = kept
    return result
