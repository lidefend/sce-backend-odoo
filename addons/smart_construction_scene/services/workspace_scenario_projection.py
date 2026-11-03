# -*- coding: utf-8 -*-
"""Pure role-workspace scenario projection.

Computes PRODUCT_RELEASED x TENANT_ENABLED x ROLE_ASSIGNED per scene. It never
persists USER_ACCESSIBLE and never creates a parallel role-scene table: role
assignment is projected from the current principal's published route authority,
and final access remains subject to runtime authority + ACL/Record Rules.
"""
from __future__ import annotations

from typing import Any

from odoo.addons.smart_construction_scene.services.tenant_scene_activation import resolve_entry_release_state, resolve_entry_surface


def resolve_allowed_company_id(requested: Any, allowed_company_ids: set[int], default: int) -> int:
    """Resolve a company id that the principal is allowed to use.

    Client-supplied company hints are never trusted: a requested company that is
    not in the principal's allowed set falls back to the default company.
    """
    allowed = {int(x) for x in allowed_company_ids if int(x) > 0}
    requested_id = int(requested or 0)
    if requested_id in allowed:
        return requested_id
    return int(default or 0)


def resolve_request_company(requested: Any, allowed_company_ids: set[int], default: int) -> tuple[int, dict | None]:
    """Resolve a client-requested company with explicit rejection.

    An omitted/empty request resolves to the default company. An explicit request
    outside the principal's allowed set is rejected instead of silently falling
    back, so the service never trusts an arbitrary client company hint.
    """
    allowed = {int(x) for x in allowed_company_ids if int(x) > 0}
    if requested in (None, "", 0, "0") and not isinstance(requested, (bool, float)):
        company_id = int(default or 0)
    else:
        # Company identifiers are integers, never truth values or rounded numbers.
        if isinstance(requested, bool) or not isinstance(requested, (int, str)):
            return 0, {"code": 400, "message": "invalid company_id"}
        try:
            company_id = int(requested)
        except (TypeError, ValueError):
            return 0, {"code": 400, "message": "invalid company_id"}
    if company_id not in allowed:
        return 0, {"code": 403, "message": "company not authorized"}
    return company_id, None


def bind_company_context(env, company_id):
    """Bind a previously validated company without changing the principal.

    Narrow the active company set as well as the query domain so record rules
    and company-dependent values observe the same request. Native data-company
    restrictions remain authoritative; this does not grant company access.
    """
    return env(context={**env.context, "allowed_company_ids": [company_id]})


def authorized_scene_candidates(*, entries, authority, resolve_ref) -> list[str]:
    """Project registry entries from authorized menu/action pairs, never role names.

    XML ids identify the requested route; their existence does not grant access.
    A container alone or a different action on the same menu is insufficient.
    """
    from odoo.addons.smart_core.delivery.runtime_route_authority import menu_publication_decision

    if not isinstance(authority, dict) or not authority:
        return []
    candidates = []
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        key = str(entry.get("code") or entry.get("key") or "").strip()
        target = entry.get("target") if isinstance(entry.get("target"), dict) else {}
        menu_xmlid = str(target.get("menu_xmlid") or "").strip()
        if not key or key in seen or not menu_xmlid:
            continue
        menu = resolve_ref(menu_xmlid, raise_if_not_found=False)
        if not menu or menu._name != "ir.ui.menu":
            continue
        action_xmlid = str(target.get("action_xmlid") or "").strip()
        action = resolve_ref(action_xmlid, raise_if_not_found=False) if action_xmlid else menu.action
        if not action or not action._name.startswith("ir.actions.") or not action.id:
            continue
        if menu_publication_decision(authority, menu.id, action.id) is True:
            candidates.append(key)
            seen.add(key)
    return candidates


def project_workspace_scenes(
    *,
    entries: list[dict[str, Any]],
    release_state_by_menu: dict[str, str],
    tenant_enabled_by_scene: dict[str, bool],
    role_scene_candidates: list[str],
    surface_index: dict | None = None,
    business_enabled_by_scene: dict | None = None,
) -> dict[str, Any]:
    role_candidates = {str(x) for x in role_scene_candidates if str(x).strip()}
    enabled_map = {str(k): bool(v) for k, v in (tenant_enabled_by_scene or {}).items()}
    rows: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        scene_key = str(entry.get("code") or entry.get("key") or "").strip()
        if not scene_key:
            continue
        product_released = resolve_entry_release_state(entry, release_state_by_menu) == "released"
        if business_enabled_by_scene is not None:
            from odoo.addons.smart_construction_scene.services.business_scene_enablement import entry_business_enabled
            tenant_enabled = entry_business_enabled(entry, surface_index or {}, business_enabled_by_scene)
        else:
            # Legacy pure projection API retained for explicit entry-level callers;
            # the runtime handler always supplies the business-scoped map.
            tenant_enabled = enabled_map.get(scene_key, False)
        role_assigned = scene_key in role_candidates
        rows.append(
            {
                "scene_key": scene_key,
                "product_surface": resolve_entry_surface(entry, surface_index),
                "name": str(entry.get("name") or scene_key).strip(),
                "product_released": product_released,
                "tenant_enabled": tenant_enabled,
                "role_assigned": role_assigned,
                # Candidate reachability; USER_ACCESSIBLE is decided at runtime.
                "workspace_candidate": product_released and tenant_enabled and role_assigned,
            }
        )
    return {
        "contract_version": "workspace_scenario_projection.v1",
        "rows": rows,
        "row_count": len(rows),
        "workspace_candidate_count": sum(1 for row in rows if row["workspace_candidate"]),
    }
