# -*- coding: utf-8 -*-
from __future__ import annotations

from odoo import api


BUSINESS_CONFIG_GROUP = "smart_core.group_smart_core_business_config_admin"
PLATFORM_ADMIN_GROUP = "smart_core.group_smart_core_admin"


class PreviewAccessDenied(Exception):
    """Raised before projection when a caller cannot consume draft context."""


def build_projection_environments(env, su_env, params: dict, projection_context: dict):
    """Return read-only projection environments with an optional verified preview."""
    preview_token = str(params.get("preview_token") or params.get("previewToken") or "").strip()
    preview_role_key = str(params.get("preview_role_key") or params.get("previewRoleKey") or "").strip()
    if preview_token:
        user = env.user
        allowed = int(user.id or 0) == 1 or user.has_group(BUSINESS_CONFIG_GROUP) or user.has_group(PLATFORM_ADMIN_GROUP)
        if not allowed:
            raise PreviewAccessDenied
        from ..identity.identity_resolver import IdentityResolver
        resolver = IdentityResolver(env)
        authenticated_role = str(resolver.resolve_role_code(resolver.user_group_xmlids(user)) or "").strip()
        if preview_role_key and preview_role_key != authenticated_role:
            raise PreviewAccessDenied("预览角色必须对应当前已认证权限身份。")
        changeset = env["ui.business.config.change.set"].sudo().search([
            ("preview_token", "=", preview_token), ("user_id", "=", user.id),
            ("company_id", "=", env.company.id), ("database_name", "=", env.cr.dbname),
            ("state", "=", "ready"),
        ], limit=1)
        from odoo import fields
        if not changeset or not changeset.preview_expires_at or changeset.preview_expires_at <= fields.Datetime.now():
            raise PreviewAccessDenied("预览凭据已失效或不属于当前身份。")
        if str(changeset.role_key or "") != preview_role_key:
            raise PreviewAccessDenied("预览作用域与草稿不匹配。")
        projection_context.update({
            "business_config_preview_token": preview_token,
            "business_config_preview_user_id": int(user.id),
            "business_config_preview_role_key": preview_role_key,
        })
    try:
        return (
            api.Environment(env.cr, env.uid, projection_context),
            api.Environment(su_env.cr, su_env.uid, projection_context),
        )
    except Exception as exc:
        if preview_token:
            raise PreviewAccessDenied("无法建立经过校验的预览环境。") from exc
        return env, su_env
