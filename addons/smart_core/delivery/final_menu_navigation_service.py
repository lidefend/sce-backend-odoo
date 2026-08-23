# -*- coding: utf-8 -*-
from __future__ import annotations

try:
    from odoo import SUPERUSER_ID, api
except Exception:  # pragma: no cover - lightweight unit-test stubs
    SUPERUSER_ID = 1
    api = None

from odoo.addons.smart_core.security.platform_admin import (
    user_is_platform_admin,
)
from odoo.addons.smart_core.utils.backend_contract_boundaries import MENU_CONFIG_POLICY_MODEL
from odoo.addons.smart_core.utils.extension_hooks import call_extension_hook_first


SOURCE_KIND = "platform_menu_delivery_projection"
SOURCE_AUTHORITIES = (
    "ir.ui.menu",
    "ir.actions.act_window",
    "res.groups",
    MENU_CONFIG_POLICY_MODEL,
    "extension_business_config_role_resolver",
)
NO_BUSINESS_FACT_AUTHORITY = True


def source_authority_contract() -> dict:
    return {
        "kind": SOURCE_KIND,
        "authorities": list(SOURCE_AUTHORITIES),
        "projection_only": True,
        "no_business_fact_authority": NO_BUSINESS_FACT_AUTHORITY,
    }


def _to_int(value) -> int:
    try:
        parsed = int(value or 0)
    except Exception:
        return 0
    return parsed if parsed > 0 else 0


def _text(value) -> str:
    return str(value or "").strip()


def _delivery_node_menu_id(node: dict) -> int:
    meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
    for candidate in (node.get("menu_id"), meta.get("menu_id"), node.get("id")):
        menu_id = _to_int(candidate)
        if menu_id:
            return menu_id
    return 0


def _delivery_node_config_menu_id(node: dict) -> int:
    meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
    config_ref = node.get("config_ref") if isinstance(node.get("config_ref"), dict) else meta.get("config_ref")
    config_ref = config_ref if isinstance(config_ref, dict) else {}
    for candidate in (
        node.get("config_menu_id"),
        meta.get("config_menu_id"),
        config_ref.get("id") if _text(config_ref.get("model") or "ir.ui.menu") == "ir.ui.menu" else 0,
    ):
        menu_id = _to_int(candidate)
        if menu_id:
            return menu_id
    return _delivery_node_menu_id(node)


def _delivery_node_label(node: dict) -> str:
    return _text(node.get("name") or node.get("label") or node.get("title"))


def _delivery_node_to_fact(node: dict) -> dict:
    meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
    config_ref = node.get("config_ref") if isinstance(node.get("config_ref"), dict) else meta.get("config_ref")
    config_ref = config_ref if isinstance(config_ref, dict) else {}
    children = [_delivery_node_to_fact(child) for child in node.get("children") or [] if isinstance(child, dict)]
    runtime_menu_id = _delivery_node_menu_id(node)
    menu_id = _delivery_node_config_menu_id(node)
    label = _delivery_node_label(node)
    configurable = bool(menu_id and _text((config_ref or {}).get("model") or "ir.ui.menu") == "ir.ui.menu")
    action_id = _to_int(node.get("action_id") or meta.get("action_id"))
    model = _text(node.get("model") or meta.get("model"))
    action_raw = _text(node.get("action") or meta.get("action") or (f"ir.actions.act_window,{action_id}" if action_id else ""))
    out = {
        "menu_id": menu_id,
        "runtime_menu_id": runtime_menu_id,
        "config_menu_id": menu_id,
        "config_ref": config_ref or ({"model": "ir.ui.menu", "id": menu_id} if menu_id else {}),
        "configurable": configurable,
        "synthetic": bool(runtime_menu_id and menu_id and runtime_menu_id != menu_id),
        "node_kind": "group" if children else "leaf",
        "key": f"menu:{menu_id}" if menu_id else "menu:unknown",
        "name": label,
        "label": label,
        "title": label,
        "parent_id": _to_int(node.get("parent_id") or meta.get("parent_id")),
        "complete_name": _text(node.get("complete_name") or label),
        "sequence": _to_int(node.get("sequence") or meta.get("sequence")),
        "groups": node.get("groups") if isinstance(node.get("groups"), list) else [],
        "web_icon": _text(node.get("web_icon") or meta.get("web_icon")),
        "has_children": bool(children),
        "action_raw": action_raw,
        "action_type": "ir.actions.act_window" if action_id else "",
        "action_id": action_id or None,
        "action_exists": bool(action_id),
        "action_meta": {
            "model": model,
            "route": _text(node.get("route") or meta.get("route")),
            "entry_target": meta.get("entry_target") if isinstance(meta.get("entry_target"), dict) else {},
        },
        "children": children,
    }
    return out


def _flatten_fact_tree(nodes: list[dict]) -> list[dict]:
    flat: list[dict] = []

    def walk(items: list[dict]):
        for item in items or []:
            if not isinstance(item, dict):
                continue
            flat.append({
                key: value
                for key, value in item.items()
                if key != "children"
            } | {"child_ids": [_to_int(child.get("menu_id")) for child in item.get("children") or [] if _to_int(child.get("menu_id"))]})
            walk(item.get("children") or [])

    walk(nodes)
    return flat


class FinalMenuNavigationService:
    def __init__(self, env):
        self.env = env

    def build(self, *, scene_map: dict | None = None, policy: dict | None = None) -> dict:
        del scene_map, policy
        return self._build_delivery_navigation_contract()

    def _business_root_xmlid(self) -> str:
        root_xmlid = _text(call_extension_hook_first(self.env, "smart_core_business_root_menu_xmlid", self.env))
        if root_xmlid:
            return root_xmlid
        try:
            return _text(self.env["ir.config_parameter"].sudo().get_param("smart_core.business_root_menu_xmlid", ""))
        except Exception:
            return ""

    def _business_root_menu_id(self) -> int:
        root_xmlid = self._business_root_xmlid()
        if not root_xmlid:
            return 0
        try:
            root = self.env.ref(root_xmlid, raise_if_not_found=False)
        except Exception:
            root = None
        return _to_int(getattr(root, "id", 0)) if root and _text(getattr(root, "_name", "")) == "ir.ui.menu" else 0

    def _runtime_role_surface(self, identity: dict | None = None, nav_tree: list | None = None) -> dict:
        is_platform_admin = self._is_platform_admin_user()
        is_business_config_admin = self._is_business_config_user()
        declared = (
            identity.get("role_surface")
            if isinstance(identity, dict)
            and isinstance(identity.get("role_surface"), dict)
            else {}
        )
        if declared:
            surface = dict(declared)
            surface["is_platform_admin"] = is_platform_admin
            surface["is_business_config_admin"] = is_business_config_admin
            surface["system_configuration_visible"] = bool(
                surface.get("system_configuration_visible")
                and (is_platform_admin or is_business_config_admin)
            )
            return surface
        from odoo.addons.smart_core.identity.identity_resolver import IdentityResolver

        resolver = IdentityResolver(self.env)
        surface = resolver.build_role_surface(
            resolver.user_group_xmlids(self.env.user),
            nav_tree if isinstance(nav_tree, list) else [],
            set(),
        )
        surface["is_platform_admin"] = is_platform_admin
        surface["is_business_config_admin"] = is_business_config_admin
        surface["system_configuration_visible"] = bool(
            surface.get("system_configuration_visible")
            and (is_platform_admin or is_business_config_admin)
        )
        return surface

    def _current_delivery_identity(self) -> dict:
        identity = call_extension_hook_first(self.env, "smart_core_resolve_startup_delivery_identity", self.env, {})
        return identity if isinstance(identity, dict) else {}

    def _build_delivery_navigation_contract(self) -> dict:
        if api is None:
            raise RuntimeError("odoo_api_unavailable")
        from odoo.addons.smart_core.adapters.nav_tree_cleaner import NavTreeCleaner
        from odoo.addons.smart_core.adapters.odoo_nav_adapter import OdooNavAdapter
        from odoo.addons.smart_core.app_config_engine.services.dispatchers.nav_dispatcher import NavDispatcher
        from odoo.addons.smart_core.core.system_init_nav_request_builder import SystemInitNavRequestBuilder
        from odoo.addons.smart_core.delivery.delivery_engine import DeliveryEngine

        params = {}
        root_menu_id = self._business_root_menu_id()
        if root_menu_id:
            params["root_menu_id"] = root_menu_id
        su_env = api.Environment(self.env.cr, SUPERUSER_ID, dict(self.env.context or {}))
        nav_request = SystemInitNavRequestBuilder.build(params, "web")
        nav_data, nav_versions = NavDispatcher(self.env, su_env).build_nav(nav_request)
        native_nav = NavTreeCleaner().clean(nav_data.get("nav") if isinstance(nav_data, dict) else [])
        OdooNavAdapter().enrich(self.env, native_nav)
        identity = self._current_delivery_identity()
        delivery_payload = DeliveryEngine(self.env).build(
            data={"role_surface": self._runtime_role_surface(identity, native_nav)},
            product_key=_text(identity.get("product_key")) if isinstance(identity, dict) else "",
            edition_key=_text(identity.get("edition_key")) if isinstance(identity, dict) else "",
            base_product_key=_text(identity.get("base_product_key")) if isinstance(identity, dict) else "",
            native_nav=native_nav,
        )
        delivery_nav = delivery_payload.get("nav") if isinstance(delivery_payload, dict) else []
        if not isinstance(delivery_nav, list) or not delivery_nav:
            raise RuntimeError("delivery_navigation_contract_empty")
        tree = [_delivery_node_to_fact(node) for node in delivery_nav if isinstance(node, dict)]
        flat = _flatten_fact_tree(tree)
        if not flat:
            raise RuntimeError("delivery_navigation_fact_empty")
        nav_fact = {"flat": flat, "tree": tree}
        return {
            "nav_fact": nav_fact,
            "nav_explained": nav_fact,
            "meta": {
                "source_authority": source_authority_contract(),
                "menu_fact_source_authority": {},
                "delivery_convergence": {"source": "delivery_engine"},
                "delivery_engine": {
                    "source": "delivery_engine",
                    "nav_versions": nav_versions if isinstance(nav_versions, dict) else {},
                },
                "user_menu_config": delivery_payload.get("meta", {}).get("user_menu_config", {}) if isinstance(delivery_payload.get("meta"), dict) else {},
            },
        }

    def _is_platform_admin_user(self) -> bool:
        try:
            return bool(user_is_platform_admin(self.env.user))
        except Exception:
            return False

    def _configured_business_config_admin_group_xmlids(self) -> list[str]:
        hook_groups = call_extension_hook_first(
            self.env,
            "smart_core_business_config_admin_group_xmlids",
            self.env,
        )
        if isinstance(hook_groups, (list, tuple, set)):
            groups = [str(item or "").strip() for item in hook_groups if str(item or "").strip()]
            if groups:
                return groups
        try:
            raw = self.env["ir.config_parameter"].sudo().get_param("smart_core.business_config_admin_group_xmlids", "")
        except Exception:
            raw = ""
        groups = [item.strip() for item in str(raw or "").split(",") if item.strip()]
        return groups or ["smart_core.group_smart_core_business_config_admin"]

    def _is_business_config_user(self) -> bool:
        for group_xmlid in self._configured_business_config_admin_group_xmlids():
            try:
                if self.env.user.has_group(group_xmlid):
                    return True
            except Exception:
                continue
        return False
