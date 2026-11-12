# -*- coding: utf-8 -*-
"""Shared platform-minimum navigation declaration.

The platform control database installs only ``smart_core``.  In that mode the
startup surface and the standalone menu APIs must expose exactly the same
minimum navigation contract; otherwise ``system.init`` succeeds while
``/api/menu/*`` raises ``delivery_navigation_contract_empty``.

The single scene leaf is a contract-declared target, not a business menu.  It
carries the same synthetic identity convention the scene navigation builder
uses, so the canonical navigation projector can authorize it without inventing
a real ``ir.ui.menu`` row or exposing platform configuration menus.
"""

from __future__ import annotations

import zlib
from typing import List

from odoo.addons.smart_core.utils.extension_hooks import call_extension_hook_first

SOURCE = "platform_minimum_surface"
WORKSPACE_SCENE_KEY = "workspace.home"


def _synthetic_menu_id(key: str, base: int = 700_000_000, span: int = 200_000_000) -> int:
    raw = zlib.crc32(str(key or "").encode("utf-8")) & 0xFFFFFFFF
    return int(base + (raw % span))


def _is_any_module_installed(env, module_names: List[str]) -> bool:
    safe_names = [str(name or "").strip() for name in (module_names or []) if str(name or "").strip()]
    if not safe_names:
        return False
    try:
        count = env["ir.module.module"].sudo().search_count([
            ("name", "in", safe_names),
            ("state", "=", "installed"),
        ])
        return bool(count)
    except Exception:
        return False


def resolve_industry_extension_modules(env) -> list[str]:
    hook_modules = call_extension_hook_first(
        env,
        "smart_core_industry_extension_module_names",
        env,
    )
    if isinstance(hook_modules, (list, tuple, set)):
        modules = [str(name or "").strip() for name in hook_modules if str(name or "").strip()]
        if modules:
            return modules
    try:
        raw = env["ir.config_parameter"].sudo().get_param("smart_core.industry_extension_modules", "")
    except Exception:
        raw = ""
    return [item.strip() for item in str(raw or "").split(",") if item.strip()]


def is_platform_minimum_surface_mode(env, delivery_identity: dict | None = None) -> bool:
    identity = delivery_identity if isinstance(delivery_identity, dict) else {}
    base_product_key = str(identity.get("base_product_key") or "").strip()
    product_key = str(identity.get("product_key") or "").strip()
    if base_product_key == "platform" or product_key.startswith("platform."):
        return True
    return not _is_any_module_installed(env, resolve_industry_extension_modules(env))


def build_platform_minimum_nav_contract() -> dict:
    workspace_menu_id = _synthetic_menu_id(f"scene:{WORKSPACE_SCENE_KEY}")
    workspace_entry_target = {
        "type": "scene",
        "scene_key": WORKSPACE_SCENE_KEY,
        "route": "/",
    }
    workspace_leaf = {
        "key": f"scene:{WORKSPACE_SCENE_KEY}",
        "label": "角色首页",
        "title": "角色首页",
        "menu_id": workspace_menu_id,
        "menu_xmlid": "scene.contract.workspace_home",
        "children": [],
        "scene_key": WORKSPACE_SCENE_KEY,
        "route": "/",
        "entry_target": dict(workspace_entry_target),
        "meta": {
            "scene_key": WORKSPACE_SCENE_KEY,
            "action_type": "scene.contract",
            "scene_source": SOURCE,
            "menu_xmlid": "scene.contract.workspace_home",
            "route": "/",
            "entry_target": dict(workspace_entry_target),
        },
    }
    group_node = {
        "key": "group:role_primary",
        "label": "我的场景",
        "title": "我的场景",
        "menu_id": _synthetic_menu_id("group:role_primary", base=640_000_000, span=40_000_000),
        "children": [workspace_leaf],
        "meta": {
            "group_key": "role_primary",
            "scene_source": SOURCE,
        },
    }
    root_node = {
        "key": "root:scene_contract",
        "label": "场景导航",
        "title": "场景导航",
        "menu_id": _synthetic_menu_id("root:scene_contract", base=600_000_000, span=20_000_000),
        "children": [group_node],
        "meta": {
            "scene_source": SOURCE,
            "menu_xmlid": "scene.contract.root",
        },
    }
    default_route = {
        "menu_id": workspace_menu_id,
        "scene_key": WORKSPACE_SCENE_KEY,
        "route": "/",
        "reason": SOURCE,
    }
    return {
        "source": SOURCE,
        "nav": [root_node],
        "default_route": default_route,
        "meta": {
            "platform_minimum_surface": True,
            "scene_count": 1,
            "scene_input_count": 1,
            "excluded_scene_count": 0,
            "candidate_count": 1,
            "group_count": 1,
            "remaining_group_count": 0,
            "remaining_hidden": False,
            "policy_applied": False,
            "nav_source": SOURCE,
        },
    }


def merge_authenticated_safe_landing(nav, authority, *, authenticated):
    """Add only the declared actionless platform home after business selection.

    This is the platform's authenticated landing guarantee, independent of
    product exposure and tenant business enablement; it grants no native action.
    """
    from copy import deepcopy

    nav, authority = deepcopy(nav), deepcopy(authority)
    if not authenticated:
        return nav, authority
    buckets = ("primary_actions", "role_home_actions", "contextual_actions", "admin_actions")

    def is_home(row):
        target = row.get("entry_target") or (row.get("meta") or {}).get("entry_target") or {}
        return (not int(row.get("action_id") or (row.get("meta") or {}).get("action_id") or 0)
                and target.get("type") == "scene" and target.get("scene_key") == WORKSPACE_SCENE_KEY)

    allowed = {int(row.get("menu_id") or 0) for bucket in buckets
               for row in authority.get(bucket, []) if is_home(row)}

    def has_home(nodes):
        return any((is_home(row) and int(row.get("menu_id") or 0) in allowed)
                   or has_home(row.get("children") or []) for row in nodes)

    if has_home(nav):
        return nav, authority
    minimum = build_platform_minimum_nav_contract()["nav"]
    leaf = minimum[0]["children"][0]["children"][0]
    entry = {
        "menu_id": leaf["menu_id"], "menu_xmlid": leaf["menu_xmlid"], "action_id": 0,
        "route_kind": "ROLE_HOME_ACTION", "scene_key": WORKSPACE_SCENE_KEY,
        "entry_target": dict(leaf["entry_target"]), "route": leaf["route"],
        "name": leaf["label"], "allowed_operation": "read", "context_requirements": {},
        "required_capability": "menu_container_visible", "source": SOURCE,
    }
    existing = [row for bucket in buckets for row in authority.get(bucket, [])
                if int(row.get("menu_id") or 0) == leaf["menu_id"]]
    if any(not is_home(row) for row in existing):
        raise ValueError("PLATFORM_HOME_IDENTITY_CONFLICT")
    if not existing:
        authority.setdefault("role_home_actions", []).append(entry)

    def merge(nodes, additions):
        for addition in additions:
            matches = [row for row in nodes if row.get("key") == addition["key"]]
            if not matches:
                nodes.append(addition)
                continue
            current = matches[0]
            if len(matches) != 1 or current.get("menu_id") != addition["menu_id"]:
                raise ValueError("PLATFORM_HOME_CONTAINER_CONFLICT")
            if addition.get("children"):
                merge(current.setdefault("children", []), addition["children"])
            elif not is_home(current):
                raise ValueError("PLATFORM_HOME_TARGET_CONFLICT")
    merge(nav, minimum)
    return nav, authority
