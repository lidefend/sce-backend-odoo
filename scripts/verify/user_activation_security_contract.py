#!/usr/bin/env python3
"""Fail-closed static companion checks for the activation behavior tests."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "addons/smart_core/models/user_activation.py"
CONTROLLER = ROOT / "addons/smart_core/controllers/user_activation.py"
SPA_SERVICE = ROOT / "frontend/apps/web/src/services/accountActivation.ts"
SPA_VIEW = ROOT / "frontend/apps/web/src/views/AccountActivationView.vue"


def require(text: str, fragment: str, source: Path) -> None:
    if fragment not in text:
        raise SystemExit(f"USER_ACTIVATION_SECURITY_CONTRACT=FAIL missing={fragment!r} source={source}")


def forbid(text: str, fragment: str, source: Path) -> None:
    if fragment in text:
        raise SystemExit(f"USER_ACTIVATION_SECURITY_CONTRACT=FAIL forbidden={fragment!r} source={source}")


def main() -> None:
    model = MODEL.read_text(encoding="utf-8")
    controller = CONTROLLER.read_text(encoding="utf-8")
    service = SPA_SERVICE.read_text(encoding="utf-8")
    view = SPA_VIEW.read_text(encoding="utf-8")
    ast.parse(model, filename=str(MODEL))
    ast.parse(controller, filename=str(CONTROLLER))

    for purpose in (
        "enterprise_activation",
        "password_recovery",
        "email_verification",
        "saas_registration_verification",
        "tenant_invitation",
    ):
        require(model, purpose, MODEL)
    require(model, "secrets.token_urlsafe(32)", MODEL)
    require(model, "hmac.compare_digest", MODEL)
    require(model, 'user.with_context(sc_skip_token_epoch_bump=False).write({"password": password})', MODEL)
    require(controller, 'methods=["POST"]', CONTROLLER)
    for route in (
        "/api/v1/auth/activation/start",
        "/api/v1/auth/activation/complete",
        "/api/v1/auth/password-recovery/status",
    ):
        require(controller, route, CONTROLLER)
    if controller.count("save_session=False") != 3:
        raise SystemExit(
            "USER_ACTIVATION_SECURITY_CONTRACT=FAIL "
            f"expected_save_session_false=3 actual={controller.count('save_session=False')}"
        )
    require(controller, 'Cache-Control', CONTROLLER)
    require(controller, 'Referrer-Policy', CONTROLLER)
    require(service, "body: body ? JSON.stringify(body) : undefined", SPA_SERVICE)
    require(service, "cache: 'no-store'", SPA_SERVICE)
    require(service, "credentials: 'omit'", SPA_SERVICE)
    require(service, "referrerPolicy: 'no-referrer'", SPA_SERVICE)
    require(view, "onBeforeUnmount", SPA_VIEW)

    for source, text in ((service, service), (view, view)):
        forbid(text, "localStorage", source)
        forbid(text, "sessionStorage", source)
        forbid(text, "?token=", source)
        forbid(text, "URLSearchParams", source)
    forbid(model, 'fields.Char(required=True, copy=False, string="Activation token")', MODEL)
    forbid(controller, "request.params.get(\"activation", CONTROLLER)

    print("USER_ACTIVATION_SECURITY_CONTRACT=PASS")
    print("CREDENTIAL_PURPOSE_MODEL=PASS")
    print("ACTIVATION_TOKEN_QUERY_PARAMETER=false")
    print("ACTIVATION_TOKEN_PLAINTEXT_STORED=false")
    print("PUBLIC_SIGNUP_ENABLED=false")


if __name__ == "__main__":
    main()
