# -*- coding: utf-8 -*-
"""Compile domain verdicts and a task profile into terminal scene semantics.

The compiler is deliberately pure: it has no ORM, request, user or company
access.  Callers must supply resolved, authoritative domain verdicts.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable

from ..schemas.business_task_scene_contract import (
    FORBIDDEN_TERMINAL_KEYS,
    check_business_task_scene_contract,
)


@dataclass(frozen=True)
class BusinessTaskCompileError(ValueError):
    code: str
    detail: dict[str, Any]

    def __str__(self) -> str:
        return f"{self.code}: {self.detail}"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: Any) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()


def _walk_forbidden(value: Any, path: str) -> list[str]:
    out: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            key_text = _text(key)
            child = f"{path}.{key_text}"
            if key_text.lower() in FORBIDDEN_TERMINAL_KEYS:
                out.append(child)
            out.extend(_walk_forbidden(nested, child))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            out.extend(_walk_forbidden(nested, f"{path}[{index}]"))
    return out


def _declared_rows(profile: dict[str, Any], section: str) -> list[dict[str, Any]]:
    rows = _as_list(profile.get(section))
    if any(not isinstance(item, dict) for item in rows):
        raise BusinessTaskCompileError("invalid_profile_collection", {"section": section})
    keys: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in rows:
        row = dict(item)
        key = _text(row.get("key"))
        if not key:
            raise BusinessTaskCompileError("profile_key_required", {"section": section})
        if key in keys:
            raise BusinessTaskCompileError("duplicate_profile_key", {"section": section, "key": key})
        keys.add(key)
        out.append(row)
    return out


def _supply_row(supply: dict[str, Any], section: str, key: str) -> dict[str, Any]:
    rows = _as_dict(supply.get(section))
    row = rows.get(key)
    if not isinstance(row, dict):
        raise BusinessTaskCompileError("semantic_supply_missing", {"section": section, "key": key})
    return dict(row)


def _project_rows(
    profile: dict[str, Any],
    supply: dict[str, Any],
    section: str,
    *,
    profile_fields: Iterable[str],
    supply_fields: Iterable[str],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for declared in _declared_rows(profile, section):
        key = _text(declared.get("key"))
        supplied = _supply_row(supply, section, key)
        row: dict[str, Any] = {"key": key}
        for field in profile_fields:
            if field in declared:
                row[field] = deepcopy(declared.get(field))
        for field in supply_fields:
            if field in supplied:
                row[field] = deepcopy(supplied.get(field))
        out.append(row)
    return out


def compile_business_task_scene_contract(
    *,
    profile: dict[str, Any],
    semantic_supply: dict[str, Any],
) -> dict[str, Any]:
    """Return a sealed terminal ``business_task`` profile.

    The declaration owns task wording, ordering and presentation. The semantic
    supply owns facts and verdicts. Unknown supply keys are intentionally not
    copied to the terminal contract.
    """

    profile_payload = _as_dict(profile)
    supply_payload = _as_dict(semantic_supply)
    leaks = _walk_forbidden(profile_payload, "profile")
    if leaks:
        raise BusinessTaskCompileError("native_vocabulary_in_profile", {"paths": leaks})
    if profile_payload.get("profile_version") != "v1":
        raise BusinessTaskCompileError("unsupported_profile_version", {"value": profile_payload.get("profile_version")})

    task_profile = _as_dict(profile_payload.get("task"))
    task_supply = _as_dict(supply_payload.get("task"))
    task = {
        "key": _text(task_profile.get("key")),
        "goal": _text(task_profile.get("goal")),
        "outcome": _text(task_profile.get("outcome")),
        "mode": _text(task_supply.get("mode")),
        "stage": _text(task_supply.get("stage")),
        "state": _text(task_supply.get("state")),
    }

    facts = _project_rows(
        profile_payload,
        supply_payload,
        "facts",
        profile_fields=("label", "importance", "group", "presentation"),
        supply_fields=("value", "value_state", "source_authority", "applicability"),
    )
    inputs = _project_rows(
        profile_payload,
        supply_payload,
        "inputs",
        profile_fields=("label", "group", "input_kind", "help"),
        supply_fields=("value", "visible", "readonly", "required", "source_authority", "applicability"),
    )
    blockers = _project_rows(
        profile_payload,
        supply_payload,
        "blockers",
        profile_fields=("label", "repair_capability_key", "owner"),
        supply_fields=("active", "reason_code", "message", "missing_items", "source_authority"),
    )
    capabilities = _project_rows(
        profile_payload,
        supply_payload,
        "capabilities",
        profile_fields=("label", "presentation", "safety", "idempotency", "outcome", "blocked_by", "handoff"),
        supply_fields=(
            "business_available",
            "authorization_allowed",
            "enabled",
            "reason_code",
            "reason",
            "source_authority",
        ),
    )
    evidence = _project_rows(
        profile_payload,
        supply_payload,
        "evidence",
        profile_fields=("label", "kind", "group"),
        supply_fields=("state", "count", "required", "source_authority"),
    )
    relations = _project_rows(
        profile_payload,
        supply_payload,
        "relations",
        profile_fields=("label", "kind", "group"),
        supply_fields=("state", "count", "summary", "source_authority"),
    )

    completion_supply = _as_dict(supply_payload.get("completion"))
    completion = {
        "complete": completion_supply.get("complete"),
        "next_capability_key": _text(completion_supply.get("next_capability_key")),
        "outcome_code": _text(completion_supply.get("outcome_code")),
    }
    terminal = {
        "profile_version": "v1",
        "task": task,
        "facts": facts,
        "inputs": inputs,
        "blockers": blockers,
        "capabilities": capabilities,
        "evidence": evidence,
        "relations": relations,
        "completion": completion,
    }
    ok, detail = check_business_task_scene_contract(terminal)
    if not ok:
        raise BusinessTaskCompileError("compiled_contract_invalid", detail)

    source_authorities = sorted(
        {
            _text(row.get("source_authority"))
            for section in (facts, inputs, blockers, capabilities, evidence, relations)
            for row in section
            if _text(row.get("source_authority"))
        }
    )
    terminal["trace"] = {
        "compiler": "smart_scene.business_task_scene_compiler.v1",
        "profile_key": _text(task.get("key")),
        "profile_sha256": _sha256(profile_payload),
        "semantic_supply_sha256": _sha256(supply_payload),
        "source_authorities": source_authorities,
    }
    terminal["trace"]["sealed_contract_sha256"] = _sha256(terminal)
    return terminal


def verify_business_task_scene_contract_seal(payload: dict[str, Any]) -> bool:
    """Verify the deterministic compiler seal without trusting trace metadata."""

    contract = _as_dict(payload)
    trace = _as_dict(contract.get("trace"))
    expected = _text(trace.get("sealed_contract_sha256"))
    if len(expected) != 64:
        return False
    unsigned = dict(contract)
    unsigned_trace = dict(trace)
    unsigned_trace.pop("sealed_contract_sha256", None)
    unsigned["trace"] = unsigned_trace
    return _sha256(unsigned) == expected
