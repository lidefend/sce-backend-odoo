# -*- coding: utf-8 -*-
"""P0-C production helpers for ``page-block-action.v1``.

The carrier is a projection of the existing Contract V2 action rule authority.
It never evaluates action authorization itself: callers supply the verdicts
from the established action/route authorization services.
"""
from __future__ import annotations

from copy import deepcopy
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any, Callable, Iterable

try:
    from .action_target_schema import (
        ActionTargetSchemaError,
        validate_action_target as _validate_action_target,
    )
except ImportError:
    _target_spec = spec_from_file_location(
        "page_block_action_target_schema",
        Path(__file__).with_name("action_target_schema.py"),
    )
    if _target_spec is None or _target_spec.loader is None:
        raise
    _target_module = module_from_spec(_target_spec)
    _target_spec.loader.exec_module(_target_module)
    ActionTargetSchemaError = _target_module.ActionTargetSchemaError
    _validate_action_target = _target_module.validate_action_target

PAGE_BLOCK_ACTION_VERSION = "1.0.0"
PAGE_BLOCK_ACTION_SCHEMA = "page-block-action.v1"

SOURCE_KIND = "page_block_action_producer"
SOURCE_AUTHORITIES = (
    "contract_v2_action_rules",
    "action_target_schema",
    "published_route_authority",
)
FORBIDDEN_PUBLIC_KEYS = frozenset({"authorizationSubject", "authorization_subject"})
FEEDBACK_STATUSES = frozenset({"success", "denied", "failed"})


class PageBlockActionContractError(ValueError):
    """A fail-closed page-block action contract error."""


def _text(value: Any) -> str:
    return str(value or "").strip()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _reject_public_identity(value: Any, path: str) -> None:
    if isinstance(value, dict):
        forbidden = sorted(set(value) & FORBIDDEN_PUBLIC_KEYS)
        if forbidden:
            raise PageBlockActionContractError(
                f"{path} exposes server-only authorization identity: {', '.join(forbidden)}"
            )
        for key, item in value.items():
            _reject_public_identity(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_public_identity(item, f"{path}[{index}]")


def source_authority_contract() -> dict[str, Any]:
    return {
        "kind": SOURCE_KIND,
        "authorities": list(SOURCE_AUTHORITIES),
        "projectionOnly": True,
        "noFrontendDefaults": True,
        "carrier": PAGE_BLOCK_ACTION_SCHEMA,
        "schemaVersion": PAGE_BLOCK_ACTION_VERSION,
    }


def validate_action_target(target: Any, *, path: str = "target") -> dict[str, Any]:
    """Validate one existing action-target form without inventing a fallback."""

    try:
        return _validate_action_target(target, path=path)
    except ActionTargetSchemaError as exc:
        raise PageBlockActionContractError(str(exc)) from exc


def _action_id(action_key: str) -> str:
    raw = _text(action_key)
    out = []
    for char in raw:
        if char.isalnum() or char in "_.:-":
            out.append(char)
        elif char in " /":
            out.append(".")
    normalized = "".join(out).strip(".")
    if not normalized:
        normalized = "action"
    if not normalized[0].isalpha():
        normalized = f"id.{normalized}"
    return normalized if normalized.startswith("action.") else f"action.{normalized}"


def _reason(
    *,
    enabled: bool,
    visible: bool,
    reason_code: Any,
    reason_message: Any,
) -> tuple[str, str]:
    code = _text(reason_code)
    message = _text(reason_message)
    if visible and not enabled and not code:
        raise PageBlockActionContractError(
            "a visible unavailable page-block action requires reasonCode"
        )
    if visible and not enabled and not message:
        raise PageBlockActionContractError(
            "a visible unavailable page-block action requires reasonMessage"
        )
    return code, message


def _normalize_action(raw: Any) -> dict[str, Any]:
    source = _dict(raw)
    _reject_public_identity(source, "action")
    action_key = _text(source.get("actionKey") or source.get("action_key"))
    if not action_key:
        raise PageBlockActionContractError("actionKey is required")
    action_id = _text(source.get("actionId") or source.get("action_id")) or _action_id(action_key)
    action_rule_ref = _text(source.get("actionRuleRef") or source.get("action_rule_ref")) or action_id
    if action_rule_ref != action_id:
        raise PageBlockActionContractError(
            f"{action_id} actionRuleRef must match the canonical actionId"
        )
    label = _text(source.get("label"))
    intent = _text(source.get("intent"))
    if not label or not intent:
        raise PageBlockActionContractError(f"{action_id} requires label and intent")
    target = validate_action_target(source.get("target"), path=f"{action_id}.target")
    visible = source.get("visible", True)
    authorization_allowed = source.get("authorizationAllowed")
    business_available = source.get("businessAvailable")
    permission_evaluated = source.get("permissionEvaluated")
    if (
        not isinstance(visible, bool)
        or not isinstance(authorization_allowed, bool)
        or not isinstance(business_available, bool)
        or permission_evaluated is not True
    ):
        raise PageBlockActionContractError(
            f"{action_id} requires visible plus fully evaluated authorization and business facts"
        )
    allowed = authorization_allowed and business_available
    explicit_enabled = source.get("enabled")
    if explicit_enabled is not None and not isinstance(explicit_enabled, bool):
        raise PageBlockActionContractError(f"{action_id}.enabled must be a boolean")
    enabled = allowed if explicit_enabled is None else explicit_enabled
    if enabled and not allowed:
        raise PageBlockActionContractError(
            f"{action_id} cannot be enabled when permission.allowed is false"
        )
    disabled = source.get("disabled") is True or not enabled
    reason_code, reason_message = _reason(
        enabled=enabled,
        visible=visible,
        reason_code=source.get("reasonCode") or source.get("reason_code"),
        reason_message=source.get("reasonMessage") or source.get("reason_message"),
    )
    source_widget_id = _text(
        source.get("sourceWidgetId") or source.get("source_widget_id")
    ) or "page.root"
    return {
        "actionId": action_id,
        "actionRuleRef": action_rule_ref,
        "actionKey": action_key,
        "label": label,
        "intent": intent,
        "target": target,
        "sourceWidgetId": source_widget_id,
        "visible": visible,
        "authorizationAllowed": authorization_allowed,
        "businessAvailable": business_available,
        "allowed": allowed,
        "enabled": enabled,
        "disabled": disabled,
        "reasonCode": reason_code,
        "reasonMessage": reason_message,
    }


def build_page_block_action_contract(
    actions: Iterable[dict[str, Any]],
    *,
    source_authority: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the carrier and its canonical ContractV2ActionRule projection."""

    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_keys: set[str] = set()
    for raw in actions:
        action = _normalize_action(raw)
        if action["actionId"] in seen_ids or action["actionKey"] in seen_keys:
            raise PageBlockActionContractError(
                f"duplicate page-block action identity: {action['actionId']}"
            )
        seen_ids.add(action["actionId"])
        seen_keys.add(action["actionKey"])
        normalized.append(action)
    normalized.sort(key=lambda row: row["actionId"])

    action_rules: list[dict[str, Any]] = []
    carrier_actions: dict[str, dict[str, Any]] = {}
    dependency_graph: dict[str, list[str]] = {}
    for action in normalized:
        actionId = action["actionId"]
        action_key = action["actionKey"]
        reason = {
            **({"reasonCode": action["reasonCode"]} if action["reasonCode"] else {}),
            **({"reasonMessage": action["reasonMessage"]} if action["reasonMessage"] else {}),
        }
        action_rule = {
            "actionId": actionId,
            "actionKey": action_key,
            "label": action["label"],
            "intent": action["intent"],
            "target": deepcopy(action["target"]),
            "button": {},
            "triggerType": "click",
            "sourceWidgetId": action["sourceWidgetId"],
            "targetIds": [],
            "dispatchMode": "server",
            "targetScope": "page",
            "refreshMode": "partial",
            "sourceChannel": "page_block_action",
            "authorizationAllowed": action["authorizationAllowed"],
            "businessAvailable": action["businessAvailable"],
            "entitlementEvaluated": True,
            "allowed": action["allowed"],
            "enabled": action["enabled"],
            "disabled": action["disabled"],
            **reason,
        }
        action_rules.append(action_rule)
        carrier_actions[actionId] = {
            "actionId": actionId,
            "actionRuleRef": action["actionRuleRef"],
            "actionKey": action_key,
            "label": action["label"],
            "intent": action["intent"],
            "target": {
                "source": "ContractV2ActionRule.target",
                "value": deepcopy(action["target"]),
            },
            "visibility": {
                "visible": action["visible"],
                "source": "action_contract",
            },
            "permission": {
                "evaluated": True,
                "allowed": action["allowed"],
                "authorizationAllowed": action["authorizationAllowed"],
                "businessAvailable": action["businessAvailable"],
            },
            "state": {
                "enabled": action["enabled"],
                "disabled": action["disabled"],
                "reasonCode": action["reasonCode"],
                "reasonMessage": action["reasonMessage"],
            },
        }
        dependency_graph.setdefault(action["sourceWidgetId"], []).append(actionId)

    authority = deepcopy(source_authority or source_authority_contract())
    _reject_public_identity(authority, "sourceAuthority")
    return {
        "action_contract": {
            "actionRuleList": action_rules,
            "dependencyGraph": {
                key: sorted(set(values))
                for key, values in sorted(dependency_graph.items())
            },
        },
        "action_schema": {
            "schemaVersion": PAGE_BLOCK_ACTION_VERSION,
            "carrier": PAGE_BLOCK_ACTION_SCHEMA,
            "sourceAuthority": authority,
            "actions": carrier_actions,
        },
    }


def build_action_feedback(
    *,
    action_id: str,
    status: str,
    reason_code: str,
    message: str,
    trace_id: str,
) -> dict[str, Any]:
    normalized_status = _text(status).lower()
    if normalized_status not in FEEDBACK_STATUSES:
        raise PageBlockActionContractError("action feedback status is invalid")
    payload = {
        "schemaVersion": PAGE_BLOCK_ACTION_VERSION,
        "actionId": _text(action_id),
        "status": normalized_status,
        "reasonCode": _text(reason_code),
        "message": _text(message),
        "traceId": _text(trace_id),
    }
    if not payload["actionId"] or not payload["traceId"]:
        raise PageBlockActionContractError(
            "action feedback requires actionId and traceId"
        )
    if normalized_status in {"denied", "failed"} and (
        not payload["reasonCode"] or not payload["message"]
    ):
        raise PageBlockActionContractError(
            "denied or failed action feedback requires reasonCode and message"
        )
    return payload


def build_action_feedback_from_result(
    action_result: dict[str, Any],
    *,
    action_id: str,
    trace_id: str,
) -> dict[str, Any]:
    result = _dict(action_result)
    error = _dict(result.get("error"))
    ok = result.get("ok") is True and not error
    status = "success"
    if not ok:
        code = _text(error.get("code"))
        status = "denied" if code in {"401", "403", "ACCESS_DENIED"} else "failed"
    return build_action_feedback(
        action_id=action_id,
        status=status,
        reason_code=_text(error.get("reason_code") or error.get("reasonCode") or error.get("code")),
        message=_text(error.get("message")),
        trace_id=trace_id,
    )


def build_navigation_action_authority(env) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Resolve published navigation targets through the existing authority."""

    from ..delivery.runtime_route_authority import (
        iter_published_pairs,
        published_route_authority,
    )

    authority = published_route_authority(env)
    published_action_ids = {
        action_id
        for _menu_id, action_id in iter_published_pairs(authority)
        if action_id
    }

    def resolve(target: dict[str, Any]) -> dict[str, Any]:
        validated = validate_action_target(target)
        target_type = _text(validated.get("type") or validated.get("_name"))
        if target_type != "action":
            raise PageBlockActionContractError(
                "published navigation action authority only resolves action targets"
            )
        action_xmlid = _text(validated.get("action_xmlid"))
        action_id_raw = validated.get("action_id")
        action = (
            env.ref(action_xmlid, raise_if_not_found=False)
            if action_xmlid
            else env["ir.actions.actions"].browse(int(action_id_raw or 0)).exists()
        )
        if not action or not action.exists():
            return {
                "authorizationAllowed": False,
                "businessAvailable": False,
                "permissionEvaluated": True,
                "reasonCode": "ACTION_TARGET_NOT_FOUND",
                "reasonMessage": "动作目标不存在",
            }
        if int(action.id) not in published_action_ids:
            return {
                "authorizationAllowed": False,
                "businessAvailable": True,
                "permissionEvaluated": True,
                "reasonCode": "ACTION_NOT_AUTHORIZED",
                "reasonMessage": "当前角色无权执行该动作",
            }
        return {
            "authorizationAllowed": True,
            "businessAvailable": True,
            "permissionEvaluated": True,
            "reasonCode": "",
            "reasonMessage": "",
        }

    return resolve
