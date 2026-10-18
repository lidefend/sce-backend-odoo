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
