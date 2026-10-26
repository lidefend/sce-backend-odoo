# -*- coding: utf-8 -*-
"""Normalize Odoo native view modifiers into the product contract AST."""
from __future__ import annotations

import ast
import math
from typing import Any


def _field_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _field_name(node.value)
        return "%s.%s" % (parent, node.attr) if parent else ""
    return ""


def _literal(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        if node.value is None or isinstance(node.value, bool):
            return node.value
        if isinstance(node.value, str) and all(not 0xD800 <= ord(char) <= 0xDFFF for char in node.value):
            return node.value
        if isinstance(node.value, (int, float)) and abs(node.value) <= 9007199254740991 and math.isfinite(node.value):
            return node.value
    if isinstance(node, ast.List):
        return [_literal(item) for item in node.elts]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        value = _literal(node.operand)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return -value if isinstance(node.op, ast.USub) else value
    raise ValueError("unsupported_literal")


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
    if isinstance(node, (ast.Name, ast.Attribute)):
        if isinstance(node, ast.Name) and node.id in ("True", "False"):
            return node.id == "True"
        field = _field_name(node)
        return {"kind": "field_truthy", "field": field} if field else None
    if isinstance(node, ast.Constant):
        return node.value if isinstance(node.value, bool) else {"kind": "static", "value": bool(_literal(node))}
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        child = _python_expr(node.operand)
        return {"kind": "not", "expr": child} if child is not None else None
    if isinstance(node, ast.BoolOp):
        children = [_python_expr(value) for value in node.values]
        if any(value is None for value in children):
            return None
        return {"kind": "all" if isinstance(node.op, ast.And) else "any", "exprs": children} if children else None
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1:
        field = _field_name(node.left)
        operator = _operator(node.ops[0])
        if field and operator:
            normalized = {
                "kind": "field_compare",
                "semantics": "python",
                "field": field,
                "operator": operator,
            }
            comparator = node.comparators[0]
            if isinstance(comparator, ast.Tuple) and operator not in ("in", "not in"):
                return None
            if isinstance(comparator, (ast.Name, ast.Attribute)):
                right_field = _field_name(comparator)
                if right_field and right_field not in ("True", "False", "None"):
                    normalized["value_field"] = right_field
            if "value_field" not in normalized:
                normalized["value"] = _literal(ast.List(elts=comparator.elts) if isinstance(comparator, ast.Tuple) else comparator)
            return normalized
    return None


def _domain(value: list[Any]) -> Any:
    if not value:
        return False
    if len(value) == 3 and isinstance(value[0], str) and value[0] not in ("|", "&", "!"):
        if not value[0] or value[1] not in ("=", "==", "!=", "<>", ">", ">=", "<", "<=", "in", "not in", "like", "ilike"):
            raise ValueError("unsupported_domain_operator")
        return {"kind": "field_compare", "field": value[0],
                "operator": "==" if value[1] == "=" else value[1], "value": value[2]}
    tokens = iter(value)

    def parse(token: Any) -> Any:
        if isinstance(token, str) and token in ("|", "&", "!"):
            left = parse(next(tokens))
            if token == "!":
                return {"kind": "not", "expr": left}
            return {"kind": "any" if token == "|" else "all",
                    "exprs": [left, parse(next(tokens))]}
        if isinstance(token, (list, tuple)):
            return _domain(list(token))
        raise ValueError("unsupported_domain_token")

    rows = []
    try:
        for token in tokens:
            rows.append(parse(token))
    except StopIteration as exc:
        raise ValueError("incomplete_domain") from exc
    return rows[0] if len(rows) == 1 else {"kind": "all", "exprs": rows}


def normalize_native_modifier(value: Any) -> Any:
    """Return a JSON-safe modifier AST understood by every product client."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (list, tuple)):
        try:
            return _domain(list(value))
        except (ValueError, TypeError):
            return {"kind": "unsupported", "raw": repr(value), "reason": "unsupported_domain"}
    raw = "" if value is None else str(value).strip()
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
    if node is None:
        return {"kind": "unsupported", "raw": raw, "reason": "unsupported_expression"}
    if isinstance(node, dict):
        node.setdefault("raw", raw)
    return node
