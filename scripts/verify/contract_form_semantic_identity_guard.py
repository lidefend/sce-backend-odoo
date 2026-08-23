#!/usr/bin/env python3
"""Validate lossless formStructureRole projection without stale source markers."""

from __future__ import annotations

import re


def _strip_comments_and_strings(source: str) -> str:
    output: list[str] = []
    index = 0
    state = "code"
    quote = ""
    while index < len(source):
        char = source[index]
        next_char = source[index + 1] if index + 1 < len(source) else ""
        if state == "code":
            if char == "/" and next_char == "/":
                output.extend("  ")
                index += 2
                state = "line_comment"
                continue
            if char == "/" and next_char == "*":
                output.extend("  ")
                index += 2
                state = "block_comment"
                continue
            if char in {"'", '"', "`"}:
                quote = char
                output.append(" ")
                index += 1
                state = "string"
                continue
            output.append(char)
            index += 1
            continue
        if state == "line_comment":
            output.append("\n" if char == "\n" else " ")
            index += 1
            if char == "\n":
                state = "code"
            continue
        if state == "block_comment":
            output.append("\n" if char == "\n" else " ")
            if char == "*" and next_char == "/":
                output.append(" ")
                index += 2
                state = "code"
            else:
                index += 1
            continue
        output.append("\n" if char == "\n" else " ")
        if char == "\\" and next_char:
            output.append("\n" if next_char == "\n" else " ")
            index += 2
        elif char == quote:
            index += 1
            state = "code"
        else:
            index += 1
    return "".join(output)


def _section(source: str, start: str, end: str) -> str:
    start_match = re.search(rf"\bfunction\s+{re.escape(start)}\s*\(", source)
    if not start_match:
        return ""
    end_match = re.search(
        rf"\bfunction\s+{re.escape(end)}\s*\(",
        source[start_match.end():],
    )
    if not end_match:
        return ""
    return source[start_match.start():start_match.end() + end_match.start()]


def _property_uses(block: str, property_name: str, variable: str, member: str) -> bool:
    return re.search(
        rf"\b{re.escape(property_name)}\s*:\s*{re.escape(variable)}\s*\.\s*{re.escape(member)}\b",
        block,
    ) is not None


def validate_semantic_identity_projection(source: str) -> list[str]:
    """Require field and node role/slot/group projection from normalized authority."""
    code = _strip_comments_and_strings(source)
    errors: list[str] = []

    identity = _section(code, "semanticIdentity", "fieldSemanticIdentity")
    for property_name, expression in (
        ("role", r"semanticRole\s*\(\s*structure\s*\)"),
        ("slot", r"text\s*\(\s*structure\s*\.\s*slot\s*\)"),
        ("group", r"text\s*\(\s*structure\s*\.\s*group\s*\)"),
    ):
        if not re.search(rf"\b{property_name}\s*:\s*{expression}", identity):
            errors.append(f"semanticIdentity does not preserve {property_name}")

    field_identity = _section(code, "fieldSemanticIdentity", "zoneRole")
    widget_match = re.search(
        r"\bconst\s+(\w+)\s*=\s*semanticIdentity\s*\(\s*widget\s*\.\s*formStructureRole\s*\)",
        field_identity,
    )
    container_match = re.search(
        r"\bconst\s+(\w+)\s*=\s*semanticIdentity\s*\(\s*container\s*\.\s*formStructureRole\s*\)",
        field_identity,
    )
    if not widget_match or not container_match:
        errors.append("field semantics do not consume widget and container formStructureRole")
    else:
        widget_identity = widget_match.group(1)
        container_identity = container_match.group(1)
        for member in ("role", "slot", "group"):
            if not re.search(
                rf"\b{member}\s*:\s*{re.escape(widget_identity)}\s*\.\s*{member}"
                rf"\s*\|\|\s*{re.escape(container_identity)}\s*\.\s*{member}\b",
                field_identity,
            ):
                errors.append(f"field semantics do not preserve widget-first {member} authority")

    field_projection = _section(code, "fieldFromWidget", "childCollections")
    field_match = re.search(
        r"\bconst\s+(\w+)\s*=\s*fieldSemanticIdentity\s*\(\s*widget\s*,\s*container\s*\)",
        field_projection,
    )
    if not field_match:
        errors.append("canonical field projection does not consume fieldSemanticIdentity")
    else:
        variable = field_match.group(1)
        for property_name, member in (
            ("semanticRole", "role"),
            ("semanticSlot", "slot"),
            ("semanticGroup", "group"),
        ):
            if not _property_uses(field_projection, property_name, variable, member):
                errors.append(f"canonical field projection loses {property_name}")

    node_projection = _section(code, "presentNode", "actionTier")
    node_match = re.search(
        r"\bconst\s+(\w+)\s*=\s*semanticIdentity\s*\(\s*container\s*\.\s*formStructureRole\s*\)",
        node_projection,
    )
    if not node_match:
        errors.append("canonical node projection does not consume container formStructureRole")
    else:
        variable = node_match.group(1)
        for property_name, member in (
            ("semanticRole", "role"),
            ("semanticSlot", "slot"),
            ("semanticGroup", "group"),
        ):
            if not _property_uses(node_projection, property_name, variable, member):
                errors.append(f"canonical node projection loses {property_name}")
    return errors
