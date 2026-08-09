# -*- coding: utf-8 -*-
"""Normalize Odoo native view modifiers into the product contract AST."""
from __future__ import annotations

import ast
from typing import Any


def _field_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _field_name(node.value)
        return "%s.%s" % (parent, node.attr) if parent else node.attr
    return ""


def _literal(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return [_literal(item) for item in node.elts]
    if isinstance(node, ast.Name):
        return {"True": True, "False": False, "None": None}.get(node.id, node.id)
    return None


def _operator(node: ast.AST) -> str:
    return {
        ast.Eq: "==",
        ast.NotEq: "!=",
        ast.Gt: ">",
        ast.GtE: ">=",
        ast.Lt: "<",
        ast.LtE: "<=",
        ast.In: "in",
        ast.NotIn: "not in",
    }.get(type(node), "")


def _python_expr(node: ast.AST) -> Any:
    if isinstance(node, ast.Name):
        if node.id in ("True", "False"):
            return node.id == "True"
        return {"kind": "field_truthy", "field": node.id}
    if isinstance(node, ast.Constant):
        return node.value if isinstance(node.value, bool) else {"kind": "static", "value": node.value}
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        child = _python_expr(node.operand)
        return {"kind": "not", "expr": child} if child is not None else None
    if isinstance(node, ast.BoolOp):
        children = [_python_expr(value) for value in node.values]
        children = [value for value in children if value is not None]
        return {"kind": "all" if isinstance(node.op, ast.And) else "any", "exprs": children} if children else None
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1:
        field = _field_name(node.left)
        operator = _operator(node.ops[0])
        if field and operator:
            return {
                "kind": "field_compare",
                "field": field,
                "operator": operator,
                "value": _literal(node.comparators[0]),
            }
    return None


def _domain(value: list[Any]) -> Any:
    if not value:
        return False
    if len(value) == 3 and isinstance(value[0], str) and value[0] not in ("|", "&", "!"):
        return {
            "kind": "field_compare",
            "field": value[0],
            "operator": "==" if value[1] == "=" else value[1],
            "value": value[2],
        }
    stack = list(value)

    def parse() -> Any:
        if not stack:
            return None
        token = stack.pop(0)
        if token in ("|", "&"):
            left, right = parse(), parse()
            return {"kind": "any" if token == "|" else "all", "exprs": [left, right]}
        if token == "!":
            return {"kind": "not", "expr": parse()}
        if isinstance(token, (list, tuple)):
            return _domain(list(token))
        return None

    parsed = parse()
    if parsed is not None and not stack:
        return parsed
    rows = [parsed] if parsed is not None else []
    rows.extend(filter(lambda item: item is not None, (_domain(list(item)) for item in stack if isinstance(item, (list, tuple)))))
    return {"kind": "all", "exprs": rows} if rows else None


def normalize_native_modifier(value: Any) -> Any:
    """Return a JSON-safe modifier AST understood by every product client."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (list, tuple)):
        return _domain(list(value))
    raw = str(value or "").strip()
    if not raw:
        return raw
    if raw in ("1", "true", "True"):
        return True
    if raw in ("0", "false", "False"):
        return False
    try:
        node = _python_expr(ast.parse(raw, mode="eval").body)
    except (SyntaxError, ValueError):
        node = None
    if isinstance(node, dict):
        node.setdefault("raw", raw)
    return node if node is not None else raw
