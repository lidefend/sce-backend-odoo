# -*- coding: utf-8 -*-
"""Pure helpers for projecting canonical page facts into P1 task semantics."""

from __future__ import annotations

from typing import Any


def text(value: Any) -> str:
    return str(value or "").strip()


def as_dict(value: Any) -> dict:
    return dict(value) if isinstance(value, dict) else {}


def as_list(value: Any) -> list:
    return list(value) if isinstance(value, list) else []


def display(value: Any) -> Any:
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return value[1]
    if isinstance(value, dict):
        return value.get("display_name") or value.get("label") or value.get("name") or ""
    return value


def inactive_capability(reason_code: str = "STATE_NOT_APPLICABLE") -> dict:
    return {
        "visible": False,
        "business_available": False,
        "authorization_allowed": False,
        "enabled": False,
        "reason_code": reason_code,
        "reason": "",
        "source_authority": "canonical_action_contract",
    }


def _method(rule: dict) -> str:
    button = as_dict(rule.get("button"))
    target = as_dict(rule.get("target"))
    identity = text(rule.get("backendIdentity"))
    return text(button.get("name") or target.get("method") or identity.rsplit(":", 1)[-1])


def _authority_verdict(rule: dict, key: str) -> bool | None:
    values = [
        trace.get(key)
        for trace in as_list(rule.get("sourceTrace"))
        if isinstance(trace, dict) and isinstance(trace.get(key), bool)
    ]
    if False in values:
        return False
    return True if True in values else None


def _capability_from_rule(rule: dict, status: dict) -> dict:
    business_available = _authority_verdict(rule, "businessAvailable")
    authorization_allowed = _authority_verdict(rule, "authorizationAllowed")
    visible = status.get("visible") if isinstance(status.get("visible"), bool) else rule.get("visible")
    enabled = rule.get("enabled") if isinstance(rule.get("enabled"), bool) else None
    disabled = status.get("disabled") if isinstance(status.get("disabled"), bool) else rule.get("disabled")
    explicit = all(
        isinstance(value, bool)
        for value in (business_available, authorization_allowed, visible, enabled)
    )
    executable = bool(
        explicit
        and business_available
        and authorization_allowed
        and visible
        and enabled
        and disabled is not True
    )
    reason_code = text(status.get("reasonCode") or rule.get("reasonCode"))
    if not explicit:
        reason_code = "ACTION_PERMISSION_UNRESOLVED"
    elif not executable and (not reason_code or reason_code.upper() == "OK"):
        reason_code = "ACTION_NOT_ALLOWED"
    return {
        "visible": bool(visible) if isinstance(visible, bool) else False,
        "business_available": bool(business_available) if isinstance(business_available, bool) else False,
        "authorization_allowed": bool(authorization_allowed) if isinstance(authorization_allowed, bool) else False,
        "enabled": executable,
        "reason_code": "" if executable else reason_code,
        "reason": "" if executable else text(status.get("reason") or rule.get("hint")),
        "source_authority": "canonical_action_contract",
    }


def canonical_action_capabilities(contract: dict, capability_methods: dict[str, set[str]]) -> dict[str, dict]:
    statuses = {
        text(row.get("btnId")): row
        for row in as_list(as_dict(contract.get("statusContract")).get("buttonStatus"))
        if isinstance(row, dict)
    }
    candidates = {key: [] for key in capability_methods}
    for rule in as_list(as_dict(contract.get("actionContract")).get("actionRuleList")):
        if not isinstance(rule, dict):
            continue
        method = _method(rule)
        capability_key = next(
            (key for key, methods in capability_methods.items() if method in methods),
            "",
        )
        if not capability_key:
            continue
        action_key = text(rule.get("actionKey"))
        candidates[capability_key].append(
            _capability_from_rule(rule, statuses.get(f"btn.{action_key}", {}))
        )
    out = {}
    for capability_key, rows in candidates.items():
        enabled = [row for row in rows if row.get("enabled")]
        applicable = [
            row for row in rows
            if row.get("visible") or row.get("business_available")
        ]
        if len(applicable) > 1:
            out[capability_key] = {
                "visible": True,
                "business_available": True,
                "authorization_allowed": False,
                "enabled": False,
                "reason_code": "ACTION_CAPABILITY_AMBIGUOUS",
                "reason": "多个后端动作同时声明为当前办理能力。",
                "source_authority": "canonical_action_contract",
            }
        elif len(enabled) == 1:
            out[capability_key] = enabled[0]
        elif len(enabled) > 1:
            # Defensive fallback: executable rows are normally applicable, so
            # this branch only protects malformed future adapters.
            out[capability_key] = {
                "visible": False,
                "business_available": False,
                "authorization_allowed": False,
                "enabled": False,
                "reason_code": "ACTION_CAPABILITY_AMBIGUOUS",
                "reason": "多个后端动作同时声明为当前办理能力。",
                "source_authority": "canonical_action_contract",
            }
        elif len(applicable) == 1:
            # Alternate backend methods may represent one stateful capability.
            # Hidden, state-inapplicable aliases must not overwrite the one
            # visible handoff or blocker verdict.
            out[capability_key] = applicable[0]
        elif rows:
            out[capability_key] = rows[0]
        else:
            out[capability_key] = inactive_capability()
    return out


def canonical_input(contract: dict, *, field: str, value: Any, source_authority: str) -> dict:
    """Project interaction flags; missing widget authority stays hidden/read-only."""

    status = next(
        (
            row
            for row in as_list(as_dict(contract.get("statusContract")).get("widgetStatus"))
            if isinstance(row, dict) and text(row.get("widgetId")) == f"field.{field}"
        ),
        {},
    )
    visible = status.get("visible") if isinstance(status.get("visible"), bool) else False
    readonly = status.get("readonly") if isinstance(status.get("readonly"), bool) else True
    disabled = status.get("disabled") if isinstance(status.get("disabled"), bool) else True
    required = status.get("required") if isinstance(status.get("required"), bool) else False
    return {
        "value": value,
        "visible": visible,
        "readonly": bool(readonly or disabled),
        "required": bool(required and visible),
        "source_authority": source_authority,
        "applicability": "always",
    }
