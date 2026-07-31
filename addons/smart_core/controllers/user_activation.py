# -*- coding: utf-8 -*-
from __future__ import annotations

import logging

from odoo import http
from odoo.exceptions import UserError
from odoo.http import request

from ..models.user_activation import PURPOSE_ENTERPRISE_ACTIVATION


_logger = logging.getLogger(__name__)
GENERIC_REJECTION = "激活请求无效、已过期或当前不可使用"


class ScUserActivationController(http.Controller):
    def _client_scope(self) -> str:
        req = request.httprequest
        remote = str(req.remote_addr or "unknown").strip()
        forwarded = str(req.headers.get("X-Forwarded-For") or "").strip()
        if remote in {"127.0.0.1", "::1"} and forwarded:
            remote = forwarded.split(",", 1)[0].strip()
        return f"activation-ip:{remote}"

    def _payload(self) -> dict:
        payload = request.httprequest.get_json(silent=True)
        return payload if isinstance(payload, dict) else {}

    def _response(self, payload: dict, status: int = 200):
        response = request.make_json_response(payload, status=status)
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        return response

    def _allow_request(self) -> bool:
        return request.env["sc.user.activation.throttle"].sudo()._check_and_bump(
            scope=self._client_scope(),
            window_seconds=600,
            max_requests=10,
        )

    @http.route(
        "/api/v1/auth/activation/start",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def activation_start(self, **_kwargs):
        if not self._allow_request():
            return self._response({"ok": False, "message": GENERIC_REJECTION}, status=429)
        activation_code = str(self._payload().get("activation_code") or "")
        try:
            result = request.env["sc.user.activation.credential"].sudo()._begin_activation(
                activation_code,
                expected_purpose=PURPOSE_ENTERPRISE_ACTIVATION,
            )
        except (UserError, ValueError):
            return self._response({"ok": False, "message": GENERIC_REJECTION}, status=400)
        return self._response({"ok": True, **result})

    @http.route(
        "/api/v1/auth/activation/complete",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def activation_complete(self, **_kwargs):
        if not self._allow_request():
            return self._response({"ok": False, "message": GENERIC_REJECTION}, status=429)
        payload = self._payload()
        activation_context = str(payload.get("activation_context") or "")
        password = str(payload.get("password") or "")
        confirm_password = str(payload.get("confirm_password") or "")
        if not password or not hmac_compare(password, confirm_password):
            return self._response({"ok": False, "message": "密码不符合要求或两次输入不一致"}, status=400)
        try:
            request.env["sc.user.activation.credential"].sudo()._complete_activation(
                activation_context,
                password,
                expected_purpose=PURPOSE_ENTERPRISE_ACTIVATION,
            )
        except UserError as exc:
            if "PASSWORD_POLICY" in str(exc):
                return self._response({"ok": False, "message": "密码不符合要求或两次输入不一致"}, status=400)
            return self._response({"ok": False, "message": GENERIC_REJECTION}, status=400)
        return self._response({"ok": True, "message": "账号激活成功，请使用正式密码登录"})

    @http.route(
        "/api/v1/auth/password-recovery/status",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
        save_session=False,
    )
    def password_recovery_status(self, **_kwargs):
        # Recovery is deliberately separated from first activation.  Until a
        # verified recovery channel exists, never accept a login identifier.
        return self._response(
            {
                "ok": True,
                "self_service_enabled": False,
                "message": "当前请通过已批准的组织身份核验流程申请密码恢复",
            }
        )


def hmac_compare(left: str, right: str) -> bool:
    import hmac

    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))
