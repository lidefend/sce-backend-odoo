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
        menus = [
            menu
            for menu, location in index.items()
            if any(
                candidate.get("location") == "scenario"
                and candidate.get("scenario_key") == key
                for candidate in _scenario_locations(location)
            )
        ]
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


def _scenario_locations(location):
    if not isinstance(location, dict):
        return []
    candidates = location.get("scenario_locations")
    if isinstance(candidates, list) and candidates:
        return [row for row in candidates if isinstance(row, dict)]
    if location.get("location") == "scenario":
        return [location]
    return []


def _location_sort_key(location):
    return (
        int(location.get("scenario_sequence") or 10),
        int(location.get("sequence") or 10),
        str(location.get("scenario_key") or ""),
        str(location.get("intent") or ""),
        int(location.get("entry_id") or 0),
    )


def enabled_scenario_locations(location, enabled):
    """Return enabled scenario placements in declared composition order."""
    rows = [
        candidate
        for candidate in _scenario_locations(location)
        if candidate.get("scenario_active", True)
        and enabled.get(candidate.get("scenario_key")) is True
    ]
    return sorted(rows, key=_location_sort_key)


def location_business_enabled(location, enabled):
    if not location or location["location"] == "missing":
        return False
    scenario_locations = _scenario_locations(location)
    if scenario_locations:
        return bool(enabled_scenario_locations(location, enabled))
    return location["location"] in ("exempt", "horizontal", "platform")


def entry_business_enabled(entry, surface_index, enabled):
    menu = (entry.get("target") or {}).get("menu_xmlid")
    return location_business_enabled(surface_index.get(menu), enabled)


def scenario_composition_selection(surface_index, enabled, *, company_id=0, menu_keys=None):
    """Project enabled scenario references for one final menu placement.

    A native menu may be referenced by multiple scenarios. The final navigation
    carries one node per native menu, while the remaining enabled placements are
    retained as diagnostics. Ordering is part of the scenario composition
    declaration, never ORM/query order.
    """
    selected_by_menu = {}
    shared_by_menu = {}
    allowed_menu_keys = set(menu_keys) if menu_keys is not None else None
    for menu_key, location in sorted((surface_index or {}).items()):
        if allowed_menu_keys is not None and menu_key not in allowed_menu_keys:
            continue
        candidates = sorted(_scenario_locations(location), key=_location_sort_key)
        if not candidates:
            continue
        enabled_locations = enabled_scenario_locations(location, enabled)
        menu_id = int(location.get("menu_id") or 0)
        if menu_id <= 0:
            continue
        selected = dict(enabled_locations[0]) if enabled_locations else {}
        selected["menu_key"] = menu_key
        selected["available_scenario_keys"] = [
            str(candidate.get("scenario_key") or "") for candidate in candidates
        ]
        selected_by_menu[str(menu_id)] = selected
        alternatives = [dict(candidate) for candidate in enabled_locations[1:]]
        if alternatives:
            shared_by_menu[str(menu_id)] = alternatives
    return {
        "authority": "sc.product.scenario.entry + tenant business scenario selection",
        "company_id": int(company_id or 0),
        "selection_order": "scenario.sequence, entry.sequence, scenario_key, intent, entry.id",
        "selected_by_menu": selected_by_menu,
        "shared_by_menu": shared_by_menu,
    }


def filter_business_authority(authority, *, surface_index, enabled, entries, menu_xmlids_by_id,
                              menu_xmlids_by_action=None, company_id=0):
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
    authority_menu_keys = set()
    published_menu_pairs = set()
    for bucket in AUTHORITY_BUCKETS:
        for row in authority.get(bucket) or []:
            menu = row.get("menu_xmlid") or menu_xmlids_by_id.get(row.get("menu_id"))
            if menu:
                authority_menu_keys.add(menu)
            elif row.get("action_id"):
                authority_menu_keys.update(action_menus.get(row["action_id"], ()))
            if menu and row.get("action_id") and row.get("allowed") is not False:
                published_menu_pairs.add((row["action_id"], menu))
    result = deepcopy(authority)
    result["scenario_composition"] = scenario_composition_selection(
        surface_index,
        enabled,
        company_id=company_id,
        menu_keys=authority_menu_keys,
    )
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
