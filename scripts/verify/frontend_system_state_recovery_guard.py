#!/usr/bin/env python3
"""Fail closed on session-expiry explanation and safe-return regressions."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(relative: str) -> str:
    path = ROOT / relative
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def validate() -> list[str]:
    failures: list[str] = []
    helper = read("frontend/apps/web/src/app/sessionExpiredRecovery.ts")
    client = read("frontend/apps/web/src/api/client.ts")
    login = read("frontend/apps/web/src/views/LoginView.vue")

    for marker in (
        "normalizeSafeLoginReturnPath",
        "SESSION_EXPIRED_RETURN_PATH_KEY",
        "sessionStorage",
        "sessionExpiredRedirectScheduled",
        "location.assign('/login?reason=session_expired')",
    ):
        if marker not in helper:
            failures.append(f"session recovery helper missing: {marker}")
    if "redirect=${encodeURIComponent" in client or "/login?reason=session_expired&redirect=" in client:
        failures.append("401 handling must not expose the retained route in the login URL")
    if "redirectForExpiredSession();" not in client:
        failures.append("401 handling must use the shared single-redirect recovery helper")
    for marker in (
        "data-session-expired-notice",
        "route.query.reason === 'session_expired'",
        "readSessionExpiredReturnPath()",
        "clearSessionExpiredReturnPath()",
        "const recoveringExpiredSession = sessionExpired.value",
        "if (recoveringExpiredSession) clearSessionExpiredReturnPath()",
        "normalizeSafeLoginReturnPath",
    ):
        if marker not in login:
            failures.append(f"LoginView missing session recovery marker: {marker}")
    if "账号或密码错误" not in login or "登录状态已过期" not in login:
        failures.append("credential failure and expired-session explanations must remain distinct")
    return failures


if __name__ == "__main__":
    errors = validate()
    if errors:
        print("[frontend_system_state_recovery_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("[frontend_system_state_recovery_guard] PASS url_leak=0 distinct_notice=1 single_redirect=1")
