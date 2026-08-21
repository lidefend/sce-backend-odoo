#!/usr/bin/env python3
"""Deterministic primitives for governed product-view structure evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET


SCHEMA = "product_view_structure_contract/1.0.0"
FINGERPRINT_SCHEMA = "codex_complete_worktree_fingerprint/v1"
CANONICAL_VIEW_TYPES = {
    "form", "tree", "search", "kanban", "pivot", "graph", "calendar",
    "gantt", "activity", "dashboard",
}
SEMANTIC_ATTRIBUTES = {
    "name", "string", "type", "widget", "groups", "invisible",
    "column_invisible", "readonly", "required", "domain", "context",
    "options", "mode", "editable", "create", "edit", "delete",
    "duplicate", "default_group_by", "default_order", "statusbar_visible",
    "statusbar_status", "filter_domain", "operator", "expand",
    "group_create", "optional", "sum", "avg", "limit", "date_start",
    "date_stop", "color", "scale", "interval", "measure", "confirm",
    "icon", "class", "placeholder", "help", "nolabel", "colspan",
}
SEMANTIC_ATTRIBUTE_PREFIXES = ("decoration-", "t-", "data-")


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def sha256_json(value: Any) -> str:
    return sha256_text(stable_json(value))


def file_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def normalize_view_type(value: Any) -> str:
    view_type = str(value or "").strip().lower()
    return "tree" if view_type == "list" else view_type


def resolve_odoo17_view(Model: Any, requested_view_id: int, view_type: str) -> tuple[dict[str, Any], Any, Any, str]:
    """Resolve Odoo 17 user-visible structure and native provenance."""
    kwargs: dict[str, Any] = {"view_type": view_type}
    if requested_view_id:
        kwargs["view_id"] = requested_view_id
    native_arch, native_view = Model._get_view(**kwargs)
    view_def = Model.get_view(**kwargs)
    if not isinstance(view_def, dict) or not isinstance(view_def.get("arch"), str) or not view_def["arch"].strip():
        raise ValueError("Odoo 17 get_view returned no user-visible arch")
    public_id = int(view_def.get("id") or 0)
    native_id = int(getattr(native_view, "id", 0) or 0)
    if public_id != native_id:
        raise ValueError(f"Odoo 17 public/native selected view mismatch: {public_id} != {native_id}")
    return view_def, native_arch, native_view, "database_view" if native_id else "synthetic_default_view"


def _tag_name(tag: Any) -> str:
    text = str(tag or "")
    return text.rsplit("}", 1)[-1] if "}" in text else text


def _normalized_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _node_payload(node: ET.Element, *, semantic: bool) -> dict[str, Any]:
    attrs: dict[str, str] = {}
    for raw_key, raw_value in sorted(node.attrib.items()):
        key = _tag_name(raw_key)
        if semantic and not (
            key in SEMANTIC_ATTRIBUTES
            or any(key.startswith(prefix) for prefix in SEMANTIC_ATTRIBUTE_PREFIXES)
        ):
            continue
        value = _normalized_text(raw_value)
        if key == "class":
            value = " ".join(sorted(set(value.split())))
        attrs[key] = value
    children = [_node_payload(child, semantic=semantic) for child in list(node) if isinstance(child.tag, str)]
    payload: dict[str, Any] = {"tag": _tag_name(node.tag)}
    if attrs:
        payload["attrs"] = attrs
    text = _normalized_text(node.text)
    if text:
        payload["text"] = text
    if children:
        payload["children"] = children
    return payload


def normalize_arch(arch: str, *, semantic: bool) -> dict[str, Any]:
    if not isinstance(arch, str) or not arch.strip():
        raise ValueError("resolved view arch is empty")
    try:
        root = ET.fromstring(arch)
    except ET.ParseError as exc:
        raise ValueError(f"resolved view arch is invalid XML: {exc}") from exc
    return _node_payload(root, semantic=semantic)


def structure_segment(node: dict[str, Any]) -> str:
    tag = str(node.get("tag") or "node")
    attrs = node.get("attrs") if isinstance(node.get("attrs"), dict) else {}
    for key in ("name", "id", "for", "widget"):
        value = str(attrs.get(key) or "").strip()
        if value:
            return f"{tag}[{key}={value}]"
    identity = {"tag": tag, "attrs": {key: value for key, value in attrs.items() if key != "string"}}
    return f"{tag}[shape={sha256_json(identity)[:12]}]"


def collect_occurrences(structure: dict[str, Any], view_ref: str) -> list[dict[str, Any]]:
    """Return every node occurrence with a stable, duplicate-aware locator."""
    rows: list[dict[str, Any]] = []

    def visit(node: dict[str, Any], parent_locator: str) -> None:
        children = [child for child in node.get("children") or [] if isinstance(child, dict)]
        totals: dict[str, int] = {}
        for child in children:
            base = structure_segment(child)
            totals[base] = totals.get(base, 0) + 1
        seen: dict[str, int] = {}
        for child in children:
            base = structure_segment(child)
            seen[base] = seen.get(base, 0) + 1
            suffix = f"#{seen[base]}" if totals[base] > 1 else ""
            locator = f"{parent_locator}/{base}{suffix}"
            attrs = child.get("attrs") if isinstance(child.get("attrs"), dict) else {}
            rows.append({
                "locator": locator,
                "occurrence_index": seen[base],
                "tag": str(child.get("tag") or ""),
                "name": str(attrs.get("name") or ""),
                "value_sha256": sha256_json(child),
            })
            visit(child, locator)

    root_locator = f"resolved:{view_ref}/{structure_segment(structure)}"
    root_attrs = structure.get("attrs") if isinstance(structure.get("attrs"), dict) else {}
    rows.append({
        "locator": root_locator, "occurrence_index": 1,
        "tag": str(structure.get("tag") or ""), "name": str(root_attrs.get("name") or ""),
        "value_sha256": sha256_json(structure),
    })
    visit(structure, root_locator)
    return rows


def collect_references(occurrences: Iterable[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    fields: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    for row in occurrences:
        item = {key: row[key] for key in ("name", "locator", "occurrence_index", "value_sha256")}
        if row.get("tag") == "field" and row.get("name"):
            fields.append(item)
        if row.get("tag") == "button" and row.get("name"):
            actions.append(item)
    return {"field_occurrences": fields, "action_occurrences": actions}


def policy_menu_rows(policy: dict[str, Any]) -> list[dict[str, Any]]:
    rows_by_menu: dict[str, dict[str, Any]] = {}
    conflicts: list[str] = []
    for product in policy.get("products") or []:
        if not isinstance(product, dict):
            continue
        for row in product.get("capabilities") or []:
            if not isinstance(row, dict) or not row.get("enabled") or row.get("release_state") != "released":
                continue
            menu_xmlid = str(row.get("menu_xmlid") or "").strip()
            model = str(row.get("res_model") or "").strip()
            if not menu_xmlid or not model:
                conflicts.append("released capability requires menu_xmlid and res_model")
                continue
            current = rows_by_menu.get(menu_xmlid)
            if current and current["res_model"] != model:
                conflicts.append(f"{menu_xmlid}: conflicting res_model values")
                continue
            rows_by_menu.setdefault(menu_xmlid, {
                "menu_xmlid": menu_xmlid, "res_model": model,
                "label": str(row.get("label") or "").strip(),
                "visible_menu_path": str(row.get("visible_menu_path") or "").strip(),
                "product_domain": str(row.get("product_domain") or "").strip(),
            })
    if conflicts:
        raise ValueError("; ".join(sorted(conflicts)))
    rows = [rows_by_menu[key] for key in sorted(rows_by_menu)]
    if not rows:
        raise ValueError("formal menu policy resolved zero released capabilities")
    return rows


def content_digest(payload: dict[str, Any], digest_key: str) -> str:
    return sha256_json({key: value for key, value in payload.items() if key != digest_key})
