#!/usr/bin/env python3
"""Deterministic helpers for product view-structure contracts."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable
from xml.etree import ElementTree as ET


SCHEMA = "product_view_structure_contract/1.0.0"
SEMANTIC_ATTRIBUTES = {
    "name", "string", "type", "widget", "groups", "invisible", "readonly",
    "required", "domain", "context", "options", "mode", "editable", "create",
    "edit", "delete", "default_group_by", "statusbar_visible", "statusbar_status",
    "filter_domain", "expand", "group_create",
}
SEMANTIC_ATTRIBUTE_PREFIXES = ("decoration-", "t-", "data-")


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_text(stable_json(value))


def normalize_view_type(value: Any) -> str:
    view_type = str(value or "").strip().lower()
    return "tree" if view_type == "list" else view_type


def _tag_name(tag: Any) -> str:
    text = str(tag or "")
    return text.rsplit("}", 1)[-1] if "}" in text else text


def _normalized_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _node_payload(node: ET.Element, *, semantic: bool) -> dict[str, Any]:
    attrs = {}
    for raw_key, raw_value in sorted(node.attrib.items()):
        key = _tag_name(raw_key)
        if semantic and not (
            key in SEMANTIC_ATTRIBUTES
            or any(key.startswith(prefix) for prefix in SEMANTIC_ATTRIBUTE_PREFIXES)
        ):
            continue
        attrs[key] = _normalized_text(raw_value)
    children = [
        _node_payload(child, semantic=semantic)
        for child in list(node)
        if isinstance(child.tag, str)
    ]
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


def collect_references(structure: dict[str, Any]) -> dict[str, list[str]]:
    fields: set[str] = set()
    actions: set[str] = set()

    def visit(node: Any) -> None:
        if not isinstance(node, dict):
            return
        tag = str(node.get("tag") or "")
        attrs = node.get("attrs") if isinstance(node.get("attrs"), dict) else {}
        name = str(attrs.get("name") or "").strip()
        if tag == "field" and name:
            fields.add(name)
        if tag == "button" and name:
            actions.add(name)
        for child in node.get("children") or []:
            visit(child)

    visit(structure)
    return {"field_refs": sorted(fields), "action_refs": sorted(actions)}


def policy_menu_rows(policy: dict[str, Any]) -> list[dict[str, Any]]:
    rows_by_menu: dict[str, dict[str, Any]] = {}
    conflicts: list[str] = []
    for product in policy.get("products") or []:
        if not isinstance(product, dict):
            continue
        for row in product.get("capabilities") or []:
            if not isinstance(row, dict):
                continue
            if not row.get("enabled") or str(row.get("release_state") or "") != "released":
                continue
            menu_xmlid = str(row.get("menu_xmlid") or "").strip()
            model = str(row.get("res_model") or "").strip()
            if not menu_xmlid:
                conflicts.append("released capability has no menu_xmlid")
                continue
            current = rows_by_menu.get(menu_xmlid)
            if current and str(current.get("res_model") or "") != model:
                conflicts.append(
                    f"{menu_xmlid}: conflicting res_model values "
                    f"{current.get('res_model')!r} and {model!r}"
                )
                continue
            rows_by_menu.setdefault(
                menu_xmlid,
                {
                    "menu_xmlid": menu_xmlid,
                    "res_model": model,
                    "label": str(row.get("label") or "").strip(),
                    "visible_menu_path": str(row.get("visible_menu_path") or "").strip(),
                    "product_domain": str(row.get("product_domain") or "").strip(),
                },
            )
    if conflicts:
        raise ValueError("; ".join(sorted(conflicts)))
    return [rows_by_menu[key] for key in sorted(rows_by_menu)]


def manifest_digest(entries: Iterable[dict[str, Any]]) -> str:
    return sha256_json(list(entries))
