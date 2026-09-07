# -*- coding: utf-8 -*-
"""Installation-time platform identity carriers."""

from odoo import SUPERUSER_ID, api


def post_init_hook(env_or_cr, registry=None):
    """Assign the built-in administrator an explicit product-admin carrier."""
    env = env_or_cr if isinstance(env_or_cr, api.Environment) else api.Environment(env_or_cr, SUPERUSER_ID, {})
    admin = env.ref("base.user_admin", raise_if_not_found=False)
    group = env.ref("smart_core.group_smart_core_admin", raise_if_not_found=False)
    if admin and group and group not in admin.groups_id:
        admin.sudo().write({"groups_id": [(4, group.id)]})
