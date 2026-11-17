"""Deterministic native View and occurrence identity projection.

The module consumes an already-resolved View arch and publishes identity
metadata only. It performs no ORM lookup and grants no permission.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any
import xml.etree.ElementTree as ET


NATIVE_VIEW_IDENTITY_SCHEMA_VERSION = "1.0.0"
NATIVE_OCCURRENCE_KINDS = frozenset({"field", "container", "button", "column", "widget"})


def _text(value: Any) -> str:
    return str(value or "").strip()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _local_tag(element: Any) -> str:
    return str(getattr(element, "tag", "") or "").split("}")[-1]


def _structure_skeleton(root: Any) -> dict[str, Any]:
    position_counts: dict[tuple[str, str], int] = {}

    def walk(element: Any, parent_locator: str = "") -> dict[str, Any] | None:
        tag = _local_tag(element)
        if not tag or not isinstance(getattr(element, "tag", None), str):
            return None
        key = (parent_locator, tag)
        position_counts[key] = position_counts.get(key, 0) + 1
        locator = f"{parent_locator}/{tag}[{position_counts[key]}]"
        node: dict[str, Any] = {
            "locator": locator,
            "type": tag,
        }
        name = _text(element.get("name"))
        if name:
            node["name"] = name
        if tag == "button":
            button_type = _text(element.get("type"))
            if button_type:
                node["buttonType"] = button_type
        children = [
            child
            for raw in element
            if (child := walk(raw, locator)) is not None
        ]
        if children:
            node["children"] = children
        return node

    skeleton = walk(root)
    return skeleton or {}


def build_native_view_identity(
    *,
    model: Any,
    view_type: Any,
    view_id: Any,
    view_xmlid: Any = "",
    arch: Any = "",
    root: Any = None,
) -> dict[str, Any]:
    """Build identity for one effective native View.

    ``viewContentHash`` covers the complete resolved content. The structural
    skeleton excludes display copy, styling and behavioral expressions, so a
    label-only edit changes only the content hash. ``crossEnvironmentStable``
    is true only when authority is rooted in an XMLID.
    """
    normalized_model = _text(model)
    normalized_type = _text(view_type).lower()
    normalized_type = "tree" if normalized_type == "list" else normalized_type
    normalized_xmlid = _text(view_xmlid)
    try:
        normalized_view_id = int(view_id or 0)
    except (TypeError, ValueError):
        normalized_view_id = 0
    if not normalized_model or not normalized_type:
        raise ValueError("native View identity requires model and view type")
    if not arch:
        raise ValueError("native View identity requires resolved arch")
    parsed_root = root
    if parsed_root is None:
        parsed_root = ET.fromstring(str(arch).encode("utf-8"))
    structure = _structure_skeleton(parsed_root)
    if not structure:
        raise ValueError("native View identity requires a structural root")
    return {
        "schemaVersion": NATIVE_VIEW_IDENTITY_SCHEMA_VERSION,
        "model": normalized_model,
        "viewType": normalized_type,
        "viewId": normalized_view_id,
        "viewXmlId": normalized_xmlid,
        "viewContentHash": _sha256({
            "model": normalized_model,
            "viewType": normalized_type,
            "viewXmlId": normalized_xmlid,
            "arch": str(arch),
        }),
        "viewStructureKey": "struct.v1." + _sha256(structure)[:24],
        "crossEnvironmentStable": bool(normalized_xmlid),
        "sourceAuthority": {
            "kind": "ir.ui.view",
            "projectionOnly": True,
            "noBusinessFactAuthority": True,
        },
    }


def build_native_occurrence_identity(
    view_identity: Any,
    *,
    kind: Any,
    name: Any,
    native_locator: Any,
    occurrence_index: Any,
    source_position: Any = None,
    authoritative: bool = True,
    native_attributes: Any = None,
) -> dict[str, Any]:
    """Build one deterministic occurrence identity from native evidence only."""
    view = view_identity if isinstance(view_identity, dict) else {}
    normalized_kind = _text(kind).lower()
    normalized_name = _text(name)
    normalized_locator = _text(native_locator)
    try:
        normalized_index = int(occurrence_index or 0)
    except (TypeError, ValueError):
        normalized_index = 0
    if normalized_kind not in NATIVE_OCCURRENCE_KINDS:
        raise ValueError("native occurrence kind is invalid")
    if not normalized_name or not normalized_locator or normalized_index <= 0:
        raise ValueError("native occurrence identity is incomplete")
    required_view_keys = {
        "model",
        "viewType",
        "viewContentHash",
        "viewStructureKey",
        "crossEnvironmentStable",
    }
    if not required_view_keys.issubset(view):
        raise ValueError("native View identity is incomplete")
    view_xmlid = _text(view.get("viewXmlId"))
    view_id = int(view.get("viewId") or 0)
    base_identity = (
        {
            "viewXmlId": view_xmlid,
            "model": _text(view.get("model")),
            "viewType": _text(view.get("viewType")),
            "crossEnvironmentStable": True,
        }
        if view_xmlid
        else {
            "viewId": view_id,
            "model": _text(view.get("model")),
            "viewType": _text(view.get("viewType")),
            "crossEnvironmentStable": False,
        }
    )
    occurrence_key = "occ.v1." + _sha256({
        "viewBaseIdentity": base_identity,
        "kind": normalized_kind,
        "name": normalized_name,
        "nativeLocator": normalized_locator,
        "occurrenceIndex": normalized_index,
    })[:24]
    result: dict[str, Any] = {
        "schemaVersion": NATIVE_VIEW_IDENTITY_SCHEMA_VERSION,
        "model": _text(view.get("model")),
        "viewType": _text(view.get("viewType")),
        "viewId": view_id,
        "viewXmlId": view_xmlid,
        "viewContentHash": _text(view.get("viewContentHash")),
        "viewStructureKey": _text(view.get("viewStructureKey")),
        "crossEnvironmentStable": bool(view.get("crossEnvironmentStable")),
        "kind": normalized_kind,
        "name": normalized_name,
        "nativeLocator": normalized_locator,
        "occurrenceIndex": normalized_index,
        "occurrenceKey": occurrence_key,
        "authoritative": bool(authoritative),
        "sourceAuthority": {
            "kind": "ir.ui.view",
            "projectionOnly": True,
            "noBusinessFactAuthority": True,
        },
    }
    if source_position is not None:
        try:
            normalized_source_position = int(source_position)
        except (TypeError, ValueError):
            normalized_source_position = -1
        if normalized_source_position >= 0:
            result["sourcePosition"] = normalized_source_position
    attributes = native_attributes if isinstance(native_attributes, dict) else {}
    native_behavior = {
        source_key: _text(attributes.get(source_key))
        for source_key in ("domain", "context", "options")
        if _text(attributes.get(source_key))
    }
    if native_behavior:
        result["nativeBehavior"] = {
            "domainRaw": native_behavior.get("domain", ""),
            "contextRaw": native_behavior.get("context", ""),
            "optionsRaw": native_behavior.get("options", ""),
        }
    return result
