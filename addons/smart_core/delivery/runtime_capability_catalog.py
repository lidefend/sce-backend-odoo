# -*- coding: utf-8 -*-
"""Read-only projection of installed Odoo capability facts."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


def _text(value: Any) -> str:
    return str(value or "").strip()


def _action_id(action: Any) -> int:
    try:
        return int(action.id or 0) if action else 0
    except Exception:
        return 0


def _action_model(action: Any) -> str:
    try:
        model = _text(getattr(action, "res_model", ""))
        if model:
            return model
        model = _text(getattr(action, "model_name", ""))
        if model:
            return model
        model_id = getattr(action, "model_id", None)
        model = _text(getattr(model_id, "model", ""))
        if model:
            return model
        binding_model_id = getattr(action, "binding_model_id", None)
        return _text(getattr(binding_model_id, "model", ""))
    except Exception:
        return ""


def _action_view_modes(action: Any) -> list[str]:
    try:
        value = _text(getattr(action, "view_mode", ""))
    except Exception:
        value = ""
    return [_text(item) for item in value.split(",") if _text(item)]


def _record_xmlid(record: Any) -> str:
    if not record:
        return ""
    try:
        return _text(record.get_external_id().get(record.id, ""))
    except Exception:
        return ""


def _record_group_xmlids(record: Any) -> list[str]:
    values = []
    try:
        groups = getattr(record, "groups_id", None) or []
    except Exception:
        groups = []
    for group in groups:
        xmlid = _record_xmlid(group)
        if xmlid:
            values.append(xmlid)
    return sorted(set(values))


def _menu_path(menu: Any) -> list[str]:
    path: list[str] = []
    current = menu
    while current:
        name = _text(getattr(current, "name", ""))
        if name:
            path.append(name)
        current = getattr(current, "parent_id", None)
    return list(reversed(path))


def capability_identity(
    *,
    menu_id: int,
    menu_xmlid: str,
    action_id: int,
    action_xmlid: str,
) -> tuple[str, bool]:
    menu_key = _text(menu_xmlid) or f"menu:{int(menu_id or 0)}"
    action_key = _text(action_xmlid) or f"action:{int(action_id or 0)}"
    stable = bool(_text(menu_xmlid) and _text(action_xmlid))
    # Preserve existing ordinary XMLID keys. Encode the entire tuple when a
    # component has additional separators or uses database-local references.
    if all(re.fullmatch(r"[A-Za-z0-9_]+\.[A-Za-z0-9_]+", key) for key in (menu_key, action_key)):
        return f"native.entry.{menu_key}.{action_key}", stable
    return f"native.entry.v2.{menu_key.encode('utf-8').hex()}.{action_key.encode('utf-8').hex()}", stable


@dataclass(frozen=True)
class CapabilityCatalogProjection:
    rows: list[dict]
    diagnostics: dict

    @property
    def by_key(self) -> dict[str, dict]:
        return {row["capability_key"]: row for row in self.rows}


class RuntimeCapabilityCatalogService:
    """Project installed native entries without publication semantics."""

    SOURCE_AUTHORITIES = (
        "ir.ui.menu",
        "ir.actions",
        "res.groups",
        "ir.model.data",
    )

    def __init__(self, env):
        self.env = env

    @classmethod
    def source_authority_contract(cls) -> dict:
        return {
            "kind": "runtime_installed_capability_catalog",
            "authorities": list(cls.SOURCE_AUTHORITIES),
            "projection_only": True,
            "candidate_object": "active_action_menu",
            "supported_action_types": ["ir.actions.act_window", "ir.actions.client", "ir.actions.server", "ir.actions.report", "ir.actions.act_url"],
            "no_business_fact_authority": True,
            "no_publication_authority": True,
            "no_tenant_authority": True,
        }

    def _candidate_menus(self, module: str):
        if not module:
            # Fact discovery must not invoke ir.ui.menu.search(), whose
            # visibility projection depends on the principal's groups/ACLs.
            self.env.cr.execute("SELECT id FROM ir_ui_menu ORDER BY sequence, id")
            return self.env["ir.ui.menu"].sudo().browse([row[0] for row in self.env.cr.fetchall()]).exists()
        rows = self.env["ir.model.data"].sudo().search(
            [
                ("module", "=", module),
                ("model", "=", "ir.ui.menu"),
            ]
        )
        menu_ids = [int(row.res_id or 0) for row in rows if int(row.res_id or 0) > 0]
        if not menu_ids:
            return []
        menus = self.env["ir.ui.menu"].sudo().browse(menu_ids).exists()
        return sorted(
            menus,
            key=lambda menu: (
                int(getattr(menu, "sequence", 0) or 0),
                int(menu.id or 0),
            ),
        )

    def collect(
        self,
        *,
        module: str = "",
        xmlid_prefix: str = "",
        root_label: str = "",
        leaf_actions_only: bool = True,
        candidate_menus=None,
    ) -> CapabilityCatalogProjection:
        menus = (
            list(candidate_menus or [])
            if candidate_menus is not None
            else self._candidate_menus(module)
        )
        rows = []
        seen = set()
        diagnostics = {
            "source_authority": self.source_authority_contract(),
            "module": _text(module),
            "xmlid_prefix": _text(xmlid_prefix),
            "root_label": _text(root_label),
            "leaf_actions_only": bool(leaf_actions_only),
            "candidate_menu_count": len(menus),
            "empty_reason": "MODULE_HAS_NO_MENU_CANDIDATES" if module and not menus else "",
            "root_label_filter_applied": bool(root_label and not (module or xmlid_prefix)),
            "skipped_action_type_count": 0,
            "skipped_inactive_count": 0,
            "skipped_prefix_count": 0,
            "skipped_root_count": 0,
            "skipped_no_action_count": 0,
            "skipped_container_count": 0,
            "duplicate_capability_count": 0,
        }
        for menu in menus:
            if hasattr(menu, "active") and not bool(getattr(menu, "active")):
                diagnostics["skipped_inactive_count"] += 1
                continue
            menu_xmlid = _record_xmlid(menu)
            prefix = _text(xmlid_prefix)
            if prefix and not menu_xmlid.startswith(prefix):
                diagnostics["skipped_prefix_count"] += 1
                continue
            path = _menu_path(menu)
            if not path:
                diagnostics["skipped_root_count"] += 1
                continue
            expected_root = _text(root_label)
            if expected_root and not (module or prefix) and path[0] != expected_root:
                diagnostics["skipped_root_count"] += 1
                continue
            action = getattr(menu, "action", None)
            action_id = _action_id(action)
            if action_id <= 0:
                diagnostics["skipped_no_action_count"] += 1
                continue
            if _text(getattr(action, "_name", "")) not in self.source_authority_contract()["supported_action_types"]:
                diagnostics["skipped_action_type_count"] += 1
                continue
            children = getattr(menu, "child_id", None) or []
            if leaf_actions_only and any(
                bool(getattr(child, "active", True)) for child in children
            ):
                diagnostics["skipped_container_count"] += 1
                continue
            action_xmlid = _record_xmlid(action)
            capability_key, stable = capability_identity(
                menu_id=int(menu.id or 0),
                menu_xmlid=menu_xmlid,
                action_id=action_id,
                action_xmlid=action_xmlid,
            )
            if capability_key in seen:
                diagnostics["duplicate_capability_count"] += 1
                continue
            seen.add(capability_key)
            owner = menu_xmlid.split(".", 1)[0] if "." in menu_xmlid else ""
            if not owner and "." in action_xmlid:
                owner = action_xmlid.split(".", 1)[0]
            rows.append(
                {
                    "capability_key": capability_key,
                    "identity_stable": stable,
                    "identity_scope": "cross_database_xmlid" if stable else "current_database",
                    "owner_module": owner,
                    "menu_id": int(menu.id or 0),
                    "menu_xmlid": menu_xmlid,
                    "menu_name": _text(getattr(menu, "name", "")),
                    "menu_path": path,
                    "menu_sequence": int(getattr(menu, "sequence", 0) or 0),
                    "action_id": action_id,
                    "action_xmlid": action_xmlid,
                    "action_model": _text(getattr(action, "_name", "")),
                    "res_model": _action_model(action),
                    "view_modes": _action_view_modes(action),
                    "menu_group_xmlids": _record_group_xmlids(menu),
                    "action_group_xmlids": _record_group_xmlids(action),
                    "source_kind": "ir.ui.menu",
                    "source_authority": self.source_authority_contract(),
                }
            )
        diagnostics["capability_count"] = len(rows)
        diagnostics["stable_identity_count"] = sum(
            bool(row["identity_stable"]) for row in rows
        )
        return CapabilityCatalogProjection(rows=rows, diagnostics=diagnostics)
