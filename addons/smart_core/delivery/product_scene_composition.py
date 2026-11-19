"""Shared product-draft composition assembly for release management."""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

from odoo.addons.smart_core.utils.extension_hooks import call_extension_hook_first

from .product_policy_normalization import normalize_product_policy_for_env


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compose_product_policy(env, policy: dict[str, Any]) -> dict[str, Any]:
    """Normalize a policy draft and apply the maintained composition hook.

    The release freeze and release-operator draft projection both consume this
    function so an administrator cannot see one composition while freezing
    another.
    """
    payload = normalize_product_policy_for_env(env, deepcopy(_dict(policy)))
    composition = call_extension_hook_first(
        env,
        "smart_core_product_scene_composition",
        env,
        payload,
    )
    if composition is None:
        return payload
    if not isinstance(composition, dict):
        raise ValueError("BUSINESS_SCENE_COMPOSITION_INVALID")
    if not isinstance(composition.get("scenarios"), list):
        raise ValueError("BUSINESS_SCENE_COMPOSITION_INVALID")
    payload["business_scene_composition"] = deepcopy(composition)
    return payload
