#!/usr/bin/env python3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VIEW = ROOT / "frontend/apps/web/src/views/ApiKeyManagementView.vue"
API = ROOT / "frontend/apps/web/src/api/authCredentials.ts"
LOGIN = ROOT / "frontend/apps/web/src/views/LoginView.vue"


def require(text, marker, path):
    if marker not in text:
        raise SystemExit(f"[auth-credential-frontend-guard] missing {marker!r} in {path}")


def main():
    view_text = VIEW.read_text(encoding="utf-8")
    api_text = API.read_text(encoding="utf-8")
    login_text = LOGIN.read_text(encoding="utf-8")
    managed_surface = f"{view_text}\n{api_text}"

    for forbidden in ("localStorage", "sessionStorage", "indexedDB", "console.log", "console.info"):
        if forbidden in managed_surface:
            raise SystemExit(
                f"[auth-credential-frontend-guard] secret-bearing surface must not use {forbidden}"
            )
    require(view_text, "onBeforeUnmount", VIEW)
    require(view_text, "clearOneTimeSecret", VIEW)
    require(view_text, "resetSensitiveInputs", VIEW)
    require(view_text, 'data-secret-display="once"', VIEW)
    require(view_text, 'data-evidence-sensitive="api_key"', VIEW)
    require(api_text, "credential: { type: 'password'", API)
    require(api_text, "auth.credential.revoke", API)
    if "api_key" in login_text.lower():
        raise SystemExit(
            "[auth-credential-frontend-guard] normal browser login must not acquire API-key semantics"
        )

    print("[auth-credential-frontend-guard] PASS")


if __name__ == "__main__":
    main()
