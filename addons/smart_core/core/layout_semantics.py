# -*- coding: utf-8 -*-
"""Layout Adapter semantic normalization (BNVA-019 Stage 3C-03B).

Container-title and technical-identifier heuristics for the native form layout.
This is a layout-presentation concern: it normalizes container labels and
layout node annotations only.  It must never derive Identity, Section,
fieldOwnership or a field business role.
"""
from __future__ import annotations

import re
from typing import Any

from .unified_page_contract_v2_assembler import (
    NOTE_FIELD_TOKENS,
    SOURCE_KIND,
    TRACE_FIELD_TOKENS,
    _dict,
    _list,
    _stable_id,
    _text,
    _walk_native_nodes,
)


def _node_field_names(node: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for item in _walk_native_nodes([node]):
        if _text(item.get("type") or item.get("kind")).lower() != "field":
            continue
        field_name = _text(item.get("name") or item.get("field"))
        if field_name and field_name not in out:
            out.append(field_name)
    return out


def _node_field_types(node: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for item in _walk_native_nodes([node]):
        if _text(item.get("type") or item.get("kind")).lower() != "field":
            continue
        field_info = _dict(item.get("fieldInfo") or item.get("field_info"))
        field_type = _text(field_info.get("type") or field_info.get("ttype") or item.get("widget")).lower()
        if field_type:
            out.append(field_type)
    return out


def _node_text_fingerprint(node: dict[str, Any]) -> str:
    values: list[str] = []
    for item in _walk_native_nodes([node]):
        values.extend([
            _text(item.get("name") or item.get("field")).lower(),
            _text(item.get("string") or item.get("label") or item.get("title")).lower(),
        ])
        field_info = _dict(item.get("fieldInfo") or item.get("field_info"))
        values.extend([
            _text(field_info.get("string") or field_info.get("label")).lower(),
            _text(field_info.get("name")).lower(),
        ])
    return " ".join(item for item in values if item)


def _node_has_token(node: dict[str, Any], tokens: tuple[str, ...]) -> bool:
    fingerprint = _node_text_fingerprint(node)
    return any(token.lower() in fingerprint for token in tokens)


def _node_has_x2many(node: dict[str, Any]) -> bool:
    return any(field_type in {"one2many", "many2many"} for field_type in _node_field_types(node))


def _node_has_direct_group_child(node: dict[str, Any]) -> bool:
    for key in ("children", "pages", "tabs", "nodes", "items"):
        child_rows = node.get(key)
        if not isinstance(child_rows, list):
            continue
        for child in child_rows:
            if not isinstance(child, dict):
                continue
            child_type = _text(child.get("type") or child.get("kind") or child.get("containerType")).lower()
            if child_type == "group":
                return True
    return False


def _is_generic_container_label(node: dict[str, Any]) -> bool:
    """Report whether a container carries no authored heading of its own.

    ``generic`` holds the values that are container identities rather than
    headings: the absence of a label, the container type, and a technical
    container id/name.  A label is a heading only when it is non-empty and
    differs from every identity value.  The empty string must never be
    intersected directly: as soon as one of title/label/string is absent the
    label set contains it, so a set intersection would mark every group
    generic and would let a structural guess replace an authored title.
    """
    node_type = _text(node.get("containerType") or node.get("type") or node.get("kind")).lower()
    generic = {"", node_type}
    container_id = _text(node.get("containerId")).lower()
    node_name = _text(node.get("name")).lower()
    if _is_technical_container_identifier(container_id):
        generic.add(container_id)
    if _is_technical_container_identifier(node_name):
        generic.add(node_name)
    labels = (
        _text(node.get("title")).lower(),
        _text(node.get("label")).lower(),
        _text(node.get("string")).lower(),
    )
    return not any(label and label not in generic for label in labels)


def _is_technical_container_identifier(value: str) -> bool:
    if not value:
        return False
    return bool(re.fullmatch(r"[a-z0-9_.:-]+", value))


def _semantic_group_label(node: dict[str, Any], *, level: int, index: int) -> str:
    fingerprint = _node_text_fingerprint(node)
    field_names = set(_node_field_names(node))
    if level <= 1 and _node_has_direct_group_child(node):
        return "主信息"
    if _node_has_token(node, TRACE_FIELD_TOKENS):
        return "来源追溯"
    if _node_has_token(node, NOTE_FIELD_TOKENS):
        return "备注说明"
    if _node_has_x2many(node):
        return "业务明细"
    if any(token in fingerprint for token in ("amount", "price", "cost", "budget", "fee", "money", "金额", "费用", "成本", "预算")):
        return "金额信息"
    if any(token in fingerprint for token in ("date", "time", "deadline", "start", "end", "日期", "时间", "截止")):
        return "时间信息"
    if any(token in fingerprint for token in ("partner", "supplier", "owner", "manager", "user", "负责人", "供应", "往来", "经理")):
        return "责任与往来"
    if level <= 1 or field_names & {"name", "code", "project_id", "state", "company_id"}:
        return "主信息" if level == 0 else "基础信息"
    return f"业务信息 {index + 1}"


def _apply_semantic_container_label(node: dict[str, Any], label: str) -> None:
    _apply_semantic_container_annotation(node, label)


def _apply_semantic_container_annotation(node: dict[str, Any], label: str) -> None:
    node["semanticTitle"] = label
    node["semanticAnchor"] = _stable_id(label, "semantic.group")
    source = _dict(node.get("sourceAuthority"))
    source.update({
        "kind": SOURCE_KIND,
        "projection_only": True,
        "no_business_fact_authority": True,
        "runtime_carrier": "business_form_semantic_label_standardizer",
    })
    node["sourceAuthority"] = source


def _business_group_label_for_node(source: dict[str, Any], node: dict[str, Any]) -> str:
    groups = _list(source.get("field_groups"))
    business_groups: list[tuple[str, str, set[str]]] = []
    for group in groups:
        if not isinstance(group, dict):
            continue
        name = _text(group.get("name")).lower()
        if not name.startswith("business_"):
            continue
        fields = {_text(item) for item in _list(group.get("fields")) if _text(item)}
        if not fields:
            continue
        label = _text(group.get("label") or group.get("title") or group.get("string"))
        if label:
            business_groups.append((name, label, fields))
    if not business_groups:
        return ""
    node_fields = set(_node_field_names(node))
    if not node_fields:
        return ""
    ranked = sorted(
        (
            (len(node_fields & fields), name, label)
            for name, label, fields in business_groups
            if node_fields & fields
        ),
        key=lambda item: (
            item[0],
            4 if item[1] == "business_collaboration" else 3 if item[1] == "business_details" else 2 if item[1] == "business_amount" else 1,
        ),
        reverse=True,
    )
    return ranked[0][2] if ranked else ""


def standardize_form_container_semantics(nodes: list[dict[str, Any]], *, model: str, view_type: str, source: dict[str, Any] | None = None) -> None:
    if view_type != "form" or not model:
        return

    def visit(rows: list[dict[str, Any]], *, level: int) -> None:
        group_index = 0
        for node in rows:
            if not isinstance(node, dict):
                continue
            node_type = _text(node.get("containerType") or node.get("type") or node.get("kind")).lower()
            if node_type == "group":
                if _is_generic_container_label(node):
                    business_label = _business_group_label_for_node(_dict(source), node)
                    _apply_semantic_container_label(
                        node,
                        business_label or _semantic_group_label(node, level=level, index=group_index),
                    )
                else:
                    semantic_title = _text(node.get("semanticTitle"))
                    visible_label = _text(node.get("title") or node.get("label") or node.get("string"))
                    if not semantic_title and visible_label:
                        _apply_semantic_container_annotation(node, visible_label)
                group_index += 1
            for key in ("children", "pages", "tabs", "nodes", "items"):
                child_rows = node.get(key)
                if isinstance(child_rows, list):
                    visit([item for item in child_rows if isinstance(item, dict)], level=level + 1)

    visit(nodes, level=0)

