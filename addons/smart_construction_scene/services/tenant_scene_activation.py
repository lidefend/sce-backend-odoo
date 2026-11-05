# -*- coding: utf-8 -*-
"""Pure tenant scene activation decisions.

Keeps PRODUCT_RELEASED (product publication) and TENANT_ENABLED (enterprise
choice) separate. It never stores ROLE_ASSIGNED or USER_ACCESSIBLE: role
applicability is projected from the existing role candidate maps, and user
reachability is computed at runtime by Navigation Authority + ACL/Record Rules.
"""
from __future__ import annotations

from typing import Any


ENTERPRISE_SETUP_CODE = "enterprise.setup"
ENTERPRISE_SETUP_MENU_XMLID = "smart_construction_core.menu_sc_enterprise_initialization"
ENTERPRISE_SETUP_ACTION_XMLID = "smart_construction_core.action_sc_enterprise_initialization"
ENABLEMENT_PARAM_PREFIX = "sc.scene.tenant.enablement."


def _enablement_param_key(company_id, scene_key) -> str:
    return f"{ENABLEMENT_PARAM_PREFIX}{int(company_id)}.{str(scene_key or '').strip()}"


def read_tenant_enablement(env, company_id, scene_key) -> bool:
    """Read the tenant enablement decision from the governed native config."""
    if env is None:
        return False
    try:
        value = env["ir.config_parameter"].sudo().get_param(_enablement_param_key(company_id, scene_key))
        if value:
            return str(value or "").strip().lower() in ("1", "true", "yes", "on")
    except Exception:
        pass
    # Legacy compatibility read: existing enablement records remain authoritative
    # until they are migrated to the native config carrier. Read-only.
    try:
        record = env["sc.scene.company.enablement"].sudo().search(
            [("company_id", "=", int(company_id)), ("scene_key", "=", str(scene_key or "").strip())],
            limit=1,
        )
        return bool(record.enabled) if record else False
    except Exception:
        return False


def write_tenant_enablement(env, company_id, scene_key, enabled: bool) -> None:
    """Record the tenant enablement decision in the governed native config."""
    if env is None:
        return
    env["ir.config_parameter"].sudo().set_param(
        _enablement_param_key(company_id, scene_key), "1" if enabled else "0"
    )


def resolve_scene_menu(scene_key: str, entries: list[dict[str, Any]] | None = None) -> str:
    """Map a scene key to its menu xmlid via the scene registry content."""
    key = str(scene_key or "").strip()
    if not key:
        return ""
    if key == ENTERPRISE_SETUP_CODE:
        return ENTERPRISE_SETUP_MENU_XMLID
    if entries is None:
        from odoo.addons.smart_construction_scene.profiles.scene_registry_content import (
            list_scene_entries,
        )
        entries = list_scene_entries()
    for entry in entries:
        if not isinstance(entry, dict) or str(entry.get("code") or entry.get("key") or "").strip() != key:
            continue
        target = entry.get("target") if isinstance(entry.get("target"), dict) else {}
        return str(target.get("menu_xmlid") or "").strip()
    return ""


def resolve_entry_release_state(entry: dict[str, Any], release_state_by_menu: dict[str, str]) -> str:
    """Read standard-edition qualification from the entry's published menu binding.

    Scene version lifecycle values are deliberately not inputs to this decision.
    Unknown or menu-less entries cannot acquire release qualification here.
    """
    target = entry.get("target") if isinstance(entry.get("target"), dict) else {}
    menu_xmlid = str(target.get("menu_xmlid") or "").strip()
    return str(release_state_by_menu.get(menu_xmlid) or "").strip() if menu_xmlid else ""


def resolve_entry_surface(entry: dict[str, Any], surface_index: dict | None) -> dict | None:
    """Read business grouping by menu binding, never by legacy scene-key equality.

    This is descriptive projection only. It must not translate or broaden a
    company's persisted enablement decision to the business scenario group.
    """
    target = entry.get("target") if isinstance(entry.get("target"), dict) else {}
    menu_xmlid = str(target.get("menu_xmlid") or "").strip()
    location = (surface_index or {}).get(menu_xmlid)
    return dict(location) if location else None


def resolve_product_released(
    scene_key: str,
    *,
    env=None,
    entries: list[dict[str, Any]] | None = None,
    release_state_by_menu: dict[str, str] | None = None,
) -> bool:
    """Whether the product publishes the scene's menu for the standard edition."""
    from odoo.addons.smart_construction_scene.services.business_scene_enablement import BUSINESS_PREFIX, business_catalog
    if scene_key.startswith(BUSINESS_PREFIX):
        from odoo.addons.smart_construction_core.services.scenario_surface_projection import load_runtime_surface
        if release_state_by_menu is None:
            from odoo.addons.smart_construction_core.services.product_menu_source import load_menu_release_states
            release_state_by_menu = load_menu_release_states()
        key = scene_key[len(BUSINESS_PREFIX):]
        return any(row["scene_key"] == key and row["product_released"]
                   for row in business_catalog(load_runtime_surface(env), release_state_by_menu, {}))
    menu_xmlid = resolve_scene_menu(scene_key, entries=entries)
    if not menu_xmlid:
        return False
    if release_state_by_menu is None:
        from odoo.addons.smart_construction_core.services.product_menu_source import (
            load_menu_release_states,
        )
        release_state_by_menu = load_menu_release_states()
    return resolve_entry_release_state({"target": {"menu_xmlid": menu_xmlid}}, release_state_by_menu) == "released"


def decide_tenant_enablement(
    *,
    product_released: bool,
    currently_enabled: bool,
    requested: bool,
) -> tuple[bool, bool]:
    """Return ``(allowed, next_enabled)``.

    - A preview (not product-released) scene can never be tenant-enabled.
    - Disable is always allowed and never touches business facts.
    - Enable/disable is idempotent: a no-op is allowed and yields no change.
    """
    if requested and not product_released:
        return (False, currently_enabled)
    return (True, requested)
