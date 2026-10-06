# -*- coding: utf-8 -*-
"""P1 policy for the unregistered delivery-surface development bypass.

`smart_core.core.scene_delivery_policy` closes an *unregistered* delivery
surface fail-closed: once the delivery policy is enabled, a surface name that no
policy source declares delivers nothing.  Opening one is a product decision, so
the platform kernel only asks the ``smart_core_surface_unregistered_bypass``
extension hook; this module answers it for the construction product.

The grant is deliberately narrow and contract-driven:

* a runtime environment is required (no acting user -> no bypass at all);
* only a development stage is allowed (``dev``/``test``/``local``/``stage``);
* only the platform/system administrator role, resolved through the same
  published role policy as ``system.init.role_surface``, is authorized.

No new capability key, no ACL widening and no customer role is added, so a
customer role can never open an unregistered surface.  This hook never decides
business data access; it only answers whether the caller may explore a surface
that the product has not registered yet.
"""
from __future__ import annotations

import os

RUNTIME_ENV_DEVELOPMENT = ("dev", "test", "local", "stage", "staging")
DEVELOPMENT_BYPASS_ROLES = ("system_admin",)
UNREGISTERED_SURFACE_DEV_BYPASS_REASON = "UNREGISTERED_SURFACE_DEV_BYPASS"


def _runtime_env(runtime_env=None) -> str:
    value = str(runtime_env or os.environ.get("ENV") or "dev").strip().lower()
    return value or "dev"


def _resolve_role_codes(env, user) -> list[str]:
    try:
        from odoo.addons.smart_core.identity.identity_resolver import IdentityResolver

        resolver = IdentityResolver(env)
        role_codes, _evidence = resolver.resolve_role_codes_with_evidence(
            resolver.user_group_xmlids(user)
        )
    except Exception:
        return []
    return [str(code or "").strip() for code in (role_codes or []) if str(code or "").strip()]


def smart_core_surface_unregistered_bypass(env, surface, runtime_env=None):
    """Authorize a development-stage bypass of one unregistered surface."""
    if env is None:
        return None
    user = getattr(env, "user", None)
    if user is None:
        return None
    stage = _runtime_env(runtime_env)
    if stage not in RUNTIME_ENV_DEVELOPMENT:
        return None
    role_codes = _resolve_role_codes(env, user)
    for role in DEVELOPMENT_BYPASS_ROLES:
        if role in role_codes:
            return {
                "authorized": True,
                "role_code": role,
                "runtime_env": stage,
                "surface": str(surface or "").strip().lower(),
                "reason_code": UNREGISTERED_SURFACE_DEV_BYPASS_REASON,
            }
    return None
