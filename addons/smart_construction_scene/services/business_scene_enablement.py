# -*- coding: utf-8 -*-
"""Business scenario enablement; legacy entry keys never grant a scenario."""
from __future__ import annotations

from copy import deepcopy

BUSINESS_PREFIX = "business.v1:"
BUSINESS_SCOPE = "business.v1"
AUTHORITY_BUCKETS = ("primary_actions", "role_home_actions", "contextual_actions", "admin_actions", "menu_containers")
ENTERPRISE_INITIALIZATION_SCOPE = "enterprise_initialization"
ENTERPRISE_INITIALIZATION_SOURCES = frozenset({
    "native_business_config_menu_projection",
    "scene_internal_action_authority",
})


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
    runtime_scope = str(surface.get("runtime_scope") or "").strip()
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
        if runtime_scope == "published_release":
            released = list(menus) if scene.get("active", True) else []
        elif runtime_scope:
            released = []
        else:
            # Compatibility for callers invoking this pure function without a
            # runtime-scope annotation. Production runtime readers always pass
            # published_release or maintained_draft.
            released = [menu for menu in menus if release_states.get(menu) == "released"]
        is_enabled = enabled.get(key, False)
        if not scene.get("active", True):
            released = []
        actions = []
        if can_manage and is_enabled:
            actions.append({"key": "disable", "label": "停用", "enabled": False})
        elif can_manage and released:
            actions.append({"key": "enable", "label": "启用", "enabled": True})
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


def _initialization_authority_row(row, entry, menu_xmlid):
    """Whether a producer-published row belongs to the pre-scene initialization lifecycle.

    Business-scene selection starts after enterprise initialization. Only the
    exact native initialization identity (or the already-supported menu-less
    internal handling action) may cross that boundary. This never creates an
    entry and never accepts a client-declared scope.
    """
    if not isinstance(row, dict) or not isinstance(entry, dict):
        return False
    if entry.get("enablement_scope") != ENTERPRISE_INITIALIZATION_SCOPE:
        return False
    if row.get("allowed") is False or row.get("allowed_operation") == "none":
        return False
    source = str(row.get("source") or "").strip()
    if source not in ENTERPRISE_INITIALIZATION_SOURCES:
        return False
    if source == "scene_internal_action_authority":
        return not row.get("menu_xmlid") and not row.get("menu_id")
    target = entry.get("target") if isinstance(entry.get("target"), dict) else {}
    return bool(
        str(row.get("menu_xmlid") or menu_xmlid or "").strip()
        == str(target.get("menu_xmlid") or "").strip()
        and str(row.get("action_xmlid") or "").strip()
        == str(target.get("action_xmlid") or "").strip()
        and _int_or(row.get("action_id"), 0) > 0
    )


def _int_or(value, default):
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _location_sort_key(location):
    return (
        _int_or(location.get("scenario_sequence"), 10),
        _int_or(location.get("sequence"), 10),
        str(location.get("scenario_key") or ""),
        str(location.get("intent") or ""),
        _int_or(location.get("entry_id"), 0),
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
    if location.get("direct_platform_exempt"):
        return True
    scenario_locations = _scenario_locations(location)
    if scenario_locations:
        return bool(enabled_scenario_locations(location, enabled))
    return location["location"] in ("exempt", "horizontal", "platform")


def entry_business_enabled(entry, surface_index, enabled):
    menu = (entry.get("target") or {}).get("menu_xmlid")
    return location_business_enabled(surface_index.get(menu), enabled)


def scenario_center_enablement(surface_index, enabled):
    """Return enabled state for every center with scenario placements."""
    states = {}
    for location in (surface_index or {}).values():
        for candidate in _scenario_locations(location):
            center_key = str(candidate.get("center_key") or "").strip()
            scenario_key = str(candidate.get("scenario_key") or "").strip()
            if not center_key or not scenario_key:
                continue
            states[center_key] = bool(states.get(center_key)) or bool(
                candidate.get("scenario_active", True)
                and enabled.get(scenario_key) is True
            )
    return states


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
        selected = (
            dict(enabled_locations[0])
            if enabled_locations
            else dict(candidates[0])
            if location.get("direct_platform_exempt")
            else {}
        )
        if selected and not enabled_locations:
            selected["direct_exempt"] = True
            selected["direct_platform_kind"] = str(
                location.get("direct_platform_kind") or ""
            )
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
        "center_enablement": scenario_center_enablement(surface_index, enabled),
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
    initialization_entry_by_menu = {}
    for entry in entries:
        if entry.get("enablement_scope") != ENTERPRISE_INITIALIZATION_SCOPE:
            continue
        target = entry.get("target") if isinstance(entry.get("target"), dict) else {}
        menu_xmlid = str(target.get("menu_xmlid") or "").strip()
        if menu_xmlid:
            initialization_entry_by_menu[menu_xmlid] = entry
    denied = result.setdefault("denied_actions", [])
    for bucket in AUTHORITY_BUCKETS:
        kept = []
        for row in result.get(bucket) or []:
            menu = row.get("menu_xmlid") or menu_xmlids_by_id.get(row.get("menu_id"))
            location = surface_index.get(menu)
            legacy = entry_by_key.get(row.get("scene_key"))
            initialization_entry = initialization_entry_by_menu.get(menu) or legacy
            # Initialization precedes business-scene enablement. Preserve only
            # producer-published rows with the exact initialization identity;
            # resolving the legacy scene's menu must not make either the native
            # admin entry or internal handling action look like an unselected
            # business page.
            if _initialization_authority_row(row, initialization_entry, menu):
                kept.append(row)
                continue
            if not location and legacy and not menu and not row.get("menu_id"):
                location = surface_index.get((legacy.get("target") or {}).get("menu_xmlid"))
            allowed = location_business_enabled(location, enabled)
            if not location and legacy is None and not row.get("scene_key") and not menu and not row.get("menu_id"):
                locations = [surface_index[xmlid] for xmlid in action_menus.get(row.get("action_id"), ())
                             if xmlid in surface_index and (row.get("action_id"), xmlid) in published_menu_pairs]
                if locations:
                    allowed = any(location_business_enabled(item, enabled) for item in locations)
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
