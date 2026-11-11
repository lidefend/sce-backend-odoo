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


def build_menu_index(
    surface: dict[str, Any],
    *,
    parent_by_menu: dict[str, str] | None = None,
) -> dict[str, dict[str, str]]:
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

    horizontal_root = _text(surface.get("horizontal_work_center", {}).get("root_menu_xmlid"))
    platform_root = _text(surface.get("platform_support", {}).get("root_menu_xmlid"))
    if parent_by_menu:
        for menu_xmlid, parent_xmlid in parent_by_menu.items():
            key = _text(menu_xmlid)
            if not key:
                continue
            if horizontal_root and _text(parent_xmlid) == horizontal_root:
                claim(key, "horizontal")
            elif platform_root and _text(parent_xmlid) == platform_root:
                claim(key, "platform")
    else:
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


def resolve_native_parent_by_menu(env, surface: dict[str, Any]) -> dict[str, str]:
    """Resolve each horizontal/platform menu's native parent xmlid from the menu tree."""
    mapping: dict[str, str] = {}
    if env is None:
        return mapping
    try:
        for section in ("horizontal_work_center", "platform_support"):
            root_xmlid = _text((surface.get(section) or {}).get("root_menu_xmlid"))
            if not root_xmlid:
                continue
            try:
                root = env.ref(root_xmlid, raise_if_not_found=False)
            except Exception:
                continue
            if not root:
                continue
            for child in getattr(root, "child_id", []) or []:
                try:
                    ext = child.get_external_id().get(child.id)
                    child_xmlid = _text(ext) if ext else ""
                except Exception:
                    child_xmlid = ""
                if child_xmlid:
                    mapping[child_xmlid] = root_xmlid
    except Exception:
        return {}
    return mapping


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
        leaves = list(authorized_leaves)
        parent_by_menu = {
            _text(leaf.get("menu_xmlid")): _text(leaf.get("parent_menu_xmlid"))
            for leaf in leaves
            if isinstance(leaf, dict) and _text(leaf.get("menu_xmlid"))
        }
        index = build_menu_index(source, parent_by_menu=parent_by_menu)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "error_code": "SURFACE_INVALID",
            "message": _text(exc),
            "tree": None,
        }

    authorized_leaves = leaves
    by_menu, unmapped = _group_leaves(authorized_leaves, index)
    # Native configuration workspaces have their own authorized action
    # declaration and lifecycle, independent of the released business catalogue.
    native_platform = [dict(leaf) for leaf in authorized_leaves
                       if isinstance(leaf, dict)
                       and _text(leaf.get("menu_xmlid")) not in index
                       and leaf.get("delivery_bucket") == "delivery_business_config"
                       and (leaf.get("entry_target") or {}).get("delivery_scope") == "configuration"]
    native_platform_keys = {leaf["menu_xmlid"] for leaf in native_platform}
    unmapped = [key for key in unmapped if key not in native_platform_keys]

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

    horizontal_root = _text(source.get("horizontal_work_center", {}).get("root_menu_xmlid"))
    platform_root = _text(source.get("platform_support", {}).get("root_menu_xmlid"))
    horizontal = [
        dict(leaf) for leaf in authorized_leaves
        if horizontal_root and _text(leaf.get("parent_menu_xmlid")) == horizontal_root
    ]
    platform = [
        dict(leaf) for leaf in authorized_leaves
        if platform_root and _text(leaf.get("parent_menu_xmlid")) == platform_root
        and _text(leaf.get("menu_xmlid")) not in native_platform_keys
    ]
    platform = native_platform + platform

    grouped_menu_count = sum(len(v) for v in by_menu.values()) + len(native_platform)
    return {
        "ok": True,
        "tree": {
            "domains": domains,
            "horizontal": horizontal,
            "platform": platform if include_platform else [],
            "platform_label": _text(source.get("platform_support", {}).get("name")),
        },
        "diagnostics": {
            "authorized_leaf_count": sum(1 for leaf in authorized_leaves if isinstance(leaf, dict) and _text(leaf.get("menu_xmlid") or leaf.get("xmlid"))),
            "grouped_menu_count": grouped_menu_count,
            "grouped_leaf_count": grouped_menu_count,
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

    def walk(
        nodes: Iterable[dict[str, Any]],
        parent_menu_xmlid: str = "",
        parent_group_key: str = "",
        parent_group_label: str = "",
        center_menu_id: int = 0,
        depth: int = 0,
    ) -> None:
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
            entry = authority_by_pair.get((menu_id, action_id), {})
            menu_xmlid = _text(node.get("menu_xmlid") or node.get("xmlid") or meta.get("menu_xmlid") or entry.get("menu_xmlid"))
            label = _text(node.get("label") or node.get("name") or carrier.get("label"))
            group_label = _text(
                node.get("policy_group_label")
                or node.get("group_label")
                or meta.get("policy_group_label")
                or meta.get("group_label")
            )
            group_key = _text(
                node.get("policy_group_key")
                or node.get("group_key")
                or meta.get("policy_group_key")
                or meta.get("group_key")
                or parent_group_key
            )
            # The center is the delivery tree's direct child of the business
            # root (depth 1). Its stable identity is the native center menu id
            # carried on the group node, never the editable display name.
            native_center_id = 0
            try:
                native_center_id = int(
                    carrier.get("menu_id")
                    or node.get("config_menu_id")
                    or meta.get("config_menu_id")
                    or 0
                )
            except (TypeError, ValueError):
                native_center_id = 0
            if depth == 1:
                group_label = group_label or label
                # Always rebase to this center node (even to zero), so a
                # sibling whose native id is missing never inherits the
                # previous sibling's center.
                center_menu_id = native_center_id
            effective_group_label = group_label or parent_group_label
            if menu_id > 0 and (action_id > 0 or route):
                leaf_parent = _text(node.get("parent_menu_xmlid") or meta.get("parent_menu_xmlid")) or parent_menu_xmlid
                leaves.append({
                    "menu_xmlid": menu_xmlid,
                    "menu_id": menu_id,
                    "action_id": action_id,
                    "action_xmlid": _text(entry.get("action_xmlid")),
                    "model": _text(node.get("model") or meta.get("model") or entry.get("model")),
                    "view_modes": node.get("view_modes") or meta.get("view_modes") or entry.get("view_modes") or [],
                    "route": route,
                    "label": label,
                    "delivery_bucket": _text(node.get("delivery_bucket") or meta.get("delivery_bucket")),
                    "entry_target": entry.get("entry_target") or meta.get("entry_target") or {},
                    "parent_menu_xmlid": leaf_parent,
                    "policy_group_key": group_key,
                    "policy_group_label": effective_group_label,
                    "center_menu_id": center_menu_id,
                })
            if children:
                walk(children, menu_xmlid, group_key, effective_group_label, center_menu_id, depth + 1)

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


BUSINESS_ROOT_XMLID = "smart_construction_core.menu_sc_root"
SCENARIO_INTENT_LABELS = {
    "handle": "办理",
    "view": "查看",
    "approve": "审批",
    "report": "报表",
    "master_data": "基础信息维护",
}


def _menu_external_id(env, menu) -> str:
    try:
        external = menu.get_external_id().get(menu.id)
        return _text(external)
    except Exception:
        return ""


def _native_center_for_menus(env, menu_ids: Iterable[int]) -> dict[int, dict[str, Any]]:
    """Map menu id to its native center, or its persisted external placement.

    The center identity is the stable native menu XMLID; its display name is
    only a projection. The original JSON alias consolidation is intentionally
    not applied: native centers stay as maintained in ``ir.ui.menu``.
    """
    if env is None:
        return {}
    Menu = env["ir.ui.menu"].sudo()
    ids = sorted({int(menu_id or 0) for menu_id in menu_ids if int(menu_id or 0) > 0})
    menus = Menu.browse(ids).exists()
    result: dict[int, dict[str, Any]] = {}
    for menu in menus:
        current = menu
        center = None
        for _ in range(32):
            parent = current.parent_id
            if not parent:
                break
            if _menu_external_id(env, parent) == BUSINESS_ROOT_XMLID:
                center = current
                break
            current = parent
        if center is None:
            candidate = getattr(menu, "sc_product_center_id", None)
            if candidate and candidate.parent_id and _menu_external_id(env, candidate.parent_id) == BUSINESS_ROOT_XMLID:
                center = candidate
        if center is not None:
            result[int(menu.id)] = {
                "key": _menu_external_id(env, center),
                "name": _text(center.name),
                "sequence": int(center.sequence),
                "entry_sequence": int(menu.sequence),
            }
    return result


def load_runtime_surface(env):
    """Read maintained scenario facts; files are never a runtime fallback.

    Archived bindings remain present so authorization cannot mistake them for
    an exemption. Native IDs cover menus without an external identifier.
    """
    if env is None:
        raise ValueError("scenario runtime requires an Odoo environment")
    scenarios = env["sc.product.scenario"].sudo().with_context(active_test=False).search([])
    rows = []
    for scenario in scenarios:
        intents = {}
        bindings = []
        for entry in scenario.entry_ids:
            menu = entry.menu_id
            key = _menu_external_id(env, menu) or f"menu:{menu.id}"
            intents.setdefault(entry.intent, []).append(key)
            bindings.append({"menu_id": menu.id, "menu_key": key,
                             "sequence": entry.sequence, "intent": entry.intent})
        rows.append({"key": scenario.code, "name": scenario.name,
                     "active": bool(scenario.active), "sequence": scenario.sequence,
                     "intents": intents, "bindings": bindings})
    return {"schema": SCHEMA, "scenarios": rows}


def runtime_menu_scope(env, surface=None):
    """Index all native menus as bound, explicitly exempt, or missing.

    This is a projection of persisted facts, not a second editable registry.
    The index and ID/action maps share the same current native identities.
    """
    surface = load_runtime_surface(env) if surface is None else surface
    index = build_menu_index(surface)
    active = {row["key"]: row["active"] for row in surface["scenarios"]}
    by_id, by_action = {}, {}
    # The scene-fact index must cover every native menu, not just the menus the
    # current principal may see. Odoo filters ir.ui.menu search by the caller's
    # menu groups even under sudo unless the full-list context is set, so a
    # role that cannot yet see a configuration menu would silently drop it from
    # this index and then misclassify its route as BUSINESS_SCENARIO_CONFIGURATION_MISSING.
    for menu in env["ir.ui.menu"].sudo().with_context(
        **{"ir.ui.menu.full_list": True}
    ).search([]):
        key = _menu_external_id(env, menu) or f"menu:{menu.id}"
        by_id[menu.id] = key
        if menu.action:
            by_action.setdefault(menu.action.id, []).append(key)
        if key in index:
            index[key]["scenario_active"] = active[index[key]["scenario_key"]]
        else:
            index[key] = {"location": ("exempt" if menu.sc_scenario_exempt else
                                       "container" if not menu.action and menu.child_id else "missing"),
                          "scenario_key": "", "scenario_name": "", "intent": ""}
    return index, by_id, by_action


def _scenario_entries_by_menu(env) -> dict[int, dict[str, Any]]:
    """Load maintainable scenario bindings from the Odoo model, server-side."""
    if env is None:
        return {}
    Entry = env["sc.product.scenario.entry"].sudo()
    result: dict[int, dict[str, Any]] = {}
    for entry in Entry.search([]):
        if not entry.menu_id or not entry.scenario_id:
            continue
        intent = _text(entry.intent)
        result[int(entry.menu_id.id)] = {
            "scenario_key": _text(entry.scenario_id.code),
            "scenario_name": _text(entry.scenario_id.name),
            "scenario_active": bool(entry.scenario_id.active),
            "scenario_sequence": int(entry.scenario_id.sequence),
            "sequence": int(entry.sequence),
            "intent": intent,
            "intent_label": SCENARIO_INTENT_LABELS.get(intent, intent),
        }
    return result


def _scenarioized_navigation(env, centers, route_authority) -> list[dict[str, Any]]:
    """Project scenario centers into the final canonical navigation contract."""
    try:
        from odoo.addons.smart_core.core.delivery_menu_defaults import (
            build_delivery_menu_child,
            build_delivery_menu_group,
            build_delivery_menu_root,
        )
        from odoo.addons.smart_core.delivery.menu_service import MenuService
    except ModuleNotFoundError:
        return []

    def child(entry):
        row = dict(entry)
        row["menu_key"] = (
            f"scenario.entry.{int(row.get('menu_id') or 0)}."
            f"{int(row.get('action_id') or 0)}"
        )
        return build_delivery_menu_child(row)

    group_nodes = []
    for center in centers or []:
        if not isinstance(center, dict):
            continue
        children = []
        for scenario in center.get("scenarios") or []:
            scenario_children = [
                node
                for entry in scenario.get("entries") or []
                if (node := child(entry))
            ]
            if not scenario_children:
                continue
            children.append(build_delivery_menu_group(
                f"scenario.{center.get('key')}.{scenario.get('key')}",
                _text(scenario.get("name") or scenario.get("key")),
                scenario_children,
            ))
        children.extend(
            node
            for entry in center.get("entries") or []
            if (node := child(entry))
        )
        if not children:
            continue
        center_menu = env.ref(center.get("key"), raise_if_not_found=False)
        group_nodes.append(build_delivery_menu_group(
            _text(center.get("key")) or f"scenario.center.{center.get('sequence')}",
            _text(center.get("name") or center.get("key")),
            children,
            config_menu_id=int(getattr(center_menu, "id", 0) or 0),
        ))
    if not group_nodes:
        return []
    root = build_delivery_menu_root(group_nodes, "")
    root["key"] = "root:scenario_navigation"
    root["label"] = "业务场景"
    root["title"] = "业务场景"
    return MenuService(env).project_canonical_navigation([root], route_authority)


def project_authorized_nav_with_env(env, nav, route_authority=None) -> dict[str, Any]:
    """Project authorized navigation into native-center -> scenario -> entries.

    Reads the maintainable ``sc.product.scenario`` bindings server-side and only
    re-attaches already-authorized leaves; it never grants authority and never
    widens the current user's entry set. Entries without an active scenario are
    kept under their center with ``configured=false`` so authorized work does
    not silently disappear.
    """
    leaves = flatten_authorized_nav_leaves(nav, route_authority=route_authority)
    center_by_id = _native_center_for_menus(env, [leaf.get("menu_id") for leaf in leaves])
    scenario_by_menu = _scenario_entries_by_menu(env)
    centers: dict[str, dict[str, Any]] = {}
    for leaf in leaves:
        menu_id = int(leaf.get("menu_id") or 0)
        # Synthetic menu containers (center headers with a /m/ route and no
        # stable XMLID) are grouping nodes, not user entries; they must not be
        # re-attached as children of themselves.
        if not _text(leaf.get("menu_xmlid")):
            continue
        center = center_by_id.get(menu_id)
        if not center:
            continue
        node = centers.setdefault(center["key"], {
            "key": center["key"],
            "name": center["name"],
            "sequence": center["sequence"],
            "scenarios": {},
            "entries": [],
        })
        entry = dict(leaf)
        binding = scenario_by_menu.get(menu_id)
        entry["sequence"] = binding["sequence"] if binding and binding["scenario_active"] else center["entry_sequence"]
        if binding and binding["scenario_active"]:
            entry["intent"] = binding["intent"]
            entry["intent_label"] = binding["intent_label"]
            entry["configured"] = True
            scenario_key = binding["scenario_key"]
            scenario_node = node["scenarios"].setdefault(scenario_key, {
                "key": scenario_key,
                "name": binding["scenario_name"],
                "sequence": binding["scenario_sequence"],
                "entries": [],
            })
            scenario_node["entries"].append(entry)
        else:
            entry["intent"] = ""
            entry["intent_label"] = ""
            entry["configured"] = False
            node["entries"].append(entry)
    center_rows: list[dict[str, Any]] = []
    for center in sorted(centers.values(), key=lambda item: (item["sequence"], item["key"])):
        scenarios = []
        for scenario in sorted(center["scenarios"].values(), key=lambda item: (item["sequence"], item["key"])):
            scenario["entries"].sort(key=lambda item: (item["sequence"], item["menu_xmlid"], item["menu_id"]))
            scenarios.append(scenario)
        center["entries"].sort(key=lambda item: (item["sequence"], item["menu_xmlid"], item["menu_id"]))
        center_rows.append({
            "key": center["key"],
            "name": center["name"],
            "sequence": center["sequence"],
            "scenarios": scenarios,
            "entries": center["entries"],
        })
    scenarioized_nav = _scenarioized_navigation(env, center_rows, route_authority)
    return {
        "ok": True,
        "tree": {"centers": center_rows},
        "nav": scenarioized_nav,
        "diagnostics": {
            "authorized_leaf_count": sum(1 for leaf in leaves if isinstance(leaf, dict) and _text(leaf.get("menu_xmlid") or leaf.get("xmlid"))),
            "center_count": len(center_rows),
            "scenario_count": sum(len(c["scenarios"]) for c in center_rows),
            "unconfigured_entry_count": sum(len(c["entries"]) for c in center_rows),
        },
    }
