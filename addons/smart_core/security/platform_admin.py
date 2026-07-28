# -*- coding: utf-8 -*-
"""Platform-admin responsibility checks owned by smart_core."""

from __future__ import annotations

PLATFORM_ADMIN_GROUP = "smart_core.group_smart_core_admin"
PLATFORM_CONFIGURATION_ADMIN_GROUP = PLATFORM_ADMIN_GROUP
SECURITY_ADMIN_GROUP = "smart_core.group_smart_core_security_admin"
SYSTEM_ADMIN_GROUP = "base.group_system"
BREAK_GLASS_TECHNICAL_ADMIN_GROUP = SYSTEM_ADMIN_GROUP
LEGACY_PLATFORM_ADMIN_GROUP = "smart_construction_core.group_sc_cap_config_admin"

CAPABILITY_DISCOVERY_ADMIN_GROUPS = (
    PLATFORM_CONFIGURATION_ADMIN_GROUP,
)


def platform_admin_group_xmlids(*, include_legacy: bool = False, include_system: bool = False) -> list[str]:
    xmlids = [PLATFORM_ADMIN_GROUP]
    if include_legacy:
        xmlids.append(LEGACY_PLATFORM_ADMIN_GROUP)
    if include_system:
        xmlids.append(SYSTEM_ADMIN_GROUP)
    return xmlids


def user_is_platform_admin(user, *, include_system: bool = False, include_legacy: bool = False) -> bool:
    if not user:
        return False
    for xmlid in platform_admin_group_xmlids(include_legacy=include_legacy, include_system=include_system):
        try:
            if user.has_group(xmlid):
                return True
        except Exception:
            continue
    return False


def platform_admin_groups(env, *, include_legacy: bool = False, include_system: bool = False):
    groups = []
    for xmlid in platform_admin_group_xmlids(include_legacy=include_legacy, include_system=include_system):
        group = env.ref(xmlid, raise_if_not_found=False)
        if group:
            groups.append(group)
    return groups


def _user_has_any_group(user, group_xmlids) -> bool:
    if not user:
        return False
    for xmlid in group_xmlids:
        try:
            if user.has_group(xmlid):
                return True
        except Exception:
            continue
    return False


def can_discover_platform_capabilities(user) -> bool:
    """Return whether the user may discover installed product capabilities.

    This is a navigation/configuration visibility decision only.  It must not
    be used as evidence of customer business-record access.
    """

    return _user_has_any_group(user, CAPABILITY_DISCOVERY_ADMIN_GROUPS)


def can_manage_system_configuration(user) -> bool:
    """Return whether system configuration entry points should be visible."""

    return _user_has_any_group(user, CAPABILITY_DISCOVERY_ADMIN_GROUPS)


def user_is_security_admin(user) -> bool:
    """Return whether the user has the independent security-admin identity."""

    return _user_has_any_group(user, (SECURITY_ADMIN_GROUP,))


def user_is_break_glass_technical_admin(user) -> bool:
    """Return whether the user holds Odoo's controlled technical-admin role."""

    return _user_has_any_group(user, (BREAK_GLASS_TECHNICAL_ADMIN_GROUP,))


def has_customer_business_data_scope(user) -> bool:
    """Fail closed for scope inferred only from an administrator identity.

    Customer data scope is established by model ACLs, record rules, company
    scope and explicit business membership, never by these administrator
    identity groups alone.
    """

    del user
    return False
