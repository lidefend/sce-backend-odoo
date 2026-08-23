# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any


CANONICAL_FORM_STRUCTURE_ROLES = (
    "summary",
    "task",
    "context",
    "risk",
    "relation",
    "activity",
    "audit",
)

FORM_STRUCTURE_SOURCE_ROLE_MAP = {
    "summary": "summary",
    "task": "task",
    "context": "context",
    "risk": "risk",
    "relation": "relation",
    "activity": "activity",
    "audit": "audit",
    "overview": "summary",
    "identity": "context",
    "term": "context",
    "fact": "context",
    "amount": "context",
    "status_or_date": "context",
    "collaboration": "activity",
    "detail": "relation",
    "provenance": "audit",
    "history_check": "audit",
    "business_fact": "context",
    "configured_field": "context",
    "configured_form": "task",
    "configured_field_group": "task",
    "facts": "context",
    "relations": "relation",
    "terms": "context",
    "other_facts": "context",
    "progress": "context",
    "amounts": "context",
    "status_dates": "context",
    "details": "relation",
    "business_category_section": "task",
    "business_category_fields": "context",
}


def canonical_form_structure_role(value: Any) -> str:
    role = str(value or "").strip().lower()
    canonical = FORM_STRUCTURE_SOURCE_ROLE_MAP.get(role)
    if not canonical:
        raise ValueError("unsupported form structure source role: %s" % (role or "<empty>"))
    return canonical


def _canonical_or_default(value: Any, default: str = "context") -> str:
    role = str(value or "").strip()
    return canonical_form_structure_role(role) if role else default


def normalize_form_structure_contract_roles(contract: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(contract, dict):
        raise ValueError("form structure contract must be an object")
    projected_roles: dict[str, dict[str, str]] = {}

    def bind(fields: Any, *, role: str, slot: str, group: str) -> None:
        for value in fields if isinstance(fields, list) else []:
            identity = str(value or "").strip()
            if not identity:
                raise ValueError("form structure field reference is invalid")
            candidate = {"role": role, "slot": slot, "group": group}
            projected_roles[identity] = candidate

    for slot in contract.get("slots") if isinstance(contract.get("slots"), list) else []:
        if not isinstance(slot, dict):
            raise ValueError("form structure slot must be an object")
        slot["role"] = _canonical_or_default(slot.get("role"))
        slot_name = str(slot.get("slot") or "").strip()
        bind(slot.get("fieldRefs"), role=slot["role"], slot=slot_name, group=slot_name)
        for group in slot.get("groups") if isinstance(slot.get("groups"), list) else []:
            if not isinstance(group, dict):
                raise ValueError("form structure group must be an object")
            group["role"] = _canonical_or_default(group.get("role"))
            group_name = str(group.get("name") or "").strip()
            bind(group.get("fieldRefs"), role=group["role"], slot=slot_name, group=group_name)
    field_roles = contract.get("fieldRoles")
    if field_roles is None:
        field_roles = projected_roles
        contract["fieldRoles"] = field_roles
    if not isinstance(field_roles, dict):
        raise ValueError("form structure fieldRoles must be an object")
    for identity, row in field_roles.items():
        if not str(identity or "").strip() or not isinstance(row, dict):
            raise ValueError("form structure field role identity is invalid")
        row["role"] = _canonical_or_default(row.get("role"))
    return contract
