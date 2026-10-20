# -*- coding: utf-8 -*-
"""Pure projection for the product configuration capability catalog."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "product_configuration_capability.v1"
AUDIENCE_ORDER = ("platform_admin", "support", "business_config_admin", "business_full")
PRIMARY_AUDIENCE_ORDER = ("platform_admin", "business_config_admin", "business_full", "support")


def load_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("product capability manifest must be an object")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unexpected product capability manifest schema")
    return payload


def _has_group(user, xmlid: str) -> bool:
    checker = getattr(user, "has_group", None)
    if not callable(checker):
        return False
    try:
        return bool(checker(xmlid))
    except Exception:
        return False


def resolve_audiences(user) -> list[str]:
    matched: set[str] = set()
    if _has_group(user, "smart_core.group_smart_core_admin") or _has_group(
        user, "smart_construction_core.group_sc_super_admin"
    ):
        matched.update({"platform_admin", "support"})
    if _has_group(
        user, "smart_construction_core.group_sc_cap_config_admin"
    ) or _has_group(user, "smart_construction_core.group_sc_cap_business_config_admin"):
        matched.add("business_config_admin")
    if _has_group(user, "smart_construction_core.group_sc_business_full"):
        matched.add("business_full")
    return [key for key in AUDIENCE_ORDER if key in matched]


def _capability_reason(status: str) -> str:
    return "available" if status in ("available", "partial") else "planned"


def build_catalog(manifest: dict[str, Any], audiences: Iterable[str]) -> dict[str, Any]:
    effective = set(audiences)
    if "business_config_admin" in effective:
        effective.add("business_full")
    if "platform_admin" in effective:
        effective.add("support")

    capabilities: list[dict[str, Any]] = []
    status_by_key: dict[str, str] = {}
    for row in manifest.get("capabilities", []):
        if not isinstance(row, dict) or row.get("audience") not in effective:
            continue
        key = str(row.get("key") or "").strip()
        status = str(row.get("status") or "").strip()
        status_by_key[key] = status
        capabilities.append(
            {
                "key": key,
                "label": str(row.get("label") or "").strip(),
                "audience": str(row.get("audience") or "").strip(),
                "status": status,
                "available": status in ("available", "partial"),
                "reason": _capability_reason(status),
                "entry": str(row.get("entry") or "").strip(),
                "authority": str(row.get("authority") or "").strip(),
                "description": str(row.get("description") or "").strip(),
            }
        )

    login_home: dict[str, Any] = {}
    if "business_full" in effective:
        source_home = manifest.get("login_home") if isinstance(manifest.get("login_home"), dict) else {}
        blocks: list[dict[str, Any]] = []
        for block in source_home.get("blocks", []):
            if not isinstance(block, dict):
                continue
            key = str(block.get("key") or "").strip()
            capability_status = status_by_key.get("workspace." + key, "")
            available = capability_status in ("available", "partial") if capability_status else True
            blocks.append(
                {
                    "key": key,
                    "label": str(block.get("label") or "").strip(),
                    "required": bool(block.get("required")),
                    "authority": str(block.get("authority") or "").strip(),
                    "available": available,
                    "reason": "available" if available else "planned",
                }
            )
        login_home = {
            "audience": str(source_home.get("audience") or "").strip(),
            "blocks": blocks,
            "empty_state_policy": dict(source_home.get("empty_state_policy") or {}),
        }

    configuration_cards: list[dict[str, Any]] = []
    system_parameter_categories: list[dict[str, Any]] = []
    if "business_config_admin" in effective:
        for card in manifest.get("configuration_cards", []):
            if not isinstance(card, dict):
                continue
            status = str(card.get("status") or "").strip()
            configuration_cards.append(
                {
                    "key": str(card.get("key") or "").strip(),
                    "label": str(card.get("label") or "").strip(),
                    "status": status,
                    "available": status in ("available", "partial"),
                    "reason": _capability_reason(status),
                    "entry": str(card.get("entry") or "").strip(),
                    "authority": str(card.get("authority") or "").strip(),
                }
            )
        system_parameter_categories = [
            dict(row)
            for row in manifest.get("system_parameter_categories", [])
            if isinstance(row, dict)
        ]

    audience_rows = [
        dict(row)
        for row in manifest.get("audiences", [])
        if isinstance(row, dict) and row.get("key") in effective
    ]
    primary_audience = next(
        (key for key in PRIMARY_AUDIENCE_ORDER if key in effective),
        "",
    )
    return {
        "schema_version": str(manifest.get("schema_version") or "").strip(),
        "manifest_status": str(manifest.get("status") or "").strip(),
        "objective": str(manifest.get("objective") or "").strip(),
        "primary_audience": primary_audience,
        "audiences": audience_rows,
        "login_home": login_home,
        "configuration_cards": configuration_cards,
        "system_parameter_categories": system_parameter_categories,
        "capabilities": capabilities,
        "guardrails": list(manifest.get("guardrails") or []),
        "reason": "" if effective else "no_declared_capability_audience",
    }
