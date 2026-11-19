"""Normalize maintained product-center identities without replaying seed data."""

from __future__ import annotations

from odoo import SUPERUSER_ID, api
from odoo.addons.smart_construction_core.services.product_center_policy import (
    normalize_construction_product_policy,
)


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    policies = env["sc.product.policy"].sudo().search(
        [
            ("product_key", "in", ["construction.standard", "construction.preview"]),
            ("active", "=", True),
        ]
    )
    changed = []
    for policy in policies:
        before_groups = policy.menu_groups if isinstance(policy.menu_groups, list) else []
        before_capabilities = (
            policy.capabilities if isinstance(policy.capabilities, list) else []
        )
        normalized = normalize_construction_product_policy(
            policy.to_runtime_dict()
        )
        after_groups = normalized.get("menu_groups") or []
        after_capabilities = normalized.get("capabilities") or []
        if after_groups == before_groups and after_capabilities == before_capabilities:
            continue
        policy.write(
            {
                "menu_groups": after_groups,
                "capabilities": after_capabilities,
                "note": "product center identities normalized by 17.0.0.184",
            }
        )
        changed.append(
            {
                "product_key": policy.product_key,
                "center_keys": [
                    group.get("center_key")
                    for group in after_groups
                    if isinstance(group, dict)
                ],
            }
        )
    return {"changed": changed}
