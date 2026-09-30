# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Callable


_ENTERPRISE_COMPANY_FIELD_LABELS: dict[str, str] = {}
_ENTERPRISE_USER_FIELD_LABELS: dict[str, str] = {}


def _safe_text(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    if text.lower() in {"undefined", "null"}:
        text = ""
    return text or fallback


def _safe_lower(value: Any) -> str:
    return _safe_text(value).lower()


def _as_dict(value: Any) -> dict:
    return dict(value) if isinstance(value, dict) else {}


def collect_layout_field_names(nodes: Any) -> list[str]:
    ordered: list[str] = []

    def _iter_children(node: dict) -> list[list]:
        rows: list[list] = []
        for key in ("children", "tabs", "pages", "nodes", "items"):
            candidate = node.get(key)
            if isinstance(candidate, list):
                rows.append(candidate)
        return rows

    def _collect(items: list) -> None:
        for node in items:
            if not isinstance(node, dict):
                continue
            if _safe_lower(node.get("type")) == "field":
                name = _safe_text(node.get("name"))
                if name and name not in ordered:
                    ordered.append(name)
            for children in _iter_children(node):
                _collect(children)

    if isinstance(nodes, list):
        _collect(nodes)
    elif isinstance(nodes, dict):
        _collect([nodes])
    return ordered


def find_layout_sheet_node(nodes: Any) -> dict | None:
    if isinstance(nodes, dict):
        nodes = [nodes]
    if not isinstance(nodes, list):
        return None
    for node in nodes:
        if not isinstance(node, dict):
            continue
        if _safe_lower(node.get("type")) == "sheet":
            return node
        for key in ("children", "tabs", "pages", "nodes", "items"):
            candidate = node.get(key)
            if isinstance(candidate, list):
                found = find_layout_sheet_node(candidate)
                if found:
                    return found
    return None


_NATIVE_OCCURRENCE_CHILD_KEYS = ("children", "tabs", "pages", "nodes", "items")


def _native_field_identity(raw: dict) -> dict[str, Any] | None:
    """Return a native occurrence identity only when it is complete.

    A partial identity is not a usable position: the native form projection
    validator rejects a node whose locator is empty or whose occurrence index
    is not positive, so an incomplete occurrence must not be offered as
    projectable in the first place.
    """
    locator = _safe_text(raw.get("native_locator") or raw.get("nativeLocator"))
    if not locator:
        return None
    try:
        occurrence_index = int(raw.get("occurrence_index", raw.get("occurrenceIndex")))
        source_position = int(raw.get("source_position", raw.get("sourcePosition")))
    except (TypeError, ValueError):
        return None
    if occurrence_index <= 0 or source_position < 0:
        return None
    return {
        "native_locator": locator,
        "occurrence_index": occurrence_index,
        "source_position": source_position,
    }


def collect_native_field_occurrences(nodes: Any) -> dict[str, dict[str, Any]]:
    """Index the field occurrences carried by a resolved native form layout.

    The flat field configuration is a presentation overlay: it may choose a
    field's label, its group and its order, but it may not invent an
    occurrence.  Projecting a field therefore requires a real occurrence in
    the native view to carry the position identity, and this index is the
    authority that overlay projects onto.

    A field can occur more than once in a native view (a visible input inside
    the sheet plus a carrier outside it).  The sheet occurrence is the one the
    native form actually renders, so it wins regardless of document order.
    """
    occurrences: dict[str, dict[str, Any]] = {}
    inside_sheet: dict[str, bool] = {}

    def _walk(items: Any, *, in_sheet: bool) -> None:
        if not isinstance(items, list):
            return
        for raw in items:
            if not isinstance(raw, dict):
                continue
            node_type = _safe_lower(raw.get("type"))
            node_in_sheet = in_sheet or node_type == "sheet"
            if node_type == "field":
                name = _safe_text(raw.get("name"))
                identity = _native_field_identity(raw)
                if name and identity and (name not in occurrences or (node_in_sheet and not inside_sheet[name])):
                    occurrences[name] = identity
                    inside_sheet[name] = node_in_sheet
            for key in _NATIVE_OCCURRENCE_CHILD_KEYS:
                _walk(raw.get(key), in_sheet=node_in_sheet)

    if isinstance(nodes, dict):
        nodes = [nodes]
    _walk(nodes, in_sheet=False)
    return occurrences


def apply_native_field_identity(node: dict[str, Any], identity: dict[str, Any] | None) -> dict[str, Any]:
    """Stamp a projected node with the native occurrence it stands for."""
    for key in ("native_locator", "occurrence_index", "source_position"):
        value = (identity or {}).get(key)
        if value is not None:
            node[key] = value
    return node


def make_labeled_field_node(
    name: str,
    fields_map: dict[str, Any],
    preferred_labels: dict[str, str] | None = None,
) -> dict[str, Any]:
    descriptor = _as_dict(fields_map.get(name))
    label = _safe_text((preferred_labels or {}).get(name), "")
    if not label:
        label = _safe_text(_ENTERPRISE_USER_FIELD_LABELS.get(name) or _ENTERPRISE_COMPANY_FIELD_LABELS.get(name), "")
    if not label:
        label = _safe_text(descriptor.get("string") if descriptor else "", name)
    ttype = _safe_lower(descriptor.get("type") or descriptor.get("ttype"))
    widget = _safe_text(descriptor.get("widget"))
    if not widget:
        widget = {
            "many2one": "many2one",
            "one2many": "one2many_list",
            "many2many": "many2many_tags",
            "boolean": "boolean",
            "date": "date",
            "datetime": "datetime",
            "text": "textarea",
            "html": "html",
            "binary": "image",
        }.get(ttype, "")
    node = {"type": "field", "name": name}
    if label:
        node["string"] = label
    node["fieldInfo"] = {
        "name": name,
        "label": label or name,
    }
    if widget:
        node["fieldInfo"]["widget"] = widget
    return node


def backfill_form_layout_from_visible_fields(
    data: dict,
    *,
    is_form_contract: Callable[[dict], bool],
    is_technical_field: Callable[[str, dict], bool],
) -> None:
    if not is_form_contract(data):
        return
    fields_map = _as_dict(data.get("fields"))
    if not fields_map:
        return
    visible_fields = [
        _safe_text(name)
        for name in (data.get("visible_fields") or [])
        if _safe_text(name) in fields_map
    ]
    if not visible_fields:
        return

    views = _as_dict(data.get("views"))
    form = _as_dict(views.get("form"))
    layout = form.get("layout")
    if not isinstance(layout, list) or not layout:
        return

    existing = set(collect_layout_field_names(layout))
    missing = [
        name
        for name in visible_fields
        if name not in existing and not is_technical_field(name, _as_dict(fields_map.get(name)))
    ]
    if not missing:
        return

    backfill_group = {
        "type": "group",
        "name": "visible_fields_backfill_group",
        "string": "补充业务信息",
        "children": [
            make_labeled_field_node(name, fields_map)
            for name in missing
        ],
    }

    target = find_layout_sheet_node(layout)
    if target:
        children = target.get("children")
        if not isinstance(children, list):
            children = []
        children.append(backfill_group)
        target["children"] = children
    else:
        layout.append(backfill_group)
    form["layout"] = layout
    views["form"] = form
    data["views"] = views
