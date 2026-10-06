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
* only the platform administrator identity is authorized, consumed through the
  same published check that the runtime contract exposes as
  ``identity.is_platform_admin``
  (``smart_core.security.platform_admin.user_is_platform_admin``).

No new capability key, no ACL widening and no customer role is added, so a
customer business role can never open an unregistered surface.  This hook never
decides business data access; it only answers whether the caller may explore a
surface that the product has not registered yet.
"""
from __future__ import annotations

import os

RUNTIME_ENV_DEVELOPMENT = ("dev", "test", "local", "stage", "staging")
DEVELOPMENT_BYPASS_ROLES = ("platform_admin",)
UNREGISTERED_SURFACE_DEV_BYPASS_REASON = "UNREGISTERED_SURFACE_DEV_BYPASS"


def _runtime_env(runtime_env=None) -> str:
    value = str(runtime_env or os.environ.get("ENV") or "dev").strip().lower()
    return value or "dev"


def _resolve_role_code(user) -> str:
    """Resolve the platform-admin identity through the published platform check.

    The kernel never decides which role may open a surface; this policy consumes
    the platform's own administrator check instead of inventing a role
    vocabulary.  ``IdentityResolver`` only knows the customer business roles
    (``executive``/``pm``/``finance``/``project_member``), so it must not be used
    as the authorization source here.  A missing check or an error denies.
    """
    try:
        from odoo.addons.smart_core.security.platform_admin import user_is_platform_admin

        if user_is_platform_admin(user):
            return DEVELOPMENT_BYPASS_ROLES[0]
    except Exception:
        return ""
    return ""


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
    role_code = _resolve_role_code(user)
    if not role_code:
        return None
    return {
        "authorized": True,
        "role_code": role_code,
        "runtime_env": stage,
        "surface": str(surface or "").strip().lower(),
        "reason_code": UNREGISTERED_SURFACE_DEV_BYPASS_REASON,
    }
