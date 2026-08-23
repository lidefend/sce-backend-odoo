#!/usr/bin/env python3
"""Recognize the governed audit disclosure without relying on stale source tokens."""

from __future__ import annotations

import re


_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_DETAILS = re.compile(r"<details\b(?P<attributes>[^>]*)>", re.IGNORECASE | re.DOTALL)
_AUDIT_REGION = re.compile(
    r"\bdata-floorplan-region\s*=\s*(['\"])audit\1",
    re.IGNORECASE,
)
_V_IF = re.compile(r"\bv-if\s*=\s*(['\"])(?P<expression>.*?)\1", re.DOTALL)


def _template_source(source: str) -> str:
    return _COMMENT.sub("", source.split("<script", 1)[0])


def _has_exact_content_condition(attributes: str) -> bool:
    match = _V_IF.search(attributes)
    if not match:
        return False
    expression = re.sub(r"[\s()]", "", match.group("expression"))
    return expression in {
        "auditNodes.length||auditEvents.length",
        "auditEvents.length||auditNodes.length",
    }


def audit_disclosure_is_governed(source: str) -> bool:
    """Require one content-backed, initially collapsed audit details element."""
    matches = [
        match.group("attributes")
        for match in _DETAILS.finditer(_template_source(source))
        if _AUDIT_REGION.search(match.group("attributes"))
    ]
    if len(matches) != 1:
        return False
    attributes = matches[0]
    if re.search(r"\bopen\b", attributes, re.IGNORECASE):
        return False
    return _has_exact_content_condition(attributes)
