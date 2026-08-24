# -*- coding: utf-8 -*-
from __future__ import annotations
import json
import re
from odoo.addons.smart_core.core.source_authority import build_source_authority_contract
from odoo.addons.smart_core.core.delivery_menu_defaults import (
    build_delivery_menu_child,
    build_delivery_menu_group,
    build_delivery_menu_root,
    synthetic_menu_id,
)
from odoo.addons.smart_core.delivery.menu_delivery_convergence_service import MenuDeliveryConvergenceService
from odoo.addons.smart_core.delivery.menu_fact_service import MenuFactService
from odoo.addons.smart_core.delivery.native_config_menu_projection import native_config_delivery_groups
from odoo.addons.smart_core.utils.backend_contract_boundaries import MENU_CONFIG_POLICY_MODEL
from odoo.addons.smart_core.utils.extension_hooks import call_extension_hook_first

_PREVIEW_GROUP_ANCHOR_SKIPPED_LABELS = {"系统菜单", "业务菜单"}
_CUSTOMER_ACCEPTANCE_GROUP_LABELS: set[str] = set()


def register_preview_group_anchor_skipped_label(label: str) -> None:
    text = str(label or "").strip()
    if text:
        _PREVIEW_GROUP_ANCHOR_SKIPPED_LABELS.add(text)


def register_customer_acceptance_group_label(label: str) -> None:
    text = str(label or "").strip()
    if text:
        _CUSTOMER_ACCEPTANCE_GROUP_LABELS.add(text)


class MenuService:
    ROUTE_AUTHORITY_CONTRACT_VERSION = "2.0.0"

    @staticmethod
    def _role_surface_menu_allowed(menu: dict, role_surface: dict | None) -> bool:
        """Apply identifier-based role projection without owning industry semantics."""
        surface = role_surface if isinstance(role_surface, dict) else {}
        meta = menu.get("meta") if isinstance(menu.get("meta"), dict) else {}
        xmlid = str(menu.get("menu_xmlid") or menu.get("xmlid") or meta.get("menu_xmlid") or "").strip().lower()
        action_xmlid = str(menu.get("action_xmlid") or meta.get("action_xmlid") or "").strip().lower()
        model = str(menu.get("model") or meta.get("model") or "").strip().lower()
        blocked_xmlids = {str(item).strip().lower() for item in surface.get("menu_blocklist_xmlids") or [] if str(item).strip()}
        blocked_actions = {str(item).strip().lower() for item in surface.get("action_blocklist_xmlids") or [] if str(item).strip()}
        blocked_models = {str(item).strip().lower() for item in surface.get("model_blocklist") or [] if str(item).strip()}
        blocked_prefixes = tuple(str(item).strip().lower() for item in surface.get("model_prefix_blocklist") or [] if str(item).strip())
        group_key = str(meta.get("group_key") or menu.get("group_key") or menu.get("key") or "").removeprefix("group:").strip().lower()
        blocked_group_keys = {str(item).strip().lower() for item in surface.get("group_key_blocklist") or [] if str(item).strip()}
        return not (
            xmlid in blocked_xmlids
            or action_xmlid in blocked_actions
            or model in blocked_models
            or (model and model.startswith(blocked_prefixes))
            or group_key in blocked_group_keys
        )

    @staticmethod
    def _node_menu_xmlid(node: dict) -> str:
        meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
        return str(node.get("menu_xmlid") or node.get("xmlid") or meta.get("menu_xmlid") or "").strip().lower()

    @classmethod
    def _exposed_menu_xmlids(cls, role_surface: dict | None) -> set[str]:
        surface = role_surface if isinstance(role_surface, dict) else {}
        if not surface.get("exposure_policy_declared"):
            return set()
        exposed = {
            str(item).strip().lower()
            for field in ("primary_menu_xmlids", "role_home_menu_xmlids", "admin_menu_xmlids")
            for item in surface.get(field) or []
            if str(item).strip()
        }
        denied = {
            str(item).strip().lower()
            for item in surface.get("denied_menu_xmlids") or []
            if str(item).strip()
        }
        return exposed - denied

    @staticmethod
    def _discovers_installed_capabilities(role_surface: dict | None) -> bool:
        surface = role_surface if isinstance(role_surface, dict) else {}
        return bool(surface.get("discover_installed_capabilities"))

    @classmethod
    def _filter_primary_native_nodes(cls, nodes: list[dict], role_surface: dict | None) -> list[dict]:
        """Intersect native ACL-visible facts with an explicit P1 exposure policy."""
        exposed = cls._exposed_menu_xmlids(role_surface)
        discovers_capabilities = cls._discovers_installed_capabilities(role_surface)
        if (not exposed and not discovers_capabilities) or (
            isinstance(role_surface, dict) and role_surface.get("deny_all_navigation")
        ):
            return []

        def walk(node: dict):
            if not isinstance(node, dict) or not cls._role_surface_menu_allowed(node, role_surface):
                return None
            xmlid = cls._node_menu_xmlid(node)
            children = [kept for child in node.get("children") or [] if (kept := walk(child))]
            # A cleaned adapter may emit a synthetic grouping ancestor without
            # an XML-ID.  It can carry already-authorized children, but can
            # never become an independently authorized route leaf.
            if not xmlid and not children:
                return None
            if not discovers_capabilities and xmlid not in exposed and not children:
                return None
            candidate = dict(node)
            candidate["children"] = children
            return candidate

        return [kept for node in nodes or [] if (kept := walk(node))]

    @classmethod
    def _filter_primary_delivery_nodes(cls, nodes: list[dict], role_surface: dict | None) -> list[dict]:
        """Keep only declared leaves while allowing synthetic grouping ancestors."""
        exposed = cls._exposed_menu_xmlids(role_surface)
        discovers_capabilities = cls._discovers_installed_capabilities(role_surface)
        if not exposed and not discovers_capabilities:
            return []

        def walk(node: dict):
            if not isinstance(node, dict) or not cls._role_surface_menu_allowed(node, role_surface):
                return None
            children = [kept for child in node.get("children") or [] if (kept := walk(child))]
            xmlid = cls._node_menu_xmlid(node)
            if not children and not discovers_capabilities and xmlid not in exposed:
                return None
            candidate = dict(node)
            candidate["children"] = children
            return candidate

        return [kept for node in nodes or [] if (kept := walk(node))]

    @classmethod
    def _menu_fact_tree_as_native(cls, nodes: list[dict]) -> list[dict]:
        projected = []
        for fact in nodes or []:
            if not isinstance(fact, dict):
                continue
            menu_id = fact.get("menu_id")
            menu_xmlid = str(fact.get("menu_xmlid") or "").strip()
            action_id = fact.get("action_id")
            action_meta = fact.get("action_meta") if isinstance(fact.get("action_meta"), dict) else {}
            model = str(action_meta.get("res_model") or "").strip()
            view_modes = [
                item.strip()
                for item in str(action_meta.get("view_mode") or "").split(",")
                if item.strip()
            ]
            route = f"/a/{action_id}?menu_id={menu_id}" if action_id and menu_id else (f"/m/{menu_id}" if menu_id else "")
            meta = {
                "menu_id": menu_id,
                "menu_xmlid": menu_xmlid,
                "action_id": action_id,
                "model": model,
                "view_modes": view_modes,
                "route": route,
            }
            meta = {key: value for key, value in meta.items() if value not in (None, "", [])}
            projected.append({
                "key": f"menu:{menu_id}",
                "label": str(fact.get("name") or "").strip(),
                "menu_id": menu_id,
                "menu_xmlid": menu_xmlid,
                "xmlid": menu_xmlid,
                "action_id": action_id,
                "model": model,
                "view_modes": view_modes,
                "route": route,
                "sequence": fact.get("sequence"),
                "meta": meta,
                "children": cls._menu_fact_tree_as_native(fact.get("children") or []),
            })
        return projected

    def _authorization_native_nav(self, role_surface: dict | None, native_nav: list[dict]) -> list[dict]:
        surface = role_surface if isinstance(role_surface, dict) else {}
        if (
            not surface.get("exposure_policy_declared")
            or self.env is None
            or self._discovers_installed_capabilities(surface)
        ):
            return native_nav
        # The role policy must intersect the actual request user's Odoo menu
        # visibility. app.menu.config is a delivery/config projection and can
        # legitimately be empty; it is not an authorization authority.
        facts = MenuFactService(self.env).export_visible_menu_facts()
        return self._menu_fact_tree_as_native(facts.tree)

    def build_contextual_routes(self, role_surface: dict | None) -> list[dict]:
        surface = role_surface if isinstance(role_surface, dict) else {}
        if self.env is None or not surface.get("exposure_policy_declared"):
            return []
        denied = {str(item).strip().lower() for item in surface.get("denied_menu_xmlids") or [] if str(item).strip()}
        declared = [
            str(item).strip()
            for item in surface.get("contextual_menu_xmlids") or []
            if str(item).strip() and str(item).strip().lower() not in denied
        ]
        facts = MenuFactService(self.env).export_visible_menu_facts()
        by_xmlid = {
            str(row.get("menu_xmlid") or "").strip(): row
            for row in facts.flat
            if isinstance(row, dict) and str(row.get("menu_xmlid") or "").strip()
        }
        routes = []
        for xmlid in declared:
            row = by_xmlid.get(xmlid)
            if not row or not row.get("action_exists"):
                continue
            menu_id = row.get("menu_id")
            action_id = row.get("action_id")
            if not isinstance(menu_id, int) or menu_id <= 0 or not isinstance(action_id, int) or action_id <= 0:
                continue
            action_meta = row.get("action_meta") if isinstance(row.get("action_meta"), dict) else {}
            view_modes = [
                item.strip()
                for item in str(action_meta.get("view_mode") or "").split(",")
                if item.strip()
            ]
            routes.append({
                "menu_id": menu_id,
                "menu_xmlid": xmlid,
                "action_id": action_id,
                "name": str(row.get("name") or "").strip(),
                "model": str(action_meta.get("res_model") or "").strip(),
                "view_modes": view_modes,
                "view_id": action_meta.get("view_id"),
                "domain": str(action_meta.get("domain") or "").strip(),
                "context": str(action_meta.get("context") or "").strip(),
                "route": f"/a/{action_id}?menu_id={menu_id}",
            })
        return routes

    @staticmethod
    def _record_xmlid(record) -> str:
        if not record:
            return ""
        try:
            return str(record.get_external_id().get(record.id) or "").strip()
        except Exception:
            return ""

    def _action_is_runtime_allowed(self, action, allowed_operation: str) -> bool:
        if not action or not bool(getattr(action, "active", True)):
            return False
        # Role authority is declared by stable XML-ID in the role surface. For
        # menu-backed entries, Odoo menu visibility has already intersected
        # the current user's groups. Action groups are metadata used by the
        # native client and are not enforced by ui.contract.v2; model ACL is
        # the backend execution boundary and must agree with the declaration.
        action_model = str(getattr(action, "_name", "") or "").strip()
        # Product navigation never promotes Odoo Web Client actions into the
        # contract-driven runtime. Client actions remain native-Odoo-only;
        # product routes require a model-backed authority below.
        if action_model == "ir.actions.client":
            return False
        model_name = str(getattr(action, "res_model", "") or "").strip()
        if not model_name and action_model == "ir.actions.server":
            # ir.model is configuration metadata. Read only the declared model
            # name with sudo, then enforce that model's ACL in the request
            # user's environment below; sudo never decides route success.
            metadata_action = action.sudo()
            model_name = str(getattr(getattr(metadata_action, "model_id", None), "model", "") or "").strip()
        if not model_name or model_name not in self.env:
            return False
        operation = str(allowed_operation or "read").strip().lower() or "read"
        try:
            return bool(self.env[model_name].check_access_rights(operation, raise_exception=False))
        except Exception:
            return False

    def _policy_target_is_runtime_allowed(self, menu: dict, allowed_operation: str = "read") -> bool:
        """Authorize a released target without treating its menu carrier as product policy."""
        if self.env is None or not isinstance(menu, dict):
            return False
        menu_xmlid = str(menu.get("menu_xmlid") or "").strip()
        menu_record = self.env.ref(menu_xmlid, raise_if_not_found=False) if menu_xmlid else None
        if menu_record and str(getattr(menu_record, "_name", "") or "") == "ir.ui.menu":
            # Active menus must still be authorized by the request user's
            # native visible-menu facts, including their ancestor chain.
            if bool(getattr(menu_record, "active", True)):
                return False
            menu_groups = getattr(menu_record.sudo(), "groups_id", self.env["res.groups"])
            if menu_groups and not bool(menu_groups & self.env.user.groups_id):
                return False
        else:
            menu_record = None

        action_xmlid = str(menu.get("action_xmlid") or "").strip()
        action = self.env.ref(action_xmlid, raise_if_not_found=False) if action_xmlid else None
        if not action and menu_record:
            action = menu_record.sudo().action
        action_id = self._positive_int(menu.get("action_id"))
        if not action and action_id:
            action = self.env["ir.actions.actions"].sudo().browse(action_id).exists()
        if not action:
            return False
        action_groups = getattr(action.sudo(), "groups_id", self.env["res.groups"])
        if action_groups and not bool(action_groups & self.env.user.groups_id):
            return False
        return self._action_is_runtime_allowed(action, allowed_operation)

    def _route_entry_from_menu(self, row: dict, *, route_kind: str, source: str) -> dict | None:
        if not isinstance(row, dict) or not row.get("action_exists"):
            return None
        menu_id = row.get("menu_id")
        action_id = row.get("action_id")
        if not isinstance(menu_id, int) or menu_id <= 0 or not isinstance(action_id, int) or action_id <= 0:
            return None
        action_model = str(row.get("action_model") or "").strip()
        # The menu fact has already intersected current-user menu visibility.
        # Read only native action metadata with sudo; product route admission
        # and model ACL remain current-user decisions below.
        action = self.env[action_model].sudo().browse(action_id).exists() if action_model in self.env else None
        if not action or not self._action_is_runtime_allowed(action, "read"):
            return None
        action_meta = row.get("action_meta") if isinstance(row.get("action_meta"), dict) else {}
        model_name = str(action_meta.get("res_model") or "").strip()
        if not model_name and str(getattr(action, "_name", "") or "") == "ir.actions.server":
            metadata_action = action.sudo()
            model_name = str(getattr(getattr(metadata_action, "model_id", None), "model", "") or "").strip()
        view_modes = [item.strip() for item in str(action_meta.get("view_mode") or "").split(",") if item.strip()]
        return {
            "action_xmlid": self._record_xmlid(action),
            "route_kind": route_kind,
            "menu_id": menu_id,
            "menu_xmlid": str(row.get("menu_xmlid") or "").strip(),
            "action_id": action_id,
            "name": str(row.get("name") or "").strip(),
            "model": model_name,
            "view_modes": view_modes,
            "view_id": action_meta.get("view_id"),
            "domain": str(action_meta.get("domain") or "").strip(),
            "context": str(action_meta.get("context") or "").strip(),
            "route": f"/a/{action_id}?menu_id={menu_id}",
            "allowed_operation": "read",
            "required_capability": "menu_action_read",
            "context_requirements": {},
            "source": source,
        }

    def _route_entry_from_action_spec(self, spec: dict, *, route_kind: str) -> dict | None:
        row = spec if isinstance(spec, dict) else {}
        action_xmlid = str(row.get("action_xmlid") or "").strip()
        action = self.env.ref(action_xmlid, raise_if_not_found=False) if action_xmlid else None
        if not action or str(getattr(action, "_name", "") or "") != "ir.actions.act_window":
            return None
        allowed_operation = str(row.get("allowed_operation") or "read").strip().lower() or "read"
        if not self._action_is_runtime_allowed(action, allowed_operation):
            return None
        menu_xmlid = str(row.get("menu_xmlid") or "").strip()
        menu = self.env.ref(menu_xmlid, raise_if_not_found=False) if menu_xmlid else None
        menu_id = self._positive_int(row.get("menu_id")) or (
            int(menu.id) if menu and str(getattr(menu, "_name", "")) == "ir.ui.menu" else 0
        )
        view_modes = [item.strip() for item in str(action.view_mode or "").split(",") if item.strip()]
        return {
            "action_xmlid": action_xmlid,
            "route_kind": route_kind,
            "menu_id": menu_id,
            "menu_xmlid": menu_xmlid if menu_id else "",
            "action_id": int(action.id),
            "name": str(action.name or "").strip(),
            "model": str(action.res_model or "").strip(),
            "view_modes": view_modes,
            "view_id": int(action.view_id.id) if action.view_id else None,
            "domain": str(action.domain or "").strip(),
            "context": str(action.context or "").strip(),
            "route": f"/a/{int(action.id)}" + (f"?menu_id={menu_id}" if menu_id else ""),
            "allowed_operation": allowed_operation,
            "required_capability": str(row.get("required_capability") or "").strip(),
            "context_requirements": dict(row.get("context_requirements") or {}),
            "source": str(row.get("source") or "role_surface.route_authority").strip(),
        }

    def _denied_route_entry(self, menu_xmlid: str) -> dict | None:
        xmlid = str(menu_xmlid or "").strip()
        menu = self.env.ref(xmlid, raise_if_not_found=False) if xmlid else None
        action = menu.action if menu and str(getattr(menu, "_name", "")) == "ir.ui.menu" else None
        if not action or str(getattr(action, "_name", "")) != "ir.actions.act_window":
            return None
        action_xmlid = self._record_xmlid(action)
        if not action_xmlid:
            return None
        return {
            "action_xmlid": action_xmlid,
            "route_kind": "DENIED",
            "menu_id": int(menu.id),
            "menu_xmlid": xmlid,
            "action_id": int(action.id),
            "name": str(action.name or "").strip(),
            "model": str(action.res_model or "").strip(),
            "view_modes": [item.strip() for item in str(action.view_mode or "").split(",") if item.strip()],
            "route": f"/a/{int(action.id)}?menu_id={int(menu.id)}",
            "allowed_operation": "none",
            "required_capability": "product_denied",
            "context_requirements": {},
            "source": "role_surface.denied_menu_xmlids",
        }

    @staticmethod
    def _node_route_menu_id(node: dict) -> int:
        """Return the real Odoo menu carrier id, never a synthetic tree id."""
        if not isinstance(node, dict):
            return 0
        meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
        config_ref = (
            node.get("config_ref") if isinstance(node.get("config_ref"), dict)
            else meta.get("config_ref") if isinstance(meta.get("config_ref"), dict)
            else {}
        )
        candidates = (
            node.get("config_menu_id"),
            meta.get("config_menu_id"),
            config_ref.get("id") if str(config_ref.get("model") or "ir.ui.menu") == "ir.ui.menu" else 0,
            0 if bool(node.get("synthetic") or meta.get("synthetic")) else node.get("menu_id"),
            0 if bool(node.get("synthetic") or meta.get("synthetic")) else meta.get("menu_id"),
        )
        for candidate in candidates:
            try:
                menu_id = int(candidate or 0)
            except (TypeError, ValueError):
                menu_id = 0
            if menu_id > 0:
                return menu_id
        return 0

    @staticmethod
    def _walk_nav_action_refs(nodes: list[dict]):
        for node in nodes or []:
            if not isinstance(node, dict):
                continue
            meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
            try:
                menu_id = MenuService._node_route_menu_id(node)
                action_id = int(node.get("action_id") or meta.get("action_id") or 0)
            except (TypeError, ValueError):
                menu_id = action_id = 0
            if action_id > 0:
                yield menu_id, action_id
            yield from MenuService._walk_nav_action_refs(node.get("children") or [])

    @staticmethod
    def _walk_nav_action_specs(nodes: list[dict]):
        for node in nodes or []:
            if not isinstance(node, dict):
                continue
            meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
            try:
                menu_id = MenuService._node_route_menu_id(node)
                action_id = int(node.get("action_id") or meta.get("action_id") or 0)
            except (TypeError, ValueError):
                menu_id = action_id = 0
            if action_id > 0:
                yield {
                    "menu_id": menu_id,
                    "menu_xmlid": str(node.get("menu_xmlid") or meta.get("menu_xmlid") or "").strip(),
                    "action_id": action_id,
                    "action_xmlid": str(node.get("action_xmlid") or meta.get("action_xmlid") or "").strip(),
                    "allowed_operation": "read",
                    "required_capability": str(meta.get("capability_key") or "menu_action_read").strip(),
                    "context_requirements": {},
                    "source": "delivery_engine.released_policy_nav",
                }
            yield from MenuService._walk_nav_action_specs(node.get("children") or [])

    @staticmethod
    def _native_route_discovery_blocked(
        pair: tuple[int, int],
        *,
        existing_pairs: set[tuple[int, int]],
        reserved_pairs: set[tuple[int, int]],
        denied_action_ids: set[int],
    ) -> bool:
        """Keep stable menu identity while preserving action-level denials."""
        return pair in existing_pairs or pair in reserved_pairs or pair[1] in denied_action_ids

    @staticmethod
    def _nav_target_index(nodes: list[dict]) -> dict[tuple[int, int], dict]:
        targets: dict[tuple[int, int], dict] = {}
        for node in nodes or []:
            if not isinstance(node, dict):
                continue
            meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
            try:
                pair = (
                    MenuService._node_route_menu_id(node),
                    int(node.get("action_id") or meta.get("action_id") or 0),
                )
            except (TypeError, ValueError):
                pair = (0, 0)
            if pair[1] > 0:
                entry_target = (
                    node.get("entry_target") if isinstance(node.get("entry_target"), dict)
                    else meta.get("entry_target") if isinstance(meta.get("entry_target"), dict)
                    else {}
                )
                scene_key = str(node.get("scene_key") or meta.get("scene_key") or entry_target.get("scene_key") or "").strip()
                route = str(node.get("route") or meta.get("route") or entry_target.get("route") or "").strip()
                targets[pair] = {"scene_key": scene_key, "route": route, "entry_target": entry_target}
            targets.update(MenuService._nav_target_index(node.get("children") or []))
        return targets

    @staticmethod
    def filter_nav_by_route_authority(nav: list[dict], route_authority: dict | None) -> list[dict]:
        """Keep action-bearing navigation only when this payload authorizes it."""
        authority = route_authority if isinstance(route_authority, dict) else {}
        allowed_pairs = {
            (int(row.get("menu_id") or 0), int(row.get("action_id") or 0))
            for bucket in ("primary_actions", "role_home_actions", "contextual_actions", "admin_actions")
            for row in authority.get(bucket) or []
            if isinstance(row, dict)
        }

        def as_directory_container(node: dict, children: list[dict]) -> dict:
            """Preserve an authorized subtree without exposing its denied parent target."""
            target_keys = {
                "action",
                "action_id",
                "actionId",
                "action_xmlid",
                "active_match",
                "entry_target",
                "model",
                "native_action_id",
                "native_model",
                "native_view_mode",
                "res_model",
                "route",
                "scene_key",
                "sceneKey",
                "target",
            }
            candidate = {key: value for key, value in node.items() if key not in target_keys}
            meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
            candidate["meta"] = {key: value for key, value in meta.items() if key not in target_keys}
            candidate.update({
                "children": children,
                "target_type": "directory",
                "delivery_mode": "none",
                "is_clickable": False,
                "availability_status": "ok",
                "reason_code": "DIRECTORY_ONLY",
            })
            return candidate

        def walk(node: dict):
            if not isinstance(node, dict):
                return None
            meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
            entry_target = (
                node.get("entry_target")
                if isinstance(node.get("entry_target"), dict)
                else meta.get("entry_target")
                if isinstance(meta.get("entry_target"), dict)
                else {}
            )
            try:
                menu_id = MenuService._node_route_menu_id(node)
                action_id = int(node.get("action_id") or meta.get("action_id") or 0)
            except (TypeError, ValueError):
                menu_id = action_id = 0
            children = [kept for child in node.get("children") or [] if (kept := walk(child))]
            # The SPA freezes every menu click into one menu/action/authority
            # tuple before choosing an action or scene target.  A scene_key
            # therefore cannot make an otherwise unauthorized action carrier
            # executable.  An independently authorized child remains valid,
            # so a denied parent target becomes a directory rather than
            # deleting the authorized subtree.
            if action_id > 0 and (menu_id, action_id) not in allowed_pairs:
                return as_directory_container(node, children) if children else None
            candidate = dict(node)
            candidate["children"] = children
            has_route = bool(
                str(node.get("route") or meta.get("route") or entry_target.get("route") or "").strip()
            )
            if not has_route and not children and action_id <= 0:
                return None
            return candidate

        return [kept for node in nav or [] if (kept := walk(node))]

    @staticmethod
    def project_canonical_navigation(nav: list[dict], route_authority: dict | None) -> list[dict]:
        """Attach the server-owned presentation identity to the final authorized tree."""
        authority = route_authority if isinstance(route_authority, dict) else {}
        authority_by_pair = {}
        for bucket in ("primary_actions", "role_home_actions", "contextual_actions", "admin_actions"):
            for entry in authority.get(bucket) or []:
                if not isinstance(entry, dict):
                    continue
                try:
                    pair = (int(entry.get("menu_id") or 0), int(entry.get("action_id") or 0))
                except (TypeError, ValueError):
                    pair = (0, 0)
                if pair[0] > 0 and pair[1] > 0:
                    authority_by_pair[pair] = entry

        def text(value) -> str:
            return str(value or "").strip()

        def node_label(node: dict) -> str:
            return text(node.get("title") or node.get("label") or node.get("name"))

        def node_key(node: dict, menu_id: int) -> str:
            return text(node.get("xmlid") or node.get("xml_id") or node.get("key")) or (
                "menu_%s" % menu_id if menu_id > 0 else ""
            )

        def walk(node: dict, parents: list[dict], sibling_index: int) -> dict:
            if not isinstance(node, dict):
                raise ValueError("canonical navigation node must be an object")
            meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
            menu_id = MenuService._node_route_menu_id(node)
            try:
                action_id = int(node.get("action_id") or meta.get("action_id") or 0)
            except (TypeError, ValueError):
                action_id = 0
            label = node_label(node)
            key = node_key(node, menu_id)
            if not key or not label or (action_id > 0 and menu_id <= 0):
                raise ValueError("canonical navigation node identity is incomplete")
            entry = authority_by_pair.get((menu_id, action_id)) if action_id > 0 else None
            if action_id > 0 and not entry:
                raise ValueError(
                    "canonical navigation action lacks exact authority: %s/%s" % (menu_id, action_id)
                )

            availability = text(
                node.get("availability_status") or meta.get("availability_status")
                or node.get("state") or meta.get("state")
            ).lower()
            explicitly_disabled = (
                node.get("is_clickable") is False
                or meta.get("is_clickable") is False
                or availability in {"disabled", "blocked", "unavailable", "denied"}
            )
            disabled_reason = text(node.get("disabled_reason") or meta.get("disabled_reason"))
            children = [
                walk(child, parents + [{"key": key, "menu_id": menu_id or None, "label": label}], index)
                for index, child in enumerate(node.get("children") or [])
            ]
            if explicitly_disabled and not disabled_reason:
                raise ValueError("disabled canonical navigation node requires a server reason")
            if action_id <= 0 and not children:
                raise ValueError("canonical navigation node has neither target nor children")

            state = "disabled" if explicitly_disabled else "enabled" if action_id > 0 else "container"
            authority_projection = (
                {
                    "state": "allowed",
                    "source": text(entry.get("source")),
                    "key": ":".join((
                        text(entry.get("route_kind")),
                        text(entry.get("menu_xmlid") or entry.get("menu_id")),
                        text(entry.get("action_xmlid") or entry.get("action_id")),
                    )),
                }
                if entry
                else {
                    "state": "container",
                    "source": "system.init.navigation.nav",
                    "key": "container:%s" % (menu_id or key),
                }
            )
            projected = dict(node)
            projected["children"] = children
            projected["canonical_navigation"] = {
                "schema_version": "1.0",
                "key": key,
                "menu_id": menu_id or None,
                "action_id": action_id or None,
                "parent_chain": list(parents),
                "label": label,
                "icon": text(node.get("icon") or meta.get("icon")) or None,
                "route": text(entry.get("route")) if entry else None,
                "authority": authority_projection,
                "state": state,
                "disabled_reason": disabled_reason or None,
                "order": int(node.get("sequence") or meta.get("sequence") or sibling_index),
            }
            return projected

        return [walk(node, [], index) for index, node in enumerate(nav or [])]

    def build_route_authority(self, role_surface: dict | None, *, nav: list[dict] | None = None) -> dict:
        surface = role_surface if isinstance(role_surface, dict) else {}
        buckets = {
            "primary_actions": [],
            "role_home_actions": [],
            "contextual_actions": [],
            "admin_actions": [],
            "denied_actions": [],
            "menu_containers": [],
        }
        if self.env is None:
            return {
                "contract_version": self.ROUTE_AUTHORITY_CONTRACT_VERSION,
                "schema_version": self.ROUTE_AUTHORITY_CONTRACT_VERSION,
                "source": "delivery_engine.route_authority",
                "principal_scope": {},
                **buckets,
            }
        principal_scope = {
            "user_id": int(self.env.user.id),
            "company_id": int(self.env.company.id),
            "role_code": str(surface.get("role_code") or "").strip(),
        }
        if not surface.get("exposure_policy_declared"):
            return {
                "contract_version": self.ROUTE_AUTHORITY_CONTRACT_VERSION,
                "schema_version": self.ROUTE_AUTHORITY_CONTRACT_VERSION,
                "source": "delivery_engine.route_authority",
                "principal_scope": principal_scope,
                **buckets,
            }

        facts = MenuFactService(self.env).export_visible_menu_facts()
        visible_by_xmlid = {
            str(row.get("menu_xmlid") or "").strip(): row
            for row in facts.flat
            if isinstance(row, dict) and str(row.get("menu_xmlid") or "").strip()
        }
        menu_fields = (
            ("primary_menu_xmlids", "primary_actions", "PRIMARY_NAV"),
            ("role_home_menu_xmlids", "role_home_actions", "ROLE_HOME_ACTION"),
            ("contextual_menu_xmlids", "contextual_actions", "CONTEXTUAL_ROUTE"),
            ("admin_menu_xmlids", "admin_actions", "ADMIN_ROUTE"),
            # Top-level principal containers (e.g. project / contract center)
            # live in role_surface.menu_xmlids. They are directory menus
            # without their own action, so the existing fallback below
            # promotes them to menu_containers with route /m/:menuId so
            # workspace home quick_links that reference them stay navigable.
            ("menu_xmlids", "primary_actions", "PRIMARY_NAV"),
        )
        for field, bucket, route_kind in menu_fields:
            for menu_xmlid in surface.get(field) or []:
                fact = visible_by_xmlid.get(str(menu_xmlid).strip())
                entry = self._route_entry_from_menu(
                    fact,
                    route_kind=route_kind,
                    source=f"role_surface.{field}",
                )
                if entry:
                    buckets[bucket].append(entry)
                elif fact and isinstance(fact.get("menu_id"), int) and fact.get("menu_id") > 0:
                    buckets["menu_containers"].append({
                        "route_kind": route_kind,
                        "menu_id": int(fact["menu_id"]),
                        "menu_xmlid": str(fact.get("menu_xmlid") or "").strip(),
                        "route": f"/m/{int(fact['menu_id'])}",
                        "allowed_operation": "navigate",
                        "required_capability": "menu_container_visible",
                        "context_requirements": {},
                        "source": f"role_surface.{field}",
                    })

        action_fields = (
            ("contextual_action_authorities", "contextual_actions", "CONTEXTUAL_ROUTE"),
            ("admin_action_authorities", "admin_actions", "ADMIN_ROUTE"),
        )
        for field, bucket, route_kind in action_fields:
            for spec in surface.get(field) or []:
                entry = self._route_entry_from_action_spec(spec, route_kind=route_kind)
                if entry:
                    buckets[bucket].append(entry)

        for menu_xmlid in surface.get("denied_menu_xmlids") or []:
            entry = self._denied_route_entry(menu_xmlid)
            if entry:
                buckets["denied_actions"].append(entry)

        if self._discovers_installed_capabilities(surface) and isinstance(nav, list):
            visible_by_pair = {
                (int(row.get("menu_id") or 0), int(row.get("action_id") or 0)): row
                for row in facts.flat
                if isinstance(row, dict)
            }
            reserved_pairs = {
                (int(item.get("menu_id") or 0), int(item.get("action_id") or 0))
                for bucket_name in ("contextual_actions", "admin_actions")
                for item in buckets[bucket_name]
                if isinstance(item, dict)
            }
            denied_action_ids = {
                int(item.get("action_id") or 0)
                for item in buckets["denied_actions"]
                if isinstance(item, dict)
            }
            existing_pairs = {
                (int(item.get("menu_id") or 0), int(item.get("action_id") or 0))
                for bucket_name in ("primary_actions", "role_home_actions")
                for item in buckets[bucket_name]
                if isinstance(item, dict)
            }
            for menu_id, action_id in self._walk_nav_action_refs(nav):
                pair = (menu_id, action_id)
                if self._native_route_discovery_blocked(
                    pair,
                    existing_pairs=existing_pairs,
                    reserved_pairs=reserved_pairs,
                    denied_action_ids=denied_action_ids,
                ):
                    continue
                entry = self._route_entry_from_menu(
                    visible_by_pair.get(pair),
                    route_kind="DISCOVERED_PRIMARY_NAV",
                    source="delivery_engine.nav",
                )
                if entry:
                    buckets["primary_actions"].append(entry)
                    existing_pairs.add(pair)

        # Released product policy may deliberately project an inactive Odoo
        # menu, or an action-only page, into the product navigation. Authorize
        # that exact runtime pair from action/model ACL facts; never revive the
        # native menu tree as a second product-selection authority.
        authorized_pairs = {
            (int(item.get("menu_id") or 0), int(item.get("action_id") or 0))
            for bucket_name in ("primary_actions", "role_home_actions", "contextual_actions", "admin_actions")
            for item in buckets[bucket_name]
            if isinstance(item, dict)
        }
        denied_action_ids = {
            int(item.get("action_id") or 0)
            for item in buckets["denied_actions"]
            if isinstance(item, dict)
        }
        for spec in self._walk_nav_action_specs(nav if isinstance(nav, list) else []):
            pair = (int(spec.get("menu_id") or 0), int(spec.get("action_id") or 0))
            if pair in authorized_pairs or pair[1] in denied_action_ids:
                continue
            if not self._policy_target_is_runtime_allowed(spec):
                continue
            entry = self._route_entry_from_action_spec(spec, route_kind="PRIMARY_NAV")
            if entry:
                buckets["primary_actions"].append(entry)
                authorized_pairs.add(pair)

        nav_targets = self._nav_target_index(nav if isinstance(nav, list) else [])
        for bucket_name in ("primary_actions", "role_home_actions", "contextual_actions", "admin_actions"):
            for entry in buckets[bucket_name]:
                pair = (int(entry.get("menu_id") or 0), int(entry.get("action_id") or 0))
                target = nav_targets.get(pair) or {}
                if target.get("route"):
                    entry["route"] = target["route"]
                if target.get("scene_key"):
                    entry["scene_key"] = target["scene_key"]
                if target.get("entry_target"):
                    entry["entry_target"] = target["entry_target"]

        for bucket_name, bucket in buckets.items():
            deduped = {
                (int(item.get("action_id") or 0), int(item.get("menu_id") or 0)): item
                for item in bucket
            }
            bucket[:] = list(deduped.values())
            bucket.sort(key=lambda item: (str(item.get("action_xmlid") or item.get("menu_xmlid") or ""), int(item.get("menu_id") or 0)))
        return {
            "contract_version": self.ROUTE_AUTHORITY_CONTRACT_VERSION,
            "schema_version": self.ROUTE_AUTHORITY_CONTRACT_VERSION,
            "source": "delivery_engine.route_authority",
            "principal_scope": principal_scope,
            **buckets,
        }

    @classmethod
    def _filter_role_surface_nodes(cls, nodes: list[dict], role_surface: dict | None) -> list[dict]:
        if isinstance(role_surface, dict) and role_surface.get("deny_all_navigation"):
            return []
        filtered = []
        for node in nodes or []:
            if not isinstance(node, dict):
                continue
            if not cls._role_surface_menu_allowed(node, role_surface):
                continue
            children = cls._filter_role_surface_nodes(node.get("children") or [], role_surface)
            candidate = dict(node)
            candidate["children"] = children
            filtered.append(candidate)
        return filtered
    SOURCE_KIND = "delivery_menu_projection"
    SOURCE_AUTHORITIES = ("odoo_menu_fact_projection", "menu_delivery_convergence_projection", "delivery_product_policy_projection")
    NO_BUSINESS_FACT_AUTHORITY = True
    NATIVE_PREVIEW_GROUP_KEY = "native_preview"
    NATIVE_PREVIEW_GROUP_LABEL = "系统菜单"
    BUSINESS_INTENT_BUCKETS = (
        ("handling", "办理入口", 10, {"handling"}),
        ("ledger_query", "台账查询", 20, {"query", "master_data"}),
        ("analysis", "分析报表", 30, {"analysis"}),
        ("source_fact", "来源明细", 40, {"source_fact"}),
        ("config", "配置管理", 50, {"config"}),
    )
    BUSINESS_GROUP_DISPLAY_ORDER = {
        "基础资料": 5,
        "人事行政": 70,
        "资料证照": 80,
        "产品配置": 980,
        "配置中心": 990,
        "配置": 990,
        "系统配置": 990,
    }

    def __init__(self, env=None):
        self.env = env
        self._business_group_display_order = self._resolve_business_group_display_order()

    @staticmethod
    def _canonical_group_label(label: str) -> str:
        normalized = str(label or "").strip()
        return "产品配置" if normalized == "配置中心" else normalized

    def _resolve_business_group_display_order(self) -> dict:
        order = dict(self.BUSINESS_GROUP_DISPLAY_ORDER)
        if self.env is None:
            return order
        hook_payload = call_extension_hook_first(self.env, "smart_core_business_nav_group_display_order", self.env)
        if isinstance(hook_payload, dict):
            for label, sequence in hook_payload.items():
                label = str(label or "").strip()
                if not label:
                    continue
                try:
                    order[label] = int(sequence)
                except Exception:
                    continue
        return order

    @classmethod
    def source_authority_contract(cls) -> dict:
        return build_source_authority_contract(
            kind=cls.SOURCE_KIND,
            authorities=cls.SOURCE_AUTHORITIES,
            no_business_fact_authority=cls.NO_BUSINESS_FACT_AUTHORITY,
            runtime_carrier="delivery_engine.nav",
        )

    def _is_admin_role(self, role_code: str) -> bool:
        normalized = str(role_code or "").strip().lower()
        return normalized in {"admin", "platform_admin", "system_admin", "administrator"}

    def _is_business_config_role(self, role_code: str) -> bool:
        normalized = str(role_code or "").strip().lower()
        return normalized in {"executive", "business_config_admin", "business_admin", "implementation_admin"}

    def _converged_menu(
        self,
        *,
        menu: dict,
        group_label: str,
        role_code: str,
        is_admin: bool = False,
        is_business_config_admin: bool = False,
    ):
        row = dict(menu or {})
        label = str(row.get("label") or "").strip()
        if not label:
            return None
        if row.get("native_preview"):
            row["delivery_bucket"] = "native_preview"
            row["source_authority"] = self.source_authority_contract()
            return row
        if str(row.get("scene_source") or "").strip() == "native_business_config_menu_projection":
            row["delivery_bucket"] = "delivery_business_config"
            row["source_authority"] = self.source_authority_contract()
            return row
        service = MenuDeliveryConvergenceService(self.env)
        category = service._classify_leaf(
            label,
            [group_label, label],
            is_admin=bool(is_admin) or self._is_admin_role(role_code),
            is_business_config_admin=bool(is_business_config_admin) or self._is_business_config_role(role_code),
        )
        if category.startswith("hidden_"):
            return None
        renamed = service.rename_labels.get(label)
        if renamed:
            row["label"] = renamed
        row["delivery_bucket"] = category
        row["source_authority"] = self.source_authority_contract()
        return row

    def _node_has_target(self, node: dict) -> bool:
        meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
        return bool(
            node.get("route")
            or node.get("scene_key")
            or node.get("action_id")
            or node.get("model")
            or meta.get("route")
            or meta.get("scene_key")
            or meta.get("action_id")
            or meta.get("model")
        )

    def _merge_explicit_entry_with_directory(self, nodes: list[dict]) -> list[dict]:
        """Merge one native action entry into its same-menu policy directory."""
        normalized = []
        for node in nodes or []:
            if not isinstance(node, dict):
                continue
            next_node = dict(node)
            children = next_node.get("children") if isinstance(next_node.get("children"), list) else []
            next_node["children"] = self._merge_explicit_entry_with_directory(children)
            normalized.append(next_node)

        removed = set()
        for directory_index, directory in enumerate(normalized):
            children = directory.get("children") if isinstance(directory.get("children"), list) else []
            if not children:
                continue
            directory_meta = directory.get("meta") if isinstance(directory.get("meta"), dict) else {}
            config_menu_id = self._positive_int(
                directory.get("config_menu_id") or directory_meta.get("config_menu_id")
            )
            label = str(directory.get("label") or "").strip()
            explicit_path_group = bool(directory_meta.get("explicit_menu_path_group"))
            if not label or (not config_menu_id and not explicit_path_group):
                continue
            entry_indexes = [
                index
                for index, entry in enumerate(normalized)
                if index != directory_index
                and index not in removed
                and str(entry.get("label") or "").strip() == label
                and not (entry.get("children") if isinstance(entry.get("children"), list) else [])
                and (not config_menu_id or self._positive_int(entry.get("menu_id")) == config_menu_id)
                and self._node_has_target(entry)
            ]
            if len(entry_indexes) != 1:
                continue
            entry_index = entry_indexes[0]
            entry = normalized[entry_index]
            entry_meta = entry.get("meta") if isinstance(entry.get("meta"), dict) else {}
            config_menu_id = config_menu_id or self._positive_int(entry.get("menu_id"))
            if not config_menu_id:
                continue
            merged_meta = dict(directory_meta)
            merged_meta["explicit_group_entry_target"] = True
            merged_meta["merged_native_entry_key"] = str(entry.get("key") or "")
            directory["menu_id"] = config_menu_id
            for field in (
                "route", "scene_key", "action_id", "action_xmlid", "model",
                "view_modes", "entry_target",
            ):
                value = entry.get(field) if entry.get(field) not in (None, "", []) else entry_meta.get(field)
                if value not in (None, "", []):
                    directory[field] = value
                    merged_meta[field] = value
            directory["meta"] = merged_meta
            removed.add(entry_index)
        return [node for index, node in enumerate(normalized) if index not in removed]

    def _iter_leaf_nodes(self, nodes, ancestors=None):
        parent_chain = list(ancestors or [])
        for node in nodes or []:
            if not isinstance(node, dict):
                continue
            children = node.get("children") if isinstance(node.get("children"), list) else []
            if children:
                yield from self._iter_leaf_nodes(children, parent_chain + [node])
                continue
            yield parent_chain, node

    def _iter_declared_entry_nodes(self, nodes, entry_xmlids: set[str], ancestors=None):
        parent_chain = list(ancestors or [])
        for node in nodes or []:
            if not isinstance(node, dict):
                continue
            xmlid = self._node_menu_xmlid(node)
            if xmlid in entry_xmlids and self._node_has_target(node):
                yield parent_chain, node
            children = node.get("children") if isinstance(node.get("children"), list) else []
            if children:
                yield from self._iter_declared_entry_nodes(children, entry_xmlids, parent_chain + [node])

    def _resolve_preview_group_anchor(self, ancestors: list[dict]) -> tuple[str, str, int]:
        skipped_labels = _PREVIEW_GROUP_ANCHOR_SKIPPED_LABELS
        business_root_xmlid = ""
        if self.env is not None:
            business_root_xmlid = str(
                call_extension_hook_first(self.env, "smart_core_business_root_menu_xmlid", self.env) or ""
            ).strip().lower()

        def is_root_ancestor(ancestor: dict) -> bool:
            key = str(ancestor.get("key") or "").strip()
            xmlid = self._node_menu_xmlid(ancestor)
            return key.startswith("root:") or bool(business_root_xmlid and xmlid == business_root_xmlid)

        for ancestor in ancestors or []:
            if not isinstance(ancestor, dict):
                continue
            if is_root_ancestor(ancestor):
                continue
            label = str(ancestor.get("label") or ancestor.get("title") or ancestor.get("name") or "").strip()
            if label in skipped_labels:
                continue
            menu_id = ancestor.get("menu_id")
            if (isinstance(menu_id, int) and menu_id > 0) and label:
                return f"menu_{menu_id}", label, int(menu_id)
        for ancestor in ancestors or []:
            if not isinstance(ancestor, dict):
                continue
            if is_root_ancestor(ancestor):
                continue
            label = str(ancestor.get("label") or ancestor.get("title") or ancestor.get("name") or "").strip()
            if label in skipped_labels:
                continue
            if label:
                key = str(ancestor.get("key") or "").strip().replace(":", "_") or "ungrouped"
                return key, label, 0
        return "ungrouped", "业务菜单", 0

    def _menu_dedupe_key(self, row: dict) -> str:
        menu_id = row.get("menu_id")
        if isinstance(menu_id, int) and menu_id > 0:
            return f"menu_id:{menu_id}"
        scene_key = str(row.get("scene_key") or "").strip()
        if scene_key:
            return f"scene:{scene_key}"
        route = str(row.get("route") or "").strip()
        if route:
            return f"route:{route}"
        menu_xmlid = str(row.get("menu_xmlid") or "").strip()
        if menu_xmlid:
            return f"xmlid:{menu_xmlid}"
        return f"label:{str(row.get('label') or '').strip()}"

    def _positive_int(self, value) -> int:
        try:
            number = int(value or 0)
        except Exception:
            return 0
        return number if number > 0 else 0

    def _node_sequence(self, node: dict) -> int:
        sequence = self._positive_int(node.get("sequence"))
        if sequence:
            return sequence
        meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
        sequence = self._positive_int(meta.get("sequence"))
        if sequence:
            return sequence
        child_sequences = [
            self._node_sequence(child)
            for child in (node.get("children") if isinstance(node.get("children"), list) else [])
            if isinstance(child, dict) and self._node_sequence(child) > 0
        ]
        return min(child_sequences) if child_sequences else 0

    def _node_followup_rank(self, node: dict) -> int:
        """Keep policy-declared follow-up entries behind released siblings."""
        meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
        domain = str(meta.get("product_domain") or node.get("product_domain") or "").strip().lower()
        domain_label = str(
            meta.get("product_domain_label") or node.get("product_domain_label") or ""
        ).strip()
        if domain_label == "后续上线" or domain.endswith("_roadmap"):
            return 1
        children = node.get("children") if isinstance(node.get("children"), list) else []
        if children and all(self._node_followup_rank(child) == 1 for child in children if isinstance(child, dict)):
            return 1
        return 0

    def _sort_delivery_nodes(self, nodes: list[dict], *, top_level: bool = False) -> list[dict]:
        decorated = []
        for index, node in enumerate(nodes or []):
            if not isinstance(node, dict):
                continue
            next_node = dict(node)
            children = next_node.get("children") if isinstance(next_node.get("children"), list) else []
            if children:
                next_node["children"] = self._sort_delivery_nodes(children, top_level=False)
            decorated.append((index, next_node))

        def sort_key(item):
            index, node = item
            label = str(node.get("label") or node.get("title") or "").strip()
            if top_level:
                group_rank = self._business_group_display_order.get(label, 500)
                return (group_rank, self._node_sequence(node) or 9999, index)
            return (self._node_followup_rank(node), self._node_sequence(node) or 9999, index)

        return [node for _index, node in sorted(decorated, key=sort_key)]

    def _policy_has_menu_surface(self, policy: dict) -> bool:
        for group in policy.get("menu_groups") or []:
            if not isinstance(group, dict):
                continue
            for menu in group.get("menus") or []:
                if isinstance(menu, dict) and str(menu.get("label") or "").strip():
                    return True
        return False

    def _policy_is_customer_acceptance_focus(self, policy: dict) -> bool:
        for group in policy.get("menu_groups") or []:
            if not isinstance(group, dict):
                continue
            group_key = str(group.get("group_key") or "").strip()
            category = str(group.get("category") or "").strip()
            if group_key.startswith("catalog.acceptance.") or category.startswith("customer_acceptance_"):
                return True
        return False

    def _release_menu_enabled(self, menu: dict) -> bool:
        if not isinstance(menu, dict):
            return False
        if menu.get("enabled") is False:
            return False
        release_state = str(menu.get("release_state") or "released").strip().lower() or "released"
        return release_state in {"released", "preview", "stable", "public"}

    def _native_authorized_menu_index(self, native_nav: list[dict]) -> dict[str, set]:
        index = {"ids": set(), "xmlids": set(), "scenes": set(), "routes": set()}
        def visit(nodes):
            for node in nodes or []:
                if not isinstance(node, dict):
                    continue
                yield node
                children = node.get("children") if isinstance(node.get("children"), list) else []
                yield from visit(children)

        # Policy entries may legitimately target a visible parent action/menu,
        # not only a leaf.  Index every user-visible native node so the policy
        # intersection does not discard valid entries before parent-chain
        # reconstruction.  The native tree is already built under the real
        # request user, so this remains an authorization check rather than a
        # sudo-derived catalog lookup.
        for leaf in visit(native_nav or []):
            if not isinstance(leaf, dict):
                continue
            meta = leaf.get("meta") if isinstance(leaf.get("meta"), dict) else {}
            menu_id = leaf.get("menu_id") or meta.get("menu_id")
            try:
                menu_id_int = int(menu_id or 0)
            except Exception:
                menu_id_int = 0
            if menu_id_int > 0:
                index["ids"].add(menu_id_int)
            menu_xmlid = str(meta.get("menu_xmlid") or leaf.get("menu_xmlid") or "").strip()
            if menu_xmlid:
                index["xmlids"].add(menu_xmlid)
            scene_key = str(leaf.get("scene_key") or meta.get("scene_key") or "").strip()
            if scene_key:
                index["scenes"].add(scene_key)
            route = str(leaf.get("route") or meta.get("route") or "").strip()
            if route:
                index["routes"].add(route)
        return index

    def _policy_menu_user_authorized(
        self,
        menu: dict,
        native_index: dict[str, set],
        *,
        is_admin: bool = False,
        is_business_config_admin: bool = False,
    ) -> bool:
        if is_admin or is_business_config_admin:
            return True
        menu_xmlid = str(menu.get("menu_xmlid") or "").strip()
        if menu_xmlid and menu_xmlid in native_index.get("xmlids", set()):
            return True
        menu_id = menu.get("menu_id")
        try:
            menu_id_int = int(menu_id or 0)
        except Exception:
            menu_id_int = 0
        if menu_id_int > 0 and menu_id_int in native_index.get("ids", set()):
            return True
        scene_key = str(menu.get("scene_key") or "").strip()
        if scene_key and scene_key in native_index.get("scenes", set()):
            return True
        route = str(menu.get("route") or "").strip()
        if route and route in native_index.get("routes", set()):
            return True
        return self._policy_target_is_runtime_allowed(menu)

    def _flatten_policy_menus(self, policy: dict) -> list[dict]:
        out = []
        index = 0
        productization_keys = (
            "product_domain",
            "product_domain_label",
            "entry_intent",
            "entry_intent_label",
            "fact_model",
            "disposition_policy",
            "integration_target",
            "default_business_category_code",
            "allowed_business_category_codes",
            "required_relationships",
            "locked_data_policy",
            "productization_source",
            "business_entry_contract_version",
            "entry_target_policy",
            "integration_action_id",
            "integration_action_xmlid",
            "integration_view_modes",
            "integration_entry_target",
            "integration_model",
            "record_scope_policy",
            "project_scope_policy",
        )
        for group in policy.get("menu_groups") or []:
            if not isinstance(group, dict):
                continue
            for menu in group.get("menus") or []:
                if not isinstance(menu, dict):
                    continue
                if not self._release_menu_enabled(menu):
                    continue
                index += 1
                scene_key = str(menu.get("scene_key") or "").strip()
                menu_id = menu.get("menu_id")
                route = str(menu.get("route") or "").strip()
                action_id = menu.get("action_id")
                menu_xmlid = str(menu.get("menu_xmlid") or "").strip()
                native_visible_menu_path = self._native_visible_menu_path(menu_xmlid)
                if route.startswith("/a/") and scene_key == menu_xmlid:
                    scene_key = ""
                raw_anchor = scene_key or (str(menu_id) if isinstance(menu_id, int) and menu_id > 0 else str(menu.get("menu_key") or "").strip() or str(index))
                sanitized_anchor = raw_anchor.replace(":", "_").replace("/", "_").replace(".", "_")
                model = str(menu.get("model") or menu.get("res_model") or "").strip()
                if not action_id and not model and not scene_key and not route:
                    continue
                row = {
                    "menu_key": f"system.policy.{sanitized_anchor}",
                    "label": str(menu.get("label") or "").strip(),
                    "menu_id": menu_id,
                    "route": route,
                    "scene_key": scene_key,
                    "product_key": str(menu.get("product_key") or "").strip(),
                    "capability_key": str(menu.get("capability_key") or "").strip(),
                    "menu_xmlid": menu_xmlid,
                    "action_id": action_id,
                    "action_xmlid": str(menu.get("action_xmlid") or "").strip(),
                    "model": model,
                    "view_modes": menu.get("view_modes") if isinstance(menu.get("view_modes"), list) else [],
                    "sequence": self._positive_int(menu.get("sequence")),
                    "scene_source": "delivery_policy",
                    "policy_group_key": str(group.get("group_key") or "").strip(),
                    "policy_group_label": str(group.get("group_label") or "").strip(),
                    "visible_menu_path": str(menu.get("visible_menu_path") or "").strip(),
                    "native_visible_menu_path": native_visible_menu_path,
                    "entry_target": menu.get("entry_target") if isinstance(menu.get("entry_target"), dict) else {},
                }
                for key in productization_keys:
                    value = menu.get(key)
                    if value not in (None, "", []):
                        row[key] = value
                out.append(row)
        return [row for row in out if row.get("menu_key") and row.get("label")]

    def _native_visible_menu_path(self, menu_xmlid: str) -> str:
        """Return the installed menu ancestry as the runtime path authority."""
        if self.env is None or not menu_xmlid or not hasattr(self.env, "ref"):
            return ""
        try:
            menu = self.env.ref(menu_xmlid, raise_if_not_found=False)
        except TypeError:
            try:
                menu = self.env.ref(menu_xmlid)
            except Exception:
                return ""
        except Exception:
            return ""
        if not menu or getattr(menu, "_name", "") != "ir.ui.menu":
            return ""
        complete_name = str(getattr(menu, "complete_name", "") or "").strip()
        return " / ".join(part.strip() for part in complete_name.split("/") if part.strip())

    def _policy_menu_path_parts(self, menu: dict) -> list[str]:
        path = str(menu.get("visible_menu_path") or "").strip()
        if not path:
            return []
        return [
            self._canonical_group_label(part)
            for part in re.split(r"\s+/\s+", path)
            if part.strip()
        ]

    def _acceptance_menu_group_parts(self, menu: dict, group_label: str) -> list[str]:
        parts = self._policy_menu_path_parts(menu)
        for index, part in enumerate(parts):
            if part == group_label:
                return [item for item in parts[index + 1 : -1] if item and item != group_label]
        return []

    def _append_policy_path_child(
        self,
        *,
        nodes: list[dict],
        parent_key: str,
        group_label: str,
        menu: dict,
        child: dict,
        group_config_menu_ids_by_label: dict[str, int] | None = None,
    ) -> None:
        group_parts = self._acceptance_menu_group_parts(menu, group_label)
        if not group_parts:
            nodes.append(child)
            return
        self._append_acceptance_child(
            nodes=nodes,
            parent_key=parent_key,
            group_parts=group_parts,
            child=child,
            group_config_menu_ids_by_label=group_config_menu_ids_by_label,
        )

    def _acceptance_group_key(self, parent_key: str, label: str, index: int) -> str:
        safe = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", str(label or "").strip()).strip("_")
        return f"{parent_key}.{safe or index}"

    def _append_acceptance_child(
        self,
        *,
        nodes: list[dict],
        parent_key: str,
        group_parts: list[str],
        child: dict,
        group_config_menu_ids_by_label: dict[str, int] | None = None,
    ) -> None:
        if not group_parts:
            nodes.append(child)
            return
        label = group_parts[0]
        group = next((row for row in nodes if row.get("label") == label and str(row.get("key") or "").startswith("group:")), None)
        if not group:
            group = build_delivery_menu_group(
                self._acceptance_group_key(parent_key, label, len(nodes) + 1),
                label,
                [],
                config_menu_id=int((group_config_menu_ids_by_label or {}).get(label) or 0),
            )
            meta = dict(group.get("meta") if isinstance(group.get("meta"), dict) else {})
            meta["explicit_menu_path_group"] = True
            group["meta"] = meta
            nodes.append(group)
        next_parent_key = str((group.get("meta") or {}).get("group_key") or parent_key)
        self._append_acceptance_child(
            nodes=group.setdefault("children", []),
            parent_key=next_parent_key,
            group_parts=group_parts[1:],
            child=child,
            group_config_menu_ids_by_label=group_config_menu_ids_by_label,
        )

    def _business_entry_intent(self, node: dict) -> str:
        meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
        return str(meta.get("entry_intent") or "").strip()

    def _business_intent_bucket(self, node: dict) -> tuple[str, str, int, set] | None:
        intent = self._business_entry_intent(node)
        if intent:
            for bucket in self.BUSINESS_INTENT_BUCKETS:
                if intent in bucket[3]:
                    return bucket
        for child in (node.get("children") if isinstance(node.get("children"), list) else []):
            if not isinstance(child, dict):
                continue
            bucket = self._business_intent_bucket(child)
            if bucket:
                return bucket
        return None

    def _has_business_entry_intent(self, node: dict) -> bool:
        if self._business_entry_intent(node):
            return True
        return any(
            self._has_business_entry_intent(child)
            for child in (node.get("children") if isinstance(node.get("children"), list) else [])
            if isinstance(child, dict)
        )

    def _intent_labeled_node(self, node: dict) -> dict:
        if not isinstance(node, dict):
            return node
        meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
        intent = str(meta.get("entry_intent") or "").strip()
        if not intent:
            return node
        label = str(node.get("label") or node.get("title") or "").strip()
        if not label:
            return node
        next_label = label
        if intent in {"query", "master_data"}:
            if not any(token in label for token in ("台账", "查询", "名册", "资料", "客户", "供应商")):
                next_label = f"{label}查询"
        elif intent == "analysis":
            if not any(token in label for token in ("报表", "分析", "总览", "余额", "明细")):
                next_label = f"{label}报表"
        elif intent == "source_fact":
            if not any(token in label for token in ("明细", "来源", "表", "记录")):
                next_label = f"{label}明细"
        elif intent == "config":
            if not any(token in label for token in ("配置", "设置", "字典")):
                next_label = f"{label}配置"
        if next_label == label:
            return node
        next_node = dict(node)
        next_node["label"] = next_label
        next_node["title"] = next_label
        next_meta = dict(meta)
        next_meta["original_label"] = label
        next_meta["intent_label_applied"] = True
        next_node["meta"] = next_meta
        return next_node

    def _merge_by_category_key(self, node: dict) -> str:
        meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
        if str(meta.get("disposition_policy") or "").strip() != "merge_by_category":
            return ""
        target = str(meta.get("integration_target") or "").strip()
        model = str(meta.get("integration_model") or meta.get("fact_model") or meta.get("model") or "").strip()
        if not target or not model:
            return ""
        return f"{model}::{target}"

    def _merge_by_category_label(self, node: dict) -> str:
        meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
        target = str(meta.get("integration_target") or "").strip()
        if not target:
            return "分类办理"
        label = re.sub(r"^[A-Za-z0-9_.]+[/\s]*", "", target).strip()
        return label or target

    def _merged_integration_meta(self, items: list[dict]) -> dict:
        action_ids = set()
        first_meta = {}
        for item in items:
            meta = item.get("meta") if isinstance(item.get("meta"), dict) else {}
            try:
                action_id = int(meta.get("integration_action_id") or 0)
            except Exception:
                action_id = 0
            if action_id > 0:
                action_ids.add(action_id)
                if not first_meta:
                    first_meta = meta
        if len(action_ids) != 1 or not first_meta:
            return {}
        view_modes = first_meta.get("integration_view_modes")
        entry_target = first_meta.get("integration_entry_target")
        return {
            "action_id": next(iter(action_ids)),
            "action_xmlid": str(first_meta.get("integration_action_xmlid") or "").strip(),
            "model": str(first_meta.get("integration_model") or first_meta.get("fact_model") or first_meta.get("model") or "").strip(),
            "view_modes": view_modes if isinstance(view_modes, list) else [],
            "entry_target": entry_target if isinstance(entry_target, dict) else {},
        }

    def _merged_record_scope_policy(self, items: list[dict]) -> str:
        policies = {
            str(
                (item.get("meta") or {}).get("record_scope_policy")
                or (item.get("meta") or {}).get("project_scope_policy")
                or ""
            ).strip().lower()
            for item in items or []
            if isinstance(item, dict) and isinstance(item.get("meta"), dict)
        }
        policies.discard("")
        if "current_project" in policies:
            policies.discard("current_project")
            policies.add("current_record")
        if not policies:
            return ""
        if policies == {"current_record"}:
            return "current_record"
        if "current_record" in policies:
            return "current_record"
        if "global" in policies:
            return "global"
        if "exempt" in policies:
            return "exempt"
        return ""

    def _merged_project_scope_policy(self, items: list[dict]) -> str:
        policy = self._merged_record_scope_policy(items)
        if policy == "current_record":
            return "current_project"
        return policy

    def _business_category_codes(self, items: list[dict]) -> list[str]:
        codes = []
        seen = set()
        for item in items or []:
            if not isinstance(item, dict):
                continue
            meta = item.get("meta") if isinstance(item.get("meta"), dict) else {}
            raw_allowed = meta.get("allowed_business_category_codes")
            candidates = raw_allowed if isinstance(raw_allowed, list) and raw_allowed else [meta.get("default_business_category_code")]
            for candidate in candidates:
                code = str(candidate or "").strip()
                if code and code not in seen:
                    seen.add(code)
                    codes.append(code)
        return codes

    def _business_category_options(self, items: list[dict]) -> list[dict]:
        codes = self._business_category_codes(items)
        category_by_code = self._business_category_default_index(codes)
        options = []
        seen = set()
        item_by_code = {}
        for item in items or []:
            if not isinstance(item, dict):
                continue
            meta = item.get("meta") if isinstance(item.get("meta"), dict) else {}
            default_code = str(meta.get("default_business_category_code") or "").strip()
            raw_allowed = meta.get("allowed_business_category_codes")
            candidates = raw_allowed if isinstance(raw_allowed, list) and raw_allowed else [default_code]
            for candidate in candidates:
                code = str(candidate or "").strip()
                if code and code not in item_by_code:
                    item_by_code[code] = item
        for code in codes:
            if not code or code in seen:
                continue
            seen.add(code)
            category = category_by_code.get(code, {})
            default_values = category.get("default_values") if isinstance(category.get("default_values"), dict) else {}
            category_id = category.get("id")
            item = item_by_code.get(code, {})
            meta = item.get("meta") if isinstance(item.get("meta"), dict) else {}
            label = str(
                category.get("name")
                or meta.get("default_business_category_label")
                or meta.get("current_business_category_label")
                or item.get("label")
                or item.get("title")
                or ""
            ).strip()
            options.append(
                {
                    "code": code,
                    "label": label,
                    "category_id": category_id,
                    "default_values": default_values,
                    "menu_id": item.get("menu_id") or item.get("id"),
                    "menu_xmlid": str(meta.get("menu_xmlid") or "").strip(),
                    "integration_target": str(meta.get("integration_target") or "").strip(),
                }
            )
        return options

    def _business_category_default_index(self, codes: list[str]) -> dict[str, dict]:
        if not codes or self.env is None or "sc.business.category" not in self.env:
            return {}
        categories = self.env["sc.business.category"].sudo().search([("code", "in", codes)])
        index = {}
        for category in categories:
            defaults = {}
            raw_defaults = str(category.default_values_json or "").strip()
            if raw_defaults:
                try:
                    parsed = json.loads(raw_defaults)
                    if isinstance(parsed, dict):
                        defaults = parsed
                except Exception:
                    defaults = {}
            index[str(category.code or "").strip()] = {
                "id": category.id,
                "name": category.name,
                "default_values": defaults,
            }
        return index

    def _group_merge_by_category_nodes(self, nodes: list[dict], parent_key: str = "") -> list[dict]:
        grouped = {}
        passthrough = []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            key = self._merge_by_category_key(node)
            if not key:
                passthrough.append(node)
                continue
            grouped.setdefault(key, []).append(node)
        synthetic_groups = []
        for key, items in grouped.items():
            first = items[0]
            meta = first.get("meta") if isinstance(first.get("meta"), dict) else {}
            integration_meta = self._merged_integration_meta(items)
            if not integration_meta:
                synthetic_groups.extend(items)
                continue
            label = self._merge_by_category_label(first)
            node_key = f"{parent_key}.merge_by_category:{key}" if parent_key else f"merge_by_category:{key}"
            sequence_candidates = [
                self._node_sequence(item)
                for item in items
                if self._node_sequence(item) > 0
            ]
            sequence = min(sequence_candidates) if sequence_candidates else 0
            record_scope_policy = self._merged_record_scope_policy(items)
            group_meta = {
                "business_entry_group": True,
                "synthetic": True,
                "configurable": False,
                "node_kind": "navigation_group",
                "merge_by_category_group": len(items) > 1,
                "single_category_integrated_entry": len(items) <= 1,
                "allowed_business_category_codes": self._business_category_codes(items),
                "business_category_options": self._business_category_options(items),
                "product_domain": meta.get("product_domain"),
                "product_domain_label": meta.get("product_domain_label"),
                "integration_target": meta.get("integration_target"),
                "fact_model": meta.get("fact_model") or meta.get("model"),
                "integration_model": meta.get("integration_model"),
                "entry_intent": meta.get("entry_intent"),
                "entry_intent_label": meta.get("entry_intent_label"),
                "disposition_policy": meta.get("disposition_policy"),
                "business_entry_contract_version": meta.get("business_entry_contract_version"),
                "entry_target_policy": "merge_to_list_form_by_business_category",
                "record_scope_policy": record_scope_policy,
                "project_scope_policy": "current_project" if record_scope_policy == "current_record" else record_scope_policy,
                "source": "delivery_engine",
                "source_authority": self.source_authority_contract(),
            }
            for field in ("action_id", "action_xmlid", "model", "view_modes", "entry_target"):
                value = integration_meta.get(field)
                if value not in (None, "", []):
                    group_meta[field] = value
            route = ""
            entry_target = group_meta.get("entry_target") if isinstance(group_meta.get("entry_target"), dict) else {}
            if entry_target:
                route = str(entry_target.get("route") or "").strip()
                if route:
                    group_meta["route"] = route
            node = {
                "key": node_key,
                "label": label,
                "title": label,
                "menu_id": synthetic_menu_id(node_key, base=870_000_000, span=10_000_000),
                "children": [],
                "meta": group_meta,
                "configurable": False,
            }
            for field in ("action_id", "action_xmlid", "model", "view_modes", "entry_target", "route"):
                value = group_meta.get(field)
                if value not in (None, "", []):
                    node[field] = value
            if sequence > 0:
                node["sequence"] = sequence
                group_meta["sequence"] = sequence
            synthetic_groups.append(node)
        return passthrough + synthetic_groups

    def _group_children_by_business_intent(self, nodes: list[dict], parent_key: str = "") -> list[dict]:
        next_nodes = []
        for node in nodes:
            if not isinstance(node, dict):
                continue
            children = node.get("children") if isinstance(node.get("children"), list) else []
            if children:
                node = dict(node)
                child_key = str(node.get("key") or node.get("menu_id") or node.get("id") or parent_key).strip()
                node["children"] = self._group_children_by_business_intent(children, parent_key=child_key)
            next_nodes.append(node)
        bucketed = {}
        passthrough = []
        for node in next_nodes:
            meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
            if meta.get("explicit_menu_path_group"):
                passthrough.append(node)
                continue
            bucket = self._business_intent_bucket(node)
            if not bucket:
                passthrough.append(node)
                continue
            bucketed.setdefault(bucket[0], []).append(node)
        productized_count = sum(len(items) for items in bucketed.values())
        if productized_count < 1:
            return next_nodes
        flattened = []
        for bucket_key, label, sequence, _intents in self.BUSINESS_INTENT_BUCKETS:
            items = bucketed.get(bucket_key) or []
            if not items:
                continue
            intent_parent_key = parent_key or "root"
            children = (
                self._group_merge_by_category_nodes(items, parent_key=f"{intent_parent_key}.intent.{bucket_key}")
                if bucket_key == "handling"
                else items
            )
            for child in self._sort_delivery_nodes(children):
                next_child = self._intent_labeled_node(child)
                next_child = dict(next_child)
                next_child.setdefault("sequence", int(next_child.get("sequence") or sequence))
                meta = dict(next_child.get("meta") if isinstance(next_child.get("meta"), dict) else {})
                meta.setdefault("intent_group", bucket_key)
                meta.setdefault("business_entry_group", True)
                meta.setdefault("source_authority", self.source_authority_contract())
                next_child["meta"] = meta
                flattened.append(next_child)
        passthrough_items = [
            item
            for item in passthrough
            if (
                (isinstance(item.get("meta"), dict) and item["meta"].get("explicit_menu_path_group"))
                or not self._has_business_entry_intent(item)
            )
        ]
        return self._sort_delivery_nodes(passthrough_items) + flattened

    def _native_preview_menus(
        self,
        *,
        native_nav: list[dict],
        policy: dict,
        entry_xmlids: set[str] | None = None,
    ) -> list[dict]:
        preview_menus_by_group = {}
        group_order = []
        emitted_menu_ids = set()
        scene_route_map = {}
        for scene in policy.get("scenes") or []:
            if not isinstance(scene, dict):
                continue
            scene_key = str(scene.get("scene_key") or "").strip()
            route = str(scene.get("route") or "").strip()
            if scene_key and route:
                scene_route_map[scene_key] = route
        entries = (
            self._iter_declared_entry_nodes(native_nav, entry_xmlids)
            if entry_xmlids is not None
            else self._iter_leaf_nodes(native_nav)
        )
        for ancestors, leaf in entries:
            meta = leaf.get("meta") if isinstance(leaf.get("meta"), dict) else {}
            menu_id = leaf.get("menu_id") or meta.get("menu_id")
            scene_key = str(leaf.get("scene_key") or ((leaf.get("meta") or {}).get("scene_key")) or "").strip()
            label = str(leaf.get("label") or leaf.get("title") or scene_key).strip()
            if not label or not menu_id:
                continue
            try:
                normalized_menu_id = int(menu_id)
            except Exception:
                continue
            if normalized_menu_id <= 0 or normalized_menu_id in emitted_menu_ids:
                continue
            emitted_menu_ids.add(normalized_menu_id)
            anchor_key, anchor_label, anchor_menu_id = self._resolve_preview_group_anchor(ancestors)
            anchor_target = {}
            for ancestor in ancestors:
                if not isinstance(ancestor, dict):
                    continue
                ancestor_meta = ancestor.get("meta") if isinstance(ancestor.get("meta"), dict) else {}
                try:
                    ancestor_menu_id = int(ancestor.get("menu_id") or ancestor_meta.get("menu_id") or 0)
                except Exception:
                    ancestor_menu_id = 0
                if ancestor_menu_id != anchor_menu_id or not self._node_has_target(ancestor):
                    continue
                for field in (
                    "route",
                    "scene_key",
                    "action_id",
                    "action_xmlid",
                    "model",
                    "view_modes",
                    "entry_target",
                ):
                    value = ancestor.get(field) if ancestor.get(field) not in (None, "", []) else ancestor_meta.get(field)
                    if value not in (None, "", []):
                        anchor_target[field] = value
                break
            group_key = f"system.{anchor_key}"
            if group_key not in preview_menus_by_group:
                preview_menus_by_group[group_key] = {
                    "group_key": group_key,
                    "group_label": anchor_label,
                    "config_menu_id": anchor_menu_id,
                    "native_preview": True,
                    "group_target": anchor_target,
                    "menus": [],
                }
                group_order.append(group_key)
            elif anchor_target and not preview_menus_by_group[group_key].get("group_target"):
                preview_menus_by_group[group_key]["group_target"] = anchor_target
            preview_menus_by_group[group_key]["menus"].append(
                {
                    "menu_key": f"system.menu_{normalized_menu_id}",
                    "label": label,
                    "menu_id": normalized_menu_id,
                    "route": str(meta.get("route") or leaf.get("route") or scene_route_map.get(scene_key) or ""),
                    "scene_key": scene_key,
                    "product_key": "",
                    "capability_key": "",
                    "menu_xmlid": str((meta.get("menu_xmlid")) or ""),
                    "scene_source": str((meta.get("scene_source")) or "native_preview"),
                    "native_preview": True,
                    "action_id": meta.get("action_id") or leaf.get("action_id"),
                    "action_xmlid": str(meta.get("action_xmlid") or leaf.get("action_xmlid") or ""),
                    "model": str(meta.get("model") or leaf.get("model") or ""),
                    "sequence": self._positive_int(leaf.get("sequence") or meta.get("sequence")),
                    "entry_target": meta.get("entry_target") if isinstance(meta.get("entry_target"), dict) else {},
                    "view_modes": (
                        meta.get("view_modes")
                        if isinstance(meta.get("view_modes"), list)
                        else (leaf.get("view_modes") if isinstance(leaf.get("view_modes"), list) else [])
                    ),
                    "visible_menu_path": " / ".join(
                        [
                            str(node.get("label") or node.get("title") or node.get("name") or "").strip()
                            for node in ancestors
                            if str(node.get("label") or node.get("title") or node.get("name") or "").strip()
                        ]
                        + [label]
                    ),
                }
            )
        return [preview_menus_by_group[group_key] for group_key in group_order]

    def _native_group_config_menu_ids_by_label(self, native_nav: list[dict]) -> dict[str, int]:
        groups: dict[str, int] = {}

        def visit(nodes: list[dict]):
            for node in nodes if isinstance(nodes, list) else []:
                if not isinstance(node, dict):
                    continue
                meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
                label = self._canonical_group_label(
                    str(node.get("label") or node.get("title") or node.get("name") or "").strip()
                )
                try:
                    menu_id = int((node.get("menu_id") or meta.get("menu_id") or 0))
                except Exception:
                    menu_id = 0
                children = node.get("children") if isinstance(node.get("children"), list) else []
                has_action = bool(
                    node.get("action_id")
                    or node.get("action")
                    or node.get("model")
                    or meta.get("action_id")
                    or meta.get("model")
                )
                if label and menu_id > 0 and children and not has_action:
                    groups.setdefault(label, menu_id)
                if children:
                    visit(children)

        visit(native_nav or [])
        if self.env is None:
            return groups
        try:
            Menu = self.env["ir.ui.menu"].sudo()
        except Exception:
            return groups

        root_id = 0
        root_xmlid = str(call_extension_hook_first(self.env, "smart_core_business_root_menu_xmlid", self.env) or "").strip()
        if not root_xmlid:
            try:
                root_xmlid = str(
                    self.env["ir.config_parameter"].sudo().get_param("smart_core.business_root_menu_xmlid", "") or ""
                ).strip()
            except Exception:
                root_xmlid = ""
        if root_xmlid and hasattr(self.env, "ref"):
            try:
                root = self.env.ref(root_xmlid, raise_if_not_found=False)
            except TypeError:
                try:
                    root = self.env.ref(root_xmlid)
                except Exception:
                    root = None
            except Exception:
                root = None
            if root and getattr(root, "_name", "") == "ir.ui.menu":
                try:
                    root_id = int(root.id or 0)
                except Exception:
                    root_id = 0
        if not root_id:
            return groups
        try:
            menus = Menu.search([("parent_id", "=", root_id)])
        except Exception:
            return groups
        for menu in menus or []:
            label = self._canonical_group_label(str(getattr(menu, "name", "") or "").strip())
            try:
                menu_id = int(getattr(menu, "id", 0) or 0)
            except Exception:
                menu_id = 0
            if label and menu_id:
                groups[label] = menu_id
        return groups

    def _native_runtime_config_menus(
        self,
        *,
        native_nav: list[dict],
        policy: dict,
        role_code: str,
        is_admin: bool,
        is_business_config_admin: bool,
    ) -> list[dict]:
        groups = self._native_preview_menus(native_nav=native_nav, policy=policy)
        out = []
        service = MenuDeliveryConvergenceService(self.env)
        for group in groups:
            if not isinstance(group, dict):
                continue
            group_label = self._canonical_group_label(str(group.get("group_label") or "").strip()) or "系统菜单"
            menus = []
            for menu in group.get("menus") or []:
                if not isinstance(menu, dict):
                    continue
                label = str(menu.get("label") or "").strip()
                model = str(menu.get("model") or "").strip()
                category = service._classify_leaf(
                    label,
                    [group_label, label],
                    is_admin=bool(is_admin) or self._is_admin_role(role_code),
                    is_business_config_admin=bool(is_business_config_admin) or self._is_business_config_role(role_code),
                )
                if (
                    category == "delivery_business_config"
                    or (model in {MENU_CONFIG_POLICY_MODEL} and (is_admin or is_business_config_admin))
                ):
                    menus.append(menu)
            if menus:
                next_group = dict(group)
                next_group["group_label"] = group_label
                next_group["menus"] = menus
                out.append(next_group)
        return out

    def build_nav(self, *, policy: dict, role_surface: dict | None = None, native_nav: list[dict] | None = None) -> list[dict]:
        role_code = str((role_surface or {}).get("role_code") or "").strip().lower()
        role_codes = [
            str(item or "").strip().lower()
            for item in ((role_surface or {}).get("role_codes") or [role_code])
            if str(item or "").strip()
        ]
        discovers_capabilities = self._discovers_installed_capabilities(role_surface)
        # Installed-capability discovery broadens the business catalogue only.
        # It must not implicitly grant the platform-admin configuration surface.
        is_admin = bool((role_surface or {}).get("is_platform_admin")) or any(
            self._is_admin_role(item) for item in role_codes
        )
        is_business_config_admin = bool((role_surface or {}).get("is_business_config_admin")) or any(
            self._is_business_config_role(item) for item in role_codes
        )
        policy_has_menu_surface = self._policy_has_menu_surface(policy)
        customer_acceptance_focus = self._policy_is_customer_acceptance_focus(policy)
        exposed_xmlids = self._exposed_menu_xmlids(role_surface)
        authorization_native_nav = self._authorization_native_nav(role_surface, native_nav or [])
        primary_native_nav = self._filter_primary_native_nodes(authorization_native_nav, role_surface)
        native_index = self._native_authorized_menu_index(primary_native_nav)
        native_group_config_ids_by_label = self._native_group_config_menu_ids_by_label(primary_native_nav)
        authorized_policy_rows = [
            menu
            for menu in self._flatten_policy_menus(policy)
            if (
                discovers_capabilities
                or str(menu.get("menu_xmlid") or "").strip().lower() in exposed_xmlids
            )
            and self._policy_menu_user_authorized(
                menu,
                native_index,
                is_admin=is_admin,
                is_business_config_admin=is_business_config_admin,
            )
            and self._role_surface_menu_allowed(menu, role_surface)
        ]
        policy_authorized_ids = set()
        policy_authorized_scenes = set()
        policy_authorized_routes = set()
        policy_authorized_xmlids = set()
        for menu in authorized_policy_rows:
            menu_id = menu.get("menu_id")
            scene_key = str(menu.get("scene_key") or "").strip()
            route = str(menu.get("route") or "").strip()
            menu_xmlid = str(menu.get("menu_xmlid") or "").strip()
            if isinstance(menu_id, int) and menu_id > 0:
                policy_authorized_ids.add(menu_id)
            if scene_key:
                policy_authorized_scenes.add(scene_key)
            if route:
                policy_authorized_routes.add(route)
            if menu_xmlid:
                policy_authorized_xmlids.add(menu_xmlid)
        grouped_native = (
            self._native_preview_menus(
                native_nav=primary_native_nav,
                policy=policy,
                entry_xmlids=exposed_xmlids,
            )
            if isinstance(role_surface, dict) and role_surface.get("exposure_policy_declared")
            else []
            if customer_acceptance_focus and not is_admin
            else self._native_runtime_config_menus(
                    native_nav=primary_native_nav,
                    policy=policy,
                    role_code=role_code,
                    is_admin=is_admin,
                    is_business_config_admin=is_business_config_admin,
                )
            if policy_has_menu_surface
            else self._native_preview_menus(native_nav=primary_native_nav, policy=policy)
        )
        if self.env is not None and (is_admin or is_business_config_admin) and not policy_has_menu_surface:
            grouped_native = native_config_delivery_groups(self.env) + list(grouped_native or [])
        groups_by_key = {}
        group_order = []
        scene_group_map = {}
        dedupe_ids = set()
        dedupe_scenes = set()
        dedupe_routes = set()
        dedupe_xmlids = set()

        if policy_has_menu_surface:
            for group in policy.get("menu_groups") or []:
                if not isinstance(group, dict):
                    continue
                group_label = self._canonical_group_label(
                    str(group.get("group_label") or group.get("label") or group.get("title") or "").strip()
                )
                if not group_label:
                    continue
                group_key = str(group.get("group_key") or group.get("key") or "").strip()
                if not group_key:
                    safe_label = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", group_label).strip("_")
                    group_key = f"catalog.{safe_label or 'product_group'}"
                if group_key in groups_by_key:
                    continue
                groups_by_key[group_key] = {
                    "group_key": group_key,
                    "group_label": group_label,
                    "config_menu_id": int(native_group_config_ids_by_label.get(group_label) or 0),
                    "native_preview": False,
                    "menus": [],
                }
                group_order.append(group_key)

        for group in grouped_native:
            if not isinstance(group, dict):
                continue
            group_key = str(group.get("group_key") or "").strip() or "system.ungrouped"
            group_label = self._canonical_group_label(str(group.get("group_label") or "").strip()) or "系统菜单"
            if group_key not in groups_by_key:
                groups_by_key[group_key] = {
                    "group_key": group_key,
                    "group_label": group_label,
                    "config_menu_id": int(group.get("config_menu_id") or native_group_config_ids_by_label.get(group_label) or 0),
                    "native_preview": bool(group.get("native_preview")),
                    "group_target": dict(group.get("group_target") or {}),
                    "menus": [],
                }
                group_order.append(group_key)
            elif group.get("native_preview"):
                groups_by_key[group_key]["native_preview"] = True
            if group.get("group_target") and not groups_by_key[group_key].get("group_target"):
                groups_by_key[group_key]["group_target"] = dict(group.get("group_target") or {})
            if int(group.get("config_menu_id") or 0):
                groups_by_key[group_key]["config_menu_id"] = int(group.get("config_menu_id") or 0)
            elif native_group_config_ids_by_label.get(group_label):
                groups_by_key[group_key].setdefault("config_menu_id", int(native_group_config_ids_by_label[group_label]))
            for menu in group.get("menus") or []:
                if not isinstance(menu, dict):
                    continue
                if not self._role_surface_menu_allowed(menu, role_surface):
                    continue
                menu_id = menu.get("menu_id")
                scene_key = str(menu.get("scene_key") or "").strip()
                route = str(menu.get("route") or "").strip()
                menu_xmlid = str(menu.get("menu_xmlid") or "").strip()
                if policy_has_menu_surface and (
                    (isinstance(menu_id, int) and menu_id > 0 and menu_id in policy_authorized_ids)
                    or (scene_key and scene_key in policy_authorized_scenes)
                    or (route and route in policy_authorized_routes)
                    or (menu_xmlid and menu_xmlid in policy_authorized_xmlids)
                ):
                    continue
                converged_menu = self._converged_menu(
                    menu=menu,
                    group_label=group_label,
                    role_code=role_code,
                    is_admin=is_admin,
                    is_business_config_admin=is_business_config_admin,
                )
                if not converged_menu:
                    continue
                if (
                    (isinstance(menu_id, int) and menu_id > 0 and menu_id in dedupe_ids)
                    or (scene_key and scene_key in dedupe_scenes)
                    or (route and route in dedupe_routes)
                    or (menu_xmlid and menu_xmlid in dedupe_xmlids)
                ):
                    continue
                if isinstance(menu_id, int) and menu_id > 0:
                    dedupe_ids.add(menu_id)
                if scene_key:
                    dedupe_scenes.add(scene_key)
                if route:
                    dedupe_routes.add(route)
                if menu_xmlid:
                    dedupe_xmlids.add(menu_xmlid)
                groups_by_key[group_key]["menus"].append(converged_menu)
                if scene_key and scene_key not in scene_group_map:
                    scene_group_map[scene_key] = group_key

        if not group_order:
            fallback_key = "system.ungrouped"
            groups_by_key[fallback_key] = {
                "group_key": fallback_key,
                "group_label": "系统菜单",
                "menus": [],
            }
            group_order.append(fallback_key)

        convergence_service = MenuDeliveryConvergenceService(self.env)
        for menu in authorized_policy_rows:
            converged_menu = dict(menu)
            policy_group_key = str(menu.get("policy_group_key") or "").strip()
            policy_group_label = self._canonical_group_label(str(menu.get("policy_group_label") or "").strip())
            preserve_policy_label = (
                policy_group_key.startswith("catalog.acceptance.")
                or policy_group_label in _CUSTOMER_ACCEPTANCE_GROUP_LABELS
            )
            renamed = None if preserve_policy_label else convergence_service.rename_labels.get(str(converged_menu.get("label") or "").strip())
            if renamed:
                converged_menu["label"] = renamed
            converged_menu["delivery_bucket"] = "released_product_policy"
            converged_menu["source_authority"] = self.source_authority_contract()
            menu_id = menu.get("menu_id")
            scene_key = str(menu.get("scene_key") or "").strip()
            route = str(menu.get("route") or "").strip()
            menu_xmlid = str(menu.get("menu_xmlid") or "").strip()
            if (isinstance(menu_id, int) and menu_id > 0 and menu_id in dedupe_ids) or (scene_key and scene_key in dedupe_scenes) or (route and route in dedupe_routes) or (menu_xmlid and menu_xmlid in dedupe_xmlids):
                continue
            if isinstance(menu_id, int) and menu_id > 0:
                dedupe_ids.add(menu_id)
            if scene_key:
                dedupe_scenes.add(scene_key)
            if route:
                dedupe_routes.add(route)
            if menu_xmlid:
                dedupe_xmlids.add(menu_xmlid)
            target_group_key = policy_group_key or scene_group_map.get(scene_key) or group_order[0]
            if target_group_key not in groups_by_key:
                groups_by_key[target_group_key] = {
                    "group_key": target_group_key,
                    "group_label": self._canonical_group_label(str(menu.get("policy_group_label") or "").strip()) or "产品发布面",
                    "config_menu_id": int(menu.get("policy_group_menu_id") or 0),
                    "menus": [],
                }
                group_order.append(target_group_key)
            groups_by_key[target_group_key]["menus"].append(converged_menu)

        label_to_group_key = {}
        for group_key in group_order:
            row = groups_by_key.get(group_key) or {}
            group_label = str(row.get("group_label") or "").strip()
            if not group_label:
                continue
            current_key = label_to_group_key.get(group_label)
            if not current_key or (
                not str(current_key).startswith("catalog.")
                and str(group_key).startswith("catalog.")
            ):
                label_to_group_key[group_label] = group_key

        merged_groups_by_key = {}
        merged_group_order = []
        for group_key in group_order:
            row = groups_by_key.get(group_key) or {}
            group_label = str(row.get("group_label") or "").strip()
            canonical_key = label_to_group_key.get(group_label) or group_key
            canonical_row = groups_by_key.get(canonical_key) or row
            if canonical_key not in merged_groups_by_key:
                merged_groups_by_key[canonical_key] = {
                    "group_key": canonical_key,
                    "group_label": str(canonical_row.get("group_label") or group_label or "系统菜单"),
                    "config_menu_id": int(canonical_row.get("config_menu_id") or 0),
                    "native_preview": bool(canonical_row.get("native_preview")),
                    "group_target": dict(canonical_row.get("group_target") or {}),
                    "menus": [],
                }
                merged_group_order.append(canonical_key)
            if row.get("native_preview"):
                merged_groups_by_key[canonical_key]["native_preview"] = True
            if row.get("group_target") and not merged_groups_by_key[canonical_key].get("group_target"):
                merged_groups_by_key[canonical_key]["group_target"] = dict(row.get("group_target") or {})
            if int(row.get("config_menu_id") or 0):
                merged_groups_by_key[canonical_key]["config_menu_id"] = int(row.get("config_menu_id") or 0)
            merged_groups_by_key[canonical_key]["menus"].extend(row.get("menus") if isinstance(row.get("menus"), list) else [])

        groups_by_key = merged_groups_by_key
        group_order = merged_group_order

        group_nodes = []
        for group_key in group_order:
            row = groups_by_key.get(group_key) or {}
            group_label = str(row.get("group_label") or "系统菜单")
            if not int(row.get("config_menu_id") or 0) and native_group_config_ids_by_label.get(group_label):
                row["config_menu_id"] = int(native_group_config_ids_by_label[group_label])
            menus = row.get("menus") if isinstance(row.get("menus"), list) else []
            if group_label in _CUSTOMER_ACCEPTANCE_GROUP_LABELS:
                children = []
                for menu in menus:
                    child = build_delivery_menu_child(menu)
                    if not child:
                        continue
                    self._append_acceptance_child(
                        nodes=children,
                        parent_key=str(row.get("group_key") or group_key),
                        group_parts=self._acceptance_menu_group_parts(menu, group_label),
                        child=child,
                        group_config_menu_ids_by_label=native_group_config_ids_by_label,
                    )
            else:
                children = []
                for menu in menus:
                    child = build_delivery_menu_child(menu)
                    if not child:
                        continue
                    self._append_policy_path_child(
                        nodes=children,
                        parent_key=str(row.get("group_key") or group_key),
                        group_label=group_label,
                        menu=menu,
                        child=child,
                        group_config_menu_ids_by_label=native_group_config_ids_by_label,
                    )
                if not (isinstance(role_surface, dict) and role_surface.get("exposure_policy_declared")):
                    children = self._group_children_by_business_intent(
                        children,
                        parent_key=str(row.get("group_key") or group_key),
                    )
            if not children:
                continue
            group_node = build_delivery_menu_group(
                str(row.get("group_key") or group_key),
                group_label,
                children,
                config_menu_id=int(row.get("config_menu_id") or 0),
                target=row.get("group_target") if isinstance(row.get("group_target"), dict) else {},
            )
            if row.get("native_preview"):
                group_meta = dict(group_node.get("meta") if isinstance(group_node.get("meta"), dict) else {})
                group_meta["native_preview"] = True
                group_meta["runtime_authority"] = "native_preview_only"
                group_node["meta"] = group_meta
            group_nodes.append(group_node)

        group_nodes = self._merge_explicit_entry_with_directory(group_nodes)
        group_nodes = self._sort_delivery_nodes(group_nodes, top_level=True)
        group_nodes = self._filter_primary_delivery_nodes(group_nodes, role_surface)
        root = build_delivery_menu_root(group_nodes, role_code)
        root["key"] = "root:system_menu"
        root["label"] = "系统菜单"
        root["title"] = "系统菜单"
        root["meta"] = {
            "source": "delivery_engine",
            "role_code": role_code,
            "role_codes": role_codes,
            "strategy": "unified_system_menu",
            "source_authority": self.source_authority_contract(),
        }
        return [root]

    def _count_leaf_nodes(self, nodes: list[dict] | None) -> int:
        count = 0
        for node in nodes or []:
            if not isinstance(node, dict):
                continue
            children = node.get("children") if isinstance(node.get("children"), list) else []
            if children:
                count += self._count_leaf_nodes(children)
            else:
                count += 1
        return count

    def describe_nav(self, nav: list[dict] | None) -> dict:
        root = (nav or [None])[0] if isinstance(nav, list) and nav else {}
        groups = root.get("children") if isinstance(root, dict) and isinstance(root.get("children"), list) else []
        stable_groups = []
        native_preview_groups = []
        for group in groups:
            if not isinstance(group, dict):
                continue
            meta = group.get("meta") if isinstance(group.get("meta"), dict) else {}
            group_key = str(meta.get("group_key") or "").strip()
            if meta.get("native_preview") or group_key == self.NATIVE_PREVIEW_GROUP_KEY:
                native_preview_groups.append(group)
            else:
                stable_groups.append(group)
        return {
            "source_authority": self.source_authority_contract(),
            "group_count": len(groups),
            "stable_group_count": len(stable_groups),
            "native_preview_group_count": len(native_preview_groups),
            "stable_leaf_count": sum(self._count_leaf_nodes(group.get("children") or []) for group in stable_groups),
            "native_preview_leaf_count": sum(self._count_leaf_nodes(group.get("children") or []) for group in native_preview_groups),
            "native_preview_group_key": self.NATIVE_PREVIEW_GROUP_KEY if native_preview_groups else "",
            "group_keys": [
                str(((group.get("meta") or {}).get("group_key")) or "").strip()
                for group in groups
                if isinstance(group, dict)
            ],
        }
