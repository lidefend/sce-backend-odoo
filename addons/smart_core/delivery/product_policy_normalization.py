"""Resolve product-specific policy normalization through the extension owner."""

from __future__ import annotations

import copy
from typing import Any

from odoo.addons.smart_core.delivery.product_center_policy import (
    ProductCenterPolicyError,
)
from odoo.addons.smart_core.utils.extension_hooks import (
    call_extension_hook_first_compatible,
)


HOOK_NAME = "smart_core_normalize_product_policy"


def normalize_product_policy_for_env(
    env, policy: dict[str, Any] | None
) -> dict[str, Any]:
    """Return the owning extension's normalized policy or the unchanged input.

    P0 owns the extension seam and snapshot mechanics. It does not know the
    construction ten-center aliases. An extension may return a structured
    error, which remains fail-closed instead of being mistaken for a pass.
    """
    payload = copy.deepcopy(policy) if isinstance(policy, dict) else {}
    if env is None:
        return payload
    result = call_extension_hook_first_compatible(
        env,
        HOOK_NAME,
        env,
        payload,
    )
    if not isinstance(result, dict):
        return payload
    status = str(result.get("status") or "").strip()
    if status == "error":
        raise ProductCenterPolicyError(
            str(result.get("code") or "PRODUCT_CENTER_POLICY_INVALID"),
            str(result.get("detail") or ""),
        )
    normalized = result.get("policy")
    if status == "ok" and isinstance(normalized, dict):
        return normalized
    raise ProductCenterPolicyError(
        "PRODUCT_CENTER_NORMALIZATION_INVALID",
        "extension result must contain status=ok and an object policy",
    )
