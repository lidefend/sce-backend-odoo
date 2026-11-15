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

from .navigation_identity import WORKBENCH_GROUP_KEY, WORKSPACE_SCENE_KEY
from odoo.addons.smart_core.utils.extension_hooks import call_extension_hook_first

SOURCE = "platform_minimum_surface"


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
        "sequence": 0,
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
        "key": f"group:{WORKBENCH_GROUP_KEY}",
        "label": "工作台",
        "title": "工作台",
        "menu_id": _synthetic_menu_id(f"group:{WORKBENCH_GROUP_KEY}", base=640_000_000, span=40_000_000),
        "sequence": 10,
        "children": [workspace_leaf],
        "meta": {
            "group_key": WORKBENCH_GROUP_KEY,
            "canonical_group_key": WORKBENCH_GROUP_KEY,
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
                if is_home(addition):
                    nodes.insert(0, addition)
                else:
                    nodes.append(addition)
                continue
            current = matches[0]
            if len(matches) != 1 or current.get("menu_id") != addition["menu_id"]:
                raise ValueError("PLATFORM_HOME_CONTAINER_CONFLICT")
            if addition.get("children"):
                merge(current.setdefault("children", []), addition["children"])
            elif not is_home(current):
                raise ValueError("PLATFORM_HOME_TARGET_CONFLICT")
    minimum_group = minimum[0]["children"][0]

    def workbench_identity(node):
        if not isinstance(node, dict) or not isinstance(node.get("children"), list) or node.get("action_id"):
            return None
        meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
        canonical = str(
            node.get("canonical_group_key")
            or meta.get("canonical_group_key")
            or node.get("group_key")
            or meta.get("group_key")
            or ""
        ).strip()
        if canonical != WORKBENCH_GROUP_KEY:
            return None
        try:
            config_menu_id = int(
                node.get("config_menu_id")
                or meta.get("config_menu_id")
                or 0
            )
        except (TypeError, ValueError):
            config_menu_id = 0
        native_center_xmlid = str(
            node.get("native_center_xmlid")
            or meta.get("native_center_xmlid")
            or ""
        ).strip()
        return {
            "canonical_group_key": canonical,
            "config_menu_id": config_menu_id,
            "native_center_xmlid": native_center_xmlid,
        }

    def assert_same_workbench_identity(primary_identity, duplicate_identity):
        primary_config = int(primary_identity["config_menu_id"] or 0)
        duplicate_config = int(duplicate_identity["config_menu_id"] or 0)
        if primary_config and duplicate_config and primary_config != duplicate_config:
            raise ValueError("PLATFORM_WORKBENCH_IDENTITY_CONFLICT: config_menu_id")
        primary_xmlid = str(primary_identity["native_center_xmlid"] or "")
        duplicate_xmlid = str(duplicate_identity["native_center_xmlid"] or "")
        if primary_xmlid and duplicate_xmlid and primary_xmlid != duplicate_xmlid:
            raise ValueError("PLATFORM_WORKBENCH_IDENTITY_CONFLICT: native_center_xmlid")

    for root in nav:
        children = root.get("children") if isinstance(root, dict) and isinstance(root.get("children"), list) else []
        matches = []
        for index, node in enumerate(children):
            identity = workbench_identity(node)
            if identity:
                matches.append((index, node, identity))
        if not matches:
            continue
        primary_index, primary, primary_identity = matches[0]
        for duplicate_index, duplicate, duplicate_identity in reversed(matches[1:]):
            assert_same_workbench_identity(primary_identity, duplicate_identity)
            merge(primary["children"], duplicate["children"])
            children.pop(duplicate_index)
        merge(primary["children"], minimum_group["children"])
        children.insert(0, children.pop(primary_index))
        return nav, authority
    if nav:
        for root in nav:
            children = root.get("children") if isinstance(root, dict) and isinstance(root.get("children"), list) else None
            if children is not None:
                children.insert(0, minimum_group)
                return nav, authority
    nav.extend(minimum)
    return nav, authority
