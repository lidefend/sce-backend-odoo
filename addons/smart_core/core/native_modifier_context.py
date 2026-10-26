"""Declared context operands for native modifiers; no source evaluation."""
from __future__ import annotations

from typing import Any

from .native_modifier_comparison import _json_value, compare_python_modifier


def native_modifier_values(contract: dict[str, Any]) -> dict[str, Any]:
    data = contract.get("dataContract", {})
    data = data if isinstance(data, dict) else {}
    main = data.get("mainData")
    values = dict(main) if isinstance(main, dict) else {}
    # This is an evaluator namespace, never a model field or writable draft value.
    values.pop("$native.context", None)
    meta = data.get("dataMeta")
    source = meta.get("sourceContext") if isinstance(meta, dict) else None
    context = source.get("context") if isinstance(source, dict) else None
    if isinstance(context, dict):
        values["$native.context"] = dict(context)
    return values


def _operand(node: Any, record: dict[str, Any]) -> tuple[bool, Any]:
    if not isinstance(node, dict):
        return False, None
    kind = node.get("kind")
    if kind == "literal" and "value" in node:
        value = node["value"]
    elif kind == "field_value" and isinstance(node.get("field"), str) and node["field"].strip() and node["field"] in record:
        value = record[node["field"]]
    elif kind == "context_get":
        context = record.get("$native.context")
        key = node.get("key")
        if not isinstance(context, dict) or not isinstance(key, str) or not _json_value(key):
            return False, None
        if "default" not in node or not _json_value(node["default"]):
            return False, None
        value = context.get(key, node["default"])
    else:
        return False, None
    return _json_value(value), value


def evaluate_context_modifier(node: dict[str, Any], record: dict[str, Any]) -> bool | None:
    if node.get("semantics") != "python":
        return None
    if node.get("kind") == "value_truthy":
        known, value = _operand(node.get("value_expr"), record)
        return bool(value) if known else None
    left_known, left = _operand(node.get("left"), record)
    right_known, right = _operand(node.get("right"), record)
    if not left_known or not right_known:
        return None
    return compare_python_modifier(left, node.get("operator"), right)
