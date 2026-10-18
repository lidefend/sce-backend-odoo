# -*- coding: utf-8 -*-
"""Declared platform duty surface endpoint (ADR-007 D6).

``GET /api/ops/platform-duty`` returns the duty surface a *verified* platform
control administrator holds.  The authorization decision is not re-implemented
here: :func:`smart_core.controllers.platform_ops_controller._platform_env`
performs the same three checks as every other platform control route (trusted
platform-control instance, token identity audience, current platform permission)
and raises :class:`AccessDenied` otherwise.

The payload comes from :mod:`.core.platform_duty_contract`; the controller only
projects it.  No physical database name is emitted -- the surface carries the
logical ``namespace_id`` and a boolean ``trusted_instance_verified``.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from odoo import http
from odoo.exceptions import AccessDenied
from odoo.http import request

from odoo.addons.smart_core.core.platform_duty_contract import (
    CONTRACT_VERSION as DUTY_CONTRACT_VERSION,
    build_platform_duty_surface,
)
from odoo.addons.smart_core.core.trace import get_trace_id
from odoo.addons.smart_core.controllers.platform_ops_controller import _platform_env
from odoo.addons.smart_core.security.platform_admin import user_is_tenant_config_admin

ROUTE = "/api/ops/platform-duty"


def _server_time() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _json_response(payload: dict[str, Any], status: int = 200):
    return request.make_response(
        json.dumps(payload, ensure_ascii=False, default=str),
        headers=[("Content-Type", "application/json; charset=utf-8")],
        status=status,
    )


def _envelope(ok: bool, data: Any = None, error: dict | None = None, status: int = 200):
    trace_id = get_trace_id(request.httprequest.headers)
    payload = {
        "ok": ok,
        "contract_version": DUTY_CONTRACT_VERSION,
        "server_time": _server_time(),
        "trace_id": trace_id,
        "warnings": [],
    }
    if ok:
        payload["data"] = data
    else:
        payload["error"] = error or {"code": "SERVER_ERROR", "message": "Internal server error"}
        payload["error"]["trace_id"] = trace_id
    return _json_response(payload, status=status)


def _namespace_id(env) -> str:
    try:
        from odoo.addons.smart_core.security.namespace_resolver import resolve_instance

        return str(resolve_instance(env).namespace_id or "")
    except Exception:
        return ""


class PlatformDutyController(http.Controller):
    @http.route(ROUTE, type="http", auth="public", methods=["GET"], csrf=False)
    def platform_duty(self, **params):
        try:
            user, env = _platform_env()
            surface = build_platform_duty_surface(
                is_platform_control_admin=True,
                is_tenant_config_admin=user_is_tenant_config_admin(user),
                namespace_id=_namespace_id(env),
            )
            return _envelope(True, surface, status=200)
        except AccessDenied:
            return _envelope(
                False,
                error={"code": "PERMISSION_DENIED", "message": "platform control permission required"},
                status=403,
            )
        except Exception as exc:
            return _envelope(
                False,
                error={"code": "SERVER_ERROR", "message": "Internal server error", "details": {"error": str(exc)}},
                status=500,
            )
