# -*- coding: utf-8 -*-
"""Platform validation for the terminal business-task scene profile.

The profile is embedded in a Scene Contract and is the only part a business
renderer needs to understand.  Native/Odoo vocabulary belongs to compiler
inputs and diagnostics, never to this terminal profile.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Tuple


REQUIRED_SECTIONS = (
    "profile_version",
    "task",
    "facts",
    "inputs",
    "blockers",
    "capabilities",
    "evidence",
    "relations",
    "completion",
)

FORBIDDEN_TERMINAL_KEYS = {
    "model",
    "res_model",
    "view_type",
    "view_id",
    "xml_id",
    "xmlid",
    "notebook",
    "modifier",
    "modifiers",
    "odoo_action",
    "server_action_id",
}

_NON_ALNUM = re.compile(r"[^a-z0-9]+")
FORBIDDEN_TERMINAL_KEY_TOKENS = {
    _NON_ALNUM.sub("", key.lower()) for key in FORBIDDEN_TERMINAL_KEYS
}


def is_forbidden_terminal_key(value: Any) -> bool:
    """Match adapter keys across snake/camel/kebab spelling variants."""

    token = _NON_ALNUM.sub("", _text(value).lower())
    return bool(token) and token in FORBIDDEN_TERMINAL_KEY_TOKENS


def _text(value: Any) -> str:
    return str(value or "").strip()


def _duplicate_keys(rows: Iterable[dict]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for row in rows:
        key = _text(row.get("key"))
        if key in seen:
            duplicates.add(key)
        seen.add(key)
    return sorted(duplicates)


def _find_forbidden_keys(value: Any, path: str = "business_task") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            key_text = _text(key)
            child_path = f"{path}.{key_text}"
            if is_forbidden_terminal_key(key_text):
                errors.append(child_path)
            errors.extend(_find_forbidden_keys(nested, child_path))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            errors.extend(_find_forbidden_keys(nested, f"{path}[{index}]"))
    return errors


def check_business_task_scene_contract(payload: dict) -> Tuple[bool, Dict[str, object]]:
    """Validate one terminal ``business_task`` profile.

    This validates explicit semantic decisions, not visual layout.  Domain
    services remain authoritative for facts and verdicts; the scene compiler
    may only project those decisions into this profile.
    """

    if not isinstance(payload, dict):
        return False, {"code": "business_task_not_object"}

    missing = [key for key in REQUIRED_SECTIONS if key not in payload]
    if missing:
        return False, {"code": "missing_business_task_sections", "keys": missing}
    if payload.get("profile_version") != "v1":
        return False, {"code": "invalid_business_task_profile_version"}

    forbidden = _find_forbidden_keys(payload)
    if forbidden:
        return False, {"code": "native_vocabulary_leak", "paths": forbidden}

    task = payload.get("task")
    if not isinstance(task, dict):
        return False, {"code": "task_not_object"}
    for key in ("key", "goal", "outcome", "mode", "stage", "state"):
        if not _text(task.get(key)):
            return False, {"code": "missing_task_semantic", "key": key}

    rows_by_section: dict[str, list[dict]] = {}
    for section in ("facts", "inputs", "blockers", "capabilities", "evidence", "relations"):
        rows = payload.get(section)
        if not isinstance(rows, list) or any(not isinstance(item, dict) for item in rows):
            return False, {"code": "invalid_business_task_collection", "section": section}
        duplicates = _duplicate_keys(rows)
        if duplicates:
            return False, {"code": "duplicate_business_task_keys", "section": section, "keys": duplicates}
        for row in rows:
            if not _text(row.get("key")):
                return False, {"code": "missing_business_task_key", "section": section}
        rows_by_section[section] = rows

    for fact in rows_by_section["facts"]:
        if not _text(fact.get("source_authority")):
            return False, {"code": "fact_source_authority_required", "key": fact.get("key")}
        if not _text(fact.get("applicability")):
            return False, {"code": "fact_applicability_required", "key": fact.get("key")}

    for item in rows_by_section["inputs"]:
        for flag in ("visible", "readonly", "required"):
            if not isinstance(item.get(flag), bool):
                return False, {"code": "input_interaction_flag_required", "key": item.get("key"), "flag": flag}
        if not _text(item.get("source_authority")):
            return False, {"code": "input_source_authority_required", "key": item.get("key")}
        if not _text(item.get("applicability")):
            return False, {"code": "input_applicability_required", "key": item.get("key")}
        if item.get("required") and not item.get("visible"):
            return False, {"code": "hidden_input_cannot_be_required", "key": item.get("key")}

    blocker_keys = {str(row["key"]) for row in rows_by_section["blockers"]}
    active_blockers = {str(row["key"]) for row in rows_by_section["blockers"] if row.get("active") is True}
    for blocker in rows_by_section["blockers"]:
        if not isinstance(blocker.get("active"), bool):
            return False, {"code": "blocker_active_verdict_required", "key": blocker.get("key")}
        if blocker.get("active") and not _text(blocker.get("reason_code")):
            return False, {"code": "active_blocker_reason_required", "key": blocker.get("key")}
        if blocker.get("active") and not _text(blocker.get("message")):
            return False, {"code": "active_blocker_message_required", "key": blocker.get("key")}
        if blocker.get("active") and not _text(blocker.get("repair_capability_key")):
            return False, {"code": "active_blocker_repair_required", "key": blocker.get("key")}
        if not isinstance(blocker.get("missing_items"), list):
            return False, {"code": "blocker_missing_items_required", "key": blocker.get("key")}
        if not _text(blocker.get("source_authority")):
            return False, {"code": "blocker_source_authority_required", "key": blocker.get("key")}

    enabled_primary = 0
    capability_keys = {str(row["key"]) for row in rows_by_section["capabilities"]}
    for capability in rows_by_section["capabilities"]:
        key = str(capability["key"])
        for flag in ("visible", "business_available", "authorization_allowed", "enabled"):
            if not isinstance(capability.get(flag), bool):
                return False, {"code": "capability_verdict_required", "key": key, "flag": flag}
        blocked_by = capability.get("blocked_by")
        if not isinstance(blocked_by, list) or any(not isinstance(item, str) for item in blocked_by):
            return False, {"code": "capability_blocked_by_required", "key": key}
        unknown_blockers = sorted(set(blocked_by) - blocker_keys)
        if unknown_blockers:
            return False, {"code": "capability_unknown_blocker", "key": key, "blockers": unknown_blockers}
        executable = bool(capability.get("business_available")) and bool(capability.get("authorization_allowed"))
        executable = executable and not bool(set(blocked_by) & active_blockers)
        executable = executable and bool(capability.get("visible"))
        if bool(capability.get("enabled")) != executable:
            return False, {"code": "capability_verdict_inconsistent", "key": key}
        if not capability.get("enabled"):
            reason_code = _text(capability.get("reason_code"))
            if not reason_code or reason_code.upper() == "OK":
                return False, {"code": "disabled_capability_reason_required", "key": key}
        if capability.get("enabled") and capability.get("presentation") == "primary":
            enabled_primary += 1
        for field in ("safety", "idempotency", "outcome"):
            if not _text(capability.get(field)):
                return False, {"code": "capability_semantic_required", "key": key, "field": field}
        if not _text(capability.get("source_authority")):
            return False, {"code": "capability_source_authority_required", "key": key}
    if enabled_primary > 1:
        return False, {"code": "multiple_enabled_primary_capabilities", "count": enabled_primary}

    for blocker in rows_by_section["blockers"]:
        if not blocker.get("active"):
            continue
        repair_key = _text(blocker.get("repair_capability_key"))
        if repair_key not in capability_keys:
            return False, {
                "code": "active_blocker_repair_capability_missing",
                "key": blocker.get("key"),
                "repair_capability_key": repair_key,
            }

    for section in ("evidence", "relations"):
        for row in rows_by_section[section]:
            if not _text(row.get("source_authority")):
                return False, {"code": "semantic_source_authority_required", "section": section, "key": row.get("key")}

    completion = payload.get("completion")
    if not isinstance(completion, dict) or not isinstance(completion.get("complete"), bool):
        return False, {"code": "completion_verdict_required"}
    next_key = _text(completion.get("next_capability_key"))
    if next_key and next_key not in capability_keys:
        return False, {"code": "completion_unknown_next_capability", "key": next_key}
    if completion.get("complete") and next_key:
        return False, {"code": "completed_task_has_next_capability", "key": next_key}
    if not completion.get("complete") and not next_key:
        return False, {"code": "incomplete_task_next_capability_required"}
    if not _text(completion.get("outcome_code")):
        return False, {"code": "completion_outcome_required"}

    return True, {
        "code": "ok",
        "counts": {section: len(rows) for section, rows in rows_by_section.items()},
        "active_blocker_count": len(active_blockers),
        "enabled_primary_count": enabled_primary,
    }
