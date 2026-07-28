# -*- coding: utf-8 -*-
"""Historical import facade for canonical smart_core platform-admin checks."""

from __future__ import annotations

from odoo.addons.smart_core.security.platform_admin import (
    BREAK_GLASS_TECHNICAL_ADMIN_GROUP,
    LEGACY_PLATFORM_ADMIN_GROUP,
    PLATFORM_ADMIN_GROUP,
    PLATFORM_CONFIGURATION_ADMIN_GROUP,
    SECURITY_ADMIN_GROUP,
    SYSTEM_ADMIN_GROUP,
    can_discover_platform_capabilities,
    can_manage_system_configuration,
    has_customer_business_data_scope,
    platform_admin_group_xmlids,
    platform_admin_groups,
    user_is_break_glass_technical_admin,
    user_is_platform_admin,
    user_is_security_admin,
)

__all__ = [
    "BREAK_GLASS_TECHNICAL_ADMIN_GROUP",
    "LEGACY_PLATFORM_ADMIN_GROUP",
    "PLATFORM_ADMIN_GROUP",
    "PLATFORM_CONFIGURATION_ADMIN_GROUP",
    "SECURITY_ADMIN_GROUP",
    "SYSTEM_ADMIN_GROUP",
    "can_discover_platform_capabilities",
    "can_manage_system_configuration",
    "has_customer_business_data_scope",
    "platform_admin_group_xmlids",
    "platform_admin_groups",
    "user_is_break_glass_technical_admin",
    "user_is_platform_admin",
    "user_is_security_admin",
]
