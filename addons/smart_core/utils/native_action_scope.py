# -*- coding: utf-8 -*-
from __future__ import annotations

import ast
from typing import Any


_CURRENT_RECORD_NAMES = frozenset({"id", "active_id", "active_ids", "active_model"})


def native_expression_references_current_record(raw_expr: Any) -> bool:
    """Return whether a native context/domain expression needs the current record.

    Malformed expressions fail closed because they are not sufficient authority
    to expose a stat action while the parent record does not yet exist.
    """
    raw = str(raw_expr or "").strip()
    if not raw:
        return False
    try:
        parsed = ast.parse(raw, mode="eval")
    except (SyntaxError, ValueError, TypeError):
        return True

    for node in ast.walk(parsed):
        if isinstance(node, ast.Name) and node.id in _CURRENT_RECORD_NAMES:
            return True
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "context"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value in _CURRENT_RECORD_NAMES
        ):
            return True
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Name)
            and node.value.id == "context"
            and isinstance(node.slice, ast.Constant)
            and node.slice.value in _CURRENT_RECORD_NAMES
        ):
            return True
    return False


def native_stat_button_requires_record(button_node: Any) -> bool:
    button_type = str(button_node.get("type") or "object").strip().lower()
    if button_type == "object":
        return True
    return any(
        native_expression_references_current_record(button_node.get(attribute))
        for attribute in ("context", "domain")
    )
