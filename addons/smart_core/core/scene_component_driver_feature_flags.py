# -*- coding: utf-8 -*-
"""Fail-closed startup projection for scene component driver policy."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


SCENE_COMPONENT_DRIVER_FLAG = "scene_component_drivers_v1"
SCENE_COMPONENT_DRIVER_KITS = frozenset({"sc-native", "tdesign-modern"})
SCENE_COMPONENT_DRIVER_FORM_MODES = frozenset({"create", "edit", "readonly"})


def _text_list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple, set)):
        return []
    result: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text and text not in result:
            result.append(text)
    return result


def _positive_integer_list(value: Any) -> list[int]:
    result: list[int] = []
    for item in _text_list(value):
        try:
            candidate = int(item)
        except (TypeError, ValueError):
            continue
        if candidate > 0 and candidate not in result:
            result.append(candidate)
    return result


def normalize_scene_component_driver_policy(value: Any) -> dict[str, Any] | None:
    """Return a safe public policy or ``None`` when the policy cannot activate."""

    if not isinstance(value, Mapping) or value.get("enabled") is not True:
        return None
    read_only_only = value.get("read_only_only") is True
    form_modes = [
        item for item in _text_list(value.get("form_modes"))
        if item in SCENE_COMPONENT_DRIVER_FORM_MODES
    ]
    if not read_only_only and not form_modes:
        return None

    action_ids = _positive_integer_list(value.get("action_ids"))
    models = _text_list(value.get("models"))
    scene_keys = _text_list(value.get("scene_keys"))
    if not action_ids and not models and not scene_keys:
        return None

    allowed_kits = [
        item for item in _text_list(value.get("allowed_kits"))
        if item in SCENE_COMPONENT_DRIVER_KITS
    ]
    if "sc-native" not in allowed_kits:
        return None

    def allowed_kit(name: str, *, fallback: str = "") -> str:
        candidate = str(value.get(name) or "").strip()
        return candidate if candidate in allowed_kits else fallback

    normalized: dict[str, Any] = {
        "enabled": True,
        "read_only_only": read_only_only,
        "form_modes": form_modes,
        "action_ids": action_ids,
        "models": models,
        "scene_keys": scene_keys,
        "allowed_kits": allowed_kits,
        "system_default_kit": allowed_kit("system_default_kit", fallback="sc-native"),
        "allow_user_override": value.get("allow_user_override") is True,
        "allow_preview_override": value.get("allow_preview_override") is True,
    }
    organization_default = allowed_kit("organization_default_kit")
    locked_kit = allowed_kit("locked_kit")
    if organization_default:
        normalized["organization_default_kit"] = organization_default
    if locked_kit:
        normalized["locked_kit"] = locked_kit
        normalized["allow_user_override"] = False
    return normalized


def resolve_system_feature_flags(
    navigation_flags: Any,
    entitlement_flags: Any,
) -> dict[str, Any]:
    """Merge startup flags while keeping scene-driver authority in entitlement."""

    result = dict(navigation_flags) if isinstance(navigation_flags, Mapping) else {}
    entitlement = dict(entitlement_flags) if isinstance(entitlement_flags, Mapping) else {}
    result.update({key: value for key, value in entitlement.items() if key != SCENE_COMPONENT_DRIVER_FLAG})

    scene_policy = normalize_scene_component_driver_policy(entitlement.get(SCENE_COMPONENT_DRIVER_FLAG))
    if scene_policy is None:
        result.pop(SCENE_COMPONENT_DRIVER_FLAG, None)
    else:
        result[SCENE_COMPONENT_DRIVER_FLAG] = scene_policy
    return result
