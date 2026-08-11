# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Callable

from ..core.contract_lifecycle import seal_unified_page_contract

REASON_ACTION_GROUP_ACCESS_DENIED = "ACTION_GROUP_ACCESS_DENIED"
REASON_SCENE_ACTION_BINDING_INVALID = "SCENE_ACTION_BINDING_INVALID"


def project_action_group_entitlements(env, source_contract: dict[str, Any], logger) -> None:
    """Resolve backend group constraints into final client-safe button status."""
    policies = source_contract.get("action_policies")
    if not isinstance(policies, dict):
        return
    user = getattr(env, "user", None)
    for action_key, raw_policy in policies.items():
        if not isinstance(raw_policy, dict):
            continue
        enabled_when = raw_policy.get("enabled_when")
        if not isinstance(enabled_when, dict):
            continue
        required_groups = [
            str(item or "").strip()
            for item in (enabled_when.get("required_groups") or [])
            if str(item or "").strip()
        ]
        if not required_groups:
            continue
        allowed = False
        if user is not None:
            try:
                allowed = any(bool(user.has_group(xmlid)) for xmlid in required_groups)
            except Exception:
                logger.warning(
                    "ui.contract.v2 group entitlement projection failed action=%s",
                    action_key,
                    exc_info=True,
                )
        projected_when = dict(enabled_when)
        projected_when.pop("required_groups", None)
        raw_policy["enabled_when"] = projected_when
        raw_policy["entitlement_evaluated"] = True
        raw_policy["enabled"] = bool(raw_policy.get("enabled", True)) and allowed
        if not allowed:
            raw_policy["reason_code"] = REASON_ACTION_GROUP_ACCESS_DENIED
            raw_policy["disabled_reason"] = str(
                raw_policy.get("disabled_reason") or "当前账号无权执行此操作"
            )


def _scene_target_action_id(scene: dict[str, Any]) -> int:
    target = scene.get("target") if isinstance(scene.get("target"), dict) else {}
    candidates = [target]
    entry_target = target.get("entry_target") if isinstance(target.get("entry_target"), dict) else {}
    candidates.extend(
        row
        for row in (
            entry_target,
            entry_target.get("compatibility_refs"),
            entry_target.get("record_entry"),
            entry_target.get("list_entry"),
        )
        if isinstance(row, dict)
    )
    for row in candidates:
        try:
            action_id = int(row.get("action_id") or 0)
        except (TypeError, ValueError):
            action_id = 0
        if action_id > 0:
            return action_id
    return 0


def validate_scene_action_binding(payload: dict[str, Any], params: dict[str, Any], error_factory: Callable[[int, str], Any]):
    """Validate only concrete registry bindings; semantic scene hints are not authorities."""
    scene_key = str(params.get("scene_key") or params.get("sceneKey") or "").strip()
    if not scene_key:
        return None
    scene = next(
        (
            row
            for row in (payload.get("scenes") or [])
            if isinstance(row, dict)
            and str(row.get("code") or row.get("key") or "").strip() == scene_key
        ),
        None,
    )
    # Action-first entries also carry scene_key as a governed routing hint.
    # Only a registry row with a concrete action is an equality authority.
    if not scene:
        return None
    expected_action_id = _scene_target_action_id(scene)
    if expected_action_id <= 0:
        return None
    try:
        requested_action_id = int(params.get("action_id") or params.get("actionId") or 0)
    except (TypeError, ValueError):
        requested_action_id = 0
    if requested_action_id <= 0:
        return error_factory(409, f"{REASON_SCENE_ACTION_BINDING_INVALID}: scene request missing action_id")
    if expected_action_id != requested_action_id:
        return error_factory(
            409,
            f"{REASON_SCENE_ACTION_BINDING_INVALID}: scene={scene_key} action_id={requested_action_id}",
        )
    return None


def resolve_trace_id(context: Any, meta: Any = None) -> str:
    context_body = context if isinstance(context, dict) else {}
    meta_body = meta if isinstance(meta, dict) else {}
    return str(
        context_body.get("trace_id")
        or meta_body.get("trace_id")
        or meta_body.get("traceId")
        or ""
    ).strip()


def seal_runtime_contract(
    owner,
    contract: dict[str, Any],
    source_payload: dict[str, Any],
    source_type: str,
    request_id: str,
    trace_id: str,
    client_type: str,
) -> dict[str, Any]:
    return seal_unified_page_contract(
        contract,
        source_payload=source_payload,
        source_type=source_type,
        request_id=request_id,
        trace_id=trace_id,
        client_type=client_type,
        stage="runtime_delivery",
        generator=owner.SOURCE_KIND,
        generator_version=owner.VERSION,
        source_authority=owner.source_authority_contract(),
    )
