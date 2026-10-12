# -*- coding: utf-8 -*-
from __future__ import annotations

from odoo import api


BUSINESS_CONFIG_GROUP = "smart_core.group_smart_core_business_config_admin"
PLATFORM_ADMIN_GROUP = "smart_core.group_smart_core_admin"


class PreviewAccessDenied(Exception):
    """Raised before projection when a caller cannot consume draft context."""


def authenticated_projection_locale(env, params: dict) -> dict[str, str]:
    """Return the lang/tz the read-only projection must be rendered in.

    A client may state the locale explicitly, either as top-level request params
    or inside ``params.context``. When the request does not state it, the
    authenticated principal's own language and timezone are authoritative.

    The projection runs on a superuser environment, so an unset locale does not
    fall back to the acting user: it silently localizes the contract to that
    environment's default (``en_US``) while the user reads it in their own
    language. That is a projection defect, not a client choice.
    """
    request_context = params.get("context") if isinstance(params.get("context"), dict) else {}
    lang = str(params.get("lang") or request_context.get("lang") or "").strip()
    tz = str(params.get("tz") or request_context.get("tz") or "").strip()
    user = getattr(env, "user", None)
    locale: dict[str, str] = {}
    resolved_lang = lang or str(getattr(user, "lang", "") or "").strip()
    resolved_tz = tz or str(getattr(user, "tz", "") or "").strip()
    if resolved_lang:
        locale["lang"] = resolved_lang
    if resolved_tz:
        locale["tz"] = resolved_tz
    return locale


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
            api.Environment(env.cr, env.uid, projection_context, su=bool(getattr(env, "su", False))),
            api.Environment(su_env.cr, su_env.uid, projection_context, su=bool(getattr(su_env, "su", False))),
        )
    except Exception as exc:
        if preview_token:
            raise PreviewAccessDenied("无法建立经过校验的预览环境。") from exc
        return env, su_env
