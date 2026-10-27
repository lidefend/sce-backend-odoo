"""Python comparison semantics over JSON values, without evaluation of source code."""
from __future__ import annotations

import math
from typing import Any


def _json_value(value: Any) -> bool:
    if value is None or type(value) is bool:
        return True
    if type(value) is str:
        return all(not 0xD800 <= ord(char) <= 0xDFFF for char in value)
    if type(value) in (int, float):
        return abs(value) <= 9007199254740991 and math.isfinite(value)
    if type(value) is list:
        return all(_json_value(item) for item in value)
    if type(value) is dict:
        return all(type(key) is str and _json_value(key) and _json_value(item) for key, item in value.items())
    return False


def compare_python_modifier(actual: Any, operator: str, expected: Any) -> bool | None:
    """None is an unsupported/ill-typed comparison, never a false verdict.

    Keep sequences intact. Relational RPC display pairs must be normalized by
    their declared field carrier, not guessed here from an array's shape.
    """
    if not _json_value(actual) or not _json_value(expected):
        return None
    try:
        if operator == "==":
            return actual == expected
        if operator == "!=":
            return actual != expected
        if operator in ("in", "not in"):
            if not isinstance(expected, (str, list, dict)):
                return None
            verdict = actual in expected
            return verdict if operator == "in" else not verdict
        if operator == ">":
            return actual > expected
        if operator == ">=":
            return actual >= expected
        if operator == "<":
            return actual < expected
        if operator == "<=":
            return actual <= expected
    except (TypeError, ValueError):
        return None
    return None
