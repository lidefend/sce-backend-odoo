# -*- coding: utf-8 -*-
"""Pure scenario-surface navigation projection (P1, smart_construction_core).

Regroups already-authorized navigation leaves into the scenario product surface.
It deliberately does NOT resolve menus/actions, grant authority, expand ACL, or
fabricate routes: every leaf identity (menu_id / action_id / action_xmlid /
model / view_modes / route) is supplied by the authorized canonical-navigation +
route-authority delivery and is only re-attached under its declared
scenario/intent. Invalid surface data returns an explicit error contract so the
caller can fall back to the legacy navigation instead of emitting a broken tree.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


SURFACE_PATH = Path(__file__).resolve().parents[1] / "data" / "scenario_product_surface.json"
SCHEMA = "construction.scenario_product_surface.v1"
INTENT_ORDER = ("handle", "view", "approve", "report", "master_data")
INTENT_LABELS = {
    "handle": "办理",
    "view": "查看",
    "approve": "审批",
    "report": "报表",
    "master_data": "基础信息维护",
}


def load_surface(path: Path | str = SURFACE_PATH) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA:
        raise ValueError(f"invalid scenario product surface schema: {data.get('schema')!r}")
    return data


def _text(value: Any) -> str:
    return str(value or "").strip()


def build_menu_index(surface: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Return menu_xmlid -> location/intent/scenario metadata.

    Raises ValueError on duplicate or empty menu assignments so the caller can
    treat a malformed surface as a fallback-triggering error rather than
    rendering partial navigation.
    """
    index: dict[str, dict[str, str]] = {}

    def claim(menu_xmlid: str, location: str, scenario_key: str = "", scenario_name: str = "", intent: str = "") -> None:
        key = _text(menu_xmlid)
        if not key:
            raise ValueError("empty menu_xmlid in scenario product surface")
        if key in index:
            raise ValueError(f"duplicate menu assignment in scenario product surface: {key}")
        index[key] = {
            "location": location,
            "scenario_key": _text(scenario_key),
            "scenario_name": _text(scenario_name),
            "intent": _text(intent),
        }

    for menu in surface.get("horizontal_work_center", {}).get("menus", []) or []:
        claim(menu, "horizontal")
    for menu in surface.get("platform_support", {}).get("menus", []) or []:
        claim(menu, "platform")
    scenario_keys: set[str] = set()
    for scenario in surface.get("scenarios", []) or []:
        if not isinstance(scenario, dict) or not isinstance(scenario.get("key"), str):
            raise ValueError("scenario key must be a nonempty string")
        scenario_key = _text(scenario.get("key"))
        if not scenario_key:
            raise ValueError("empty scenario key in scenario product surface")
        if scenario_key in scenario_keys:
            raise ValueError(f"duplicate scenario key in scenario product surface: {scenario_key}")
        scenario_keys.add(scenario_key)
        scenario_name = _text(scenario.get("name") or scenario_key)
        for intent, menus in (scenario.get("intents") or {}).items():
            for menu in menus or []:
                claim(menu, "scenario", scenario_key, scenario_name, _text(intent))
    return index


def _group_leaves(
    leaves: Iterable[dict[str, Any]],
    index: dict[str, dict[str, str]],
) -> tuple[dict[str, Any], list[str]]:
    by_menu: dict[str, list[dict[str, Any]]] = {}
    unmapped: list[str] = []
    for leaf in leaves:
        if not isinstance(leaf, dict):
            continue
        menu_xmlid = _text(leaf.get("menu_xmlid") or leaf.get("xmlid"))
        if not menu_xmlid:
            continue
        meta = index.get(menu_xmlid)
        if not meta:
            unmapped.append(menu_xmlid)
            continue
        by_menu.setdefault(menu_xmlid, []).append(dict(leaf))
    return by_menu, unmapped


def project_scenario_navigation(
    *,
    surface: dict[str, Any] | None = None,
    authorized_leaves: Iterable[dict[str, Any]],
    include_platform: bool = False,
) -> dict[str, Any]:
    """Project authorized leaves into domain -> scenario -> intent -> entries.

    `authorized_leaves` are the already-filtered navigation leaves supplied by
    the canonical-navigation + route-authority delivery. Only leaves whose
    menu_xmlid is declared in the surface are regrouped; unmapped leaves remain
    in the legacy navigation and are reported in diagnostics.
    """
    try:
        source = surface if surface is not None else load_surface()
        if _text(source.get("schema")) != SCHEMA:
            raise ValueError(f"invalid scenario product surface schema: {source.get('schema')!r}")
        index = build_menu_index(source)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "error_code": "SURFACE_INVALID",
            "message": _text(exc),
            "tree": None,
        }

    by_menu, unmapped = _group_leaves(authorized_leaves, index)

    scenario_rows: dict[str, dict[str, Any]] = {
        _text(s.get("key")): s for s in (source.get("scenarios") or []) if _text(s.get("key"))
    }

    domains: list[dict[str, Any]] = []
    for domain in source.get("domains", []) or []:
        scenario_nodes: list[dict[str, Any]] = []
        for scenario_key in domain.get("scenarios", []) or []:
            key = _text(scenario_key)
            scenario = scenario_rows.get(key)
            if not scenario:
                continue
            intent_nodes: list[dict[str, Any]] = []
            for intent in INTENT_ORDER:
                entries = [
                    leaf
                    for menu in (scenario.get("intents") or {}).get(intent, []) or []
                    for leaf in by_menu.get(_text(menu), [])
                ]
                if entries:
                    intent_nodes.append({
                        "intent": intent,
                        "label": INTENT_LABELS.get(intent, intent),
                        "entries": entries,
                    })
            if intent_nodes:
                scenario_nodes.append({
                    "key": key,
                    "name": _text(scenario.get("name") or key),
                    "type": _text(scenario.get("type")),
                    "intents": intent_nodes,
                })
        if scenario_nodes:
            domains.append({
                "key": _text(domain.get("key")),
                "name": _text(domain.get("name") or domain.get("key")),
                "scenarios": scenario_nodes,
            })

    horizontal = [leaf for menu in (source.get("horizontal_work_center", {}).get("menus", []) or []) for leaf in by_menu.get(_text(menu), [])]
    platform = [leaf for menu in (source.get("platform_support", {}).get("menus", []) or []) for leaf in by_menu.get(_text(menu), [])]

    grouped_menu_count = sum(len(v) for v in by_menu.values())
    return {
        "ok": True,
        "tree": {
            "domains": domains,
            "horizontal": horizontal,
            "platform": platform if include_platform else [],
            "platform_label": _text(source.get("platform_support", {}).get("name")),
            "management_actions": [],
        },
        "diagnostics": {
            "authorized_leaf_count": sum(1 for leaf in authorized_leaves if isinstance(leaf, dict) and _text(leaf.get("menu_xmlid") or leaf.get("xmlid"))),
            "grouped_menu_count": grouped_menu_count,
            "grouped_leaf_count": sum(len(v) for v in by_menu.values()),
            "unmapped_menu_xmlids": unmapped,
            "unmapped_count": len(unmapped),
            "domain_count": len(domains),
            "scenario_count": sum(len(d["scenarios"]) for d in domains),
            "intent_count": sum(len(s["intents"]) for d in domains for s in d["scenarios"]),
        },
    }


def _route_authority_by_pair(route_authority: dict[str, Any] | None) -> dict[tuple[int, int], dict[str, Any]]:
    authority = route_authority if isinstance(route_authority, dict) else {}
    by_pair: dict[tuple[int, int], dict[str, Any]] = {}
    for bucket in ("primary_actions", "role_home_actions", "contextual_actions", "admin_actions"):
        for entry in authority.get(bucket) or []:
            if not isinstance(entry, dict):
                continue
            try:
                pair = (int(entry.get("menu_id") or 0), int(entry.get("action_id") or 0))
            except (TypeError, ValueError):
                pair = (0, 0)
            if pair[0] > 0 and pair[1] > 0:
                by_pair[pair] = entry
    return by_pair


def flatten_authorized_nav_leaves(
    nav: Iterable[dict[str, Any]],
    route_authority: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Flatten the final authorized canonical-navigation tree into leaf rows.

    The projection never resolves or authorizes anything; it only re-attaches
    the leaf identity already emitted by the navigation delivery. ``action_xmlid``
    is recovered from the route-authority pair so the projection preserves the
    original XML identity without consulting the ORM.
    """
    authority_by_pair = _route_authority_by_pair(route_authority)
    leaves: list[dict[str, Any]] = []

    def walk(nodes: Iterable[dict[str, Any]]) -> None:
        for node in nodes:
            if not isinstance(node, dict):
                continue
            meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
            carrier = node.get("canonical_navigation") if isinstance(node.get("canonical_navigation"), dict) else {}
            try:
                menu_id = int(node.get("menu_id") or meta.get("menu_id") or carrier.get("menu_id") or 0)
                action_id = int(node.get("action_id") or meta.get("action_id") or carrier.get("action_id") or 0)
            except (TypeError, ValueError):
                menu_id, action_id = 0, 0
            children = node.get("children") or []
            route = _text(carrier.get("route") or node.get("route") or meta.get("route"))
            if menu_id > 0 and (action_id > 0 or route):
                entry = authority_by_pair.get((menu_id, action_id), {})
                leaves.append({
                    "menu_xmlid": _text(node.get("menu_xmlid") or node.get("xmlid") or meta.get("menu_xmlid") or entry.get("menu_xmlid")),
                    "menu_id": menu_id,
                    "action_id": action_id,
                    "action_xmlid": _text(entry.get("action_xmlid")),
                    "model": _text(node.get("model") or meta.get("model") or entry.get("model")),
                    "view_modes": node.get("view_modes") or meta.get("view_modes") or entry.get("view_modes") or [],
                    "route": route,
                    "label": _text(node.get("label") or node.get("name") or carrier.get("label")),
                })
            if children:
                walk(children)

    walk(nav or [])
    return leaves


def project_authorized_nav(
    *,
    nav: Iterable[dict[str, Any]],
    route_authority: dict[str, Any] | None = None,
    surface: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Convenience: flatten the authorized nav and project the scenario surface."""
    leaves = flatten_authorized_nav_leaves(nav, route_authority=route_authority)
    return project_scenario_navigation(
        surface=surface,
        authorized_leaves=leaves,
        # Leaves are already native-authorized; regrouping must not discard
        # tenant configuration entries just because no business scene is enabled.
        include_platform=True,
    )


def project_management_workspaces(*, scenes, check_access, surface=None):
    """Expose declared workspaces only when already delivered and native ACL allows.

    This navigation affordance never enables a business scene or grants access;
    the workspace and mutation handlers retain their native authorization checks.
    """
    source = surface if surface is not None else load_surface()
    available = {row.get("key") or row.get("code"): row for row in scenes if isinstance(row, dict)}
    actions = []
    for declaration in source.get("platform_support", {}).get("workspace_entries", []):
        scene = available.get(declaration.get("scene_key"))
        operations = declaration.get("access_operations") or []
        model = declaration.get("access_model")
        if not scene or not model or not operations:
            continue
        if not all(check_access(model, operation) for operation in operations):
            continue
        route = _text((scene.get("target") or {}).get("route"))
        label = _text(scene.get("name"))
        if route.startswith("/s/") and label:
            actions.append({"key": declaration["scene_key"], "label": label, "route": route})
    return actions
