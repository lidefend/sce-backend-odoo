# -*- coding: utf-8 -*-
from __future__ import annotations

from odoo.addons.smart_core.core.source_authority import build_source_authority_contract
from odoo.addons.smart_core.core.platform_duty_contract import (
    build_platform_duty_surface,
    declared_platform_action_xmlids,
)
from odoo.addons.smart_core.security.platform_admin import (
    user_is_platform_control_admin,
    user_is_tenant_config_admin,
)


def _instance_identity(user) -> tuple[str, str]:
    """Logical namespace id and audience of the instance serving this user.

    The physical database name never leaves the backend verification path; the
    identity projection only carries the immutable identifier and the declared
    audience.  Both are resolved once so the platform decision below is made
    against the same instance fact that is reported.
    """

    env = getattr(user, "env", None)
    if env is None:
        return "", ""
    try:
        from odoo.addons.smart_core.security.namespace_resolver import resolve_instance

        instance = resolve_instance(env)
        return str(instance.namespace_id or ""), str(instance.audience or "")
    except Exception:
        return "", ""


def _duty_action_routes(user) -> dict:
    """Resolve declared duty actions to the official action route.

    A duty that names a window action must be rendered by the same
    ``ActionViewShell`` path as every other product action; the projection
    therefore carries ``/a/<id>`` instead of an ad-hoc data endpoint.
    """

    env = getattr(user, "env", None)
    if env is None:
        return {}
    routes = {}
    for xmlid in declared_platform_action_xmlids():
        try:
            action = env.ref(xmlid, raise_if_not_found=False)
        except Exception:
            action = None
        if action is not None and getattr(action, "_name", "") == "ir.actions.act_window":
            routes[xmlid] = "/a/%s" % action.id
    return routes


class SystemInitIdentityPayload:
    SOURCE_KIND = "system_init_identity_payload_projection"
    SOURCE_AUTHORITIES = ("res.users", "res.company", "res.groups")
    NO_BUSINESS_FACT_AUTHORITY = True

    @classmethod
    def source_authority_contract(cls) -> dict:
        return build_source_authority_contract(
            kind=cls.SOURCE_KIND,
            authorities=cls.SOURCE_AUTHORITIES,
            no_business_fact_authority=cls.NO_BUSINESS_FACT_AUTHORITY,
            identity_surface_only=True,
        )

    @staticmethod
    def build(
        user,
        user_groups_xmlids: list,
        *,
        company=None,
        allowed_company_ids=None,
    ) -> dict:
        company = company or (user.company_id if user.company_id else None)
        company_id = company.id if company else None
        company_name = (company.name or "").strip() if company else ""
        normalized_allowed = []
        for value in allowed_company_ids or []:
            try:
                candidate = int(value or 0)
            except (TypeError, ValueError):
                continue
            if candidate > 0 and candidate not in normalized_allowed:
                normalized_allowed.append(candidate)
        if company_id:
            normalized_allowed = [company_id] + [
                candidate for candidate in normalized_allowed if candidate != company_id
            ]
        namespace_id, audience = _instance_identity(user)
        is_platform_admin = user_is_platform_control_admin(
            user, identity_audience=audience or None
        )
        is_tenant_config_admin = user_is_tenant_config_admin(user)
        return {
            "id": user.id,
            "name": user.name,
            # The contract declares a set of group identifiers; emitting them in
            # Python set order made the same identity produce different bytes in
            # every process (string hash randomization). Stable order keeps the
            # startup response byte-identical and therefore cacheable.
            "groups_xmlids": sorted(
                str(item) for item in (user_groups_xmlids or []) if item
            ),
            # ADR-007 D6: platform control is a distinct authority from the
            # tenant configuration admin the product surfaces use.  Emitting
            # both keeps the frontend from treating a product administrator
            # as a platform administrator.
            "is_platform_admin": is_platform_admin,
            "is_tenant_config_admin": is_tenant_config_admin,
            # Declared duty surface: identity domain, capability list and the
            # default landing all come from the backend contract; the frontend
            # only renders them.
            "platform_duty": build_platform_duty_surface(
                is_platform_control_admin=is_platform_admin,
                is_tenant_config_admin=is_tenant_config_admin,
                namespace_id=namespace_id,
                action_routes=_duty_action_routes(user),
            ),
            "lang": user.lang,
            "tz": user.tz,
            "company_id": company_id,
            "allowed_company_ids": normalized_allowed or ([company_id] if company_id else []),
            "company_name": company_name,
            "company": {
                "id": company_id,
                "name": company_name,
                "display_name": company_name,
            } if company_id else None,
        }
