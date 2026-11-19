"""P0-owned definitions for platform-management executable actions."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .release_operator_contract_versions import (
    RELEASE_OPERATOR_WRITE_MODEL_CONTRACT_VERSION,
)

PLATFORM_MANAGEMENT_ACTION_CONTRACT_VERSION = "platform_management_actions.v1"

STATE_OPTIONS = (
    {"value": "draft", "label": "草稿"},
    {"value": "preview", "label": "预览"},
    {"value": "stable", "label": "稳定"},
    {"value": "archived", "label": "归档"},
)
ACCESS_LEVEL_OPTIONS = (
    {"value": "public", "label": "公开"},
    {"value": "internal", "label": "内部"},
    {"value": "role_restricted", "label": "按角色限制"},
)
RELEASE_STATE_OPTIONS = (
    {"value": "released", "label": "正式"},
    {"value": "preview", "label": "预览"},
    {"value": "hidden", "label": "隐藏"},
    {"value": "retired", "label": "退役"},
)

ACTION_DEFINITIONS: dict[str, dict[str, Any]] = {
    "approve": {
        "label": "审批发布申请",
        "intent": "release.operator.approve",
        "accepted_fields": ["action_id"],
        "readback_fields": ["action", "surface"],
        "confirmation_required": True,
    },
    "freeze": {
        "label": "冻结产品候选版本",
        "intent": "release.operator.freeze",
        "accepted_fields": ["product_key", "version", "role_code", "note"],
        "readback_fields": ["snapshot", "surface"],
        "confirmation_required": False,
    },
    "sync_policy": {
        "label": "同步产品能力",
        "intent": "release.operator.sync_policy",
        "accepted_fields": [
            "product_key",
            "preserve_state",
            "preserve_access_level",
        ],
        "readback_fields": ["policy", "surface"],
        "confirmation_required": False,
    },
    "set_page_enabled": {
        "label": "调整产品页面范围",
        "intent": "release.operator.set_page_enabled",
        "accepted_fields": ["product_key", "page_key", "enabled"],
        "readback_fields": ["policy", "surface"],
        "confirmation_required": False,
    },
    "update_page_policy": {
        "label": "调整产品页面策略",
        "intent": "release.operator.update_page_policy",
        "accepted_fields": [
            "product_key",
            "page_key",
            "enabled",
            "release_state",
            "access_level",
            "policy_note",
        ],
        "readback_fields": ["policy", "surface"],
        "confirmation_required": False,
        "editable_fields": [
            {
                "key": "release_state",
                "type": "select",
                "options": deepcopy(list(RELEASE_STATE_OPTIONS)),
            },
            {
                "key": "access_level",
                "type": "select",
                "options": deepcopy(list(ACCESS_LEVEL_OPTIONS)),
            },
            {"key": "policy_note", "type": "text"},
        ],
    },
    "update_policy": {
        "label": "保存产品草案",
        "intent": "release.operator.update_policy",
        "accepted_fields": [
            "product_key",
            "state",
            "access_level",
            "active",
            "allowed_role_codes",
            "center_updates",
            "entry_placements",
        ],
        "readback_fields": ["policy", "surface", "readback"],
        "confirmation_required": True,
        "editable_fields": [
            {
                "key": "state",
                "type": "select",
                "options": deepcopy(list(STATE_OPTIONS)),
            },
            {
                "key": "access_level",
                "type": "select",
                "options": deepcopy(list(ACCESS_LEVEL_OPTIONS)),
            },
            {"key": "active", "type": "boolean"},
            {"key": "allowed_role_codes", "type": "string_list"},
            {"key": "center_updates", "type": "list"},
            {"key": "entry_placements", "type": "list"},
        ],
    },
    "runtime_probe": {
        "label": "验证产品用户",
        "intent": "release.operator.runtime_probe",
        "accepted_fields": ["product_key"],
        "readback_fields": ["runtime_user_probe"],
        "confirmation_required": False,
    },
    "rollback": {
        "label": "回滚产品版本",
        "intent": "release.operator.rollback",
        "accepted_fields": [
            "product_key",
            "target_snapshot_id",
            "replace_active",
            "note",
        ],
        "readback_fields": ["action", "surface"],
        "confirmation_required": True,
    },
}


def management_action_definition(key: str) -> dict[str, Any]:
    definition = ACTION_DEFINITIONS.get(str(key or "").strip())
    if not definition:
        raise KeyError(f"unknown platform management action: {key}")
    return deepcopy(definition)


def configured_management_action(
    key: str,
    *,
    action_key: str,
    enabled: bool,
    reason_code: str,
    params: dict[str, Any],
    role_context: dict[str, Any] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    definition = management_action_definition(key)
    return {
        "write_model_contract_version": RELEASE_OPERATOR_WRITE_MODEL_CONTRACT_VERSION,
        "key": action_key,
        "label": definition["label"],
        "intent": definition["intent"],
        "enabled": bool(enabled),
        "reason_code": str(reason_code or ""),
        "role_context": deepcopy(role_context or {}),
        "params": deepcopy(params),
        "accepted_fields": definition["accepted_fields"],
        "readback_fields": definition["readback_fields"],
        "prerequisites": {
            "confirmation_required": bool(
                definition["confirmation_required"]
            ),
        },
        **(
            {
                "editable_fields": deepcopy(definition["editable_fields"]),
            }
            if definition.get("editable_fields")
            else {}
        ),
        **deepcopy(extra),
    }
