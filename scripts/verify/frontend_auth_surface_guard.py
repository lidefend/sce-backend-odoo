#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LOGIN = ROOT / "frontend/apps/web/src/views/LoginView.vue"
ACTIVATION = ROOT / "frontend/apps/web/src/views/AccountActivationView.vue"
RECOVERY = ROOT / "frontend/apps/web/src/views/PasswordRecoveryView.vue"
API_KEY = ROOT / "frontend/apps/web/src/views/ApiKeyManagementView.vue"
BOUNDARY_GUARD = ROOT / "scripts/verify/frontend_page_contract_boundary_guard.py"
ORCHESTRATION_GUARD = ROOT / "scripts/verify/frontend_page_contract_orchestration_consumption_guard.py"
AUTH_CREDENTIAL_GUARD = ROOT / "scripts/verify/auth_credential_frontend_guard.py"
ACTIVATION_SECURITY_GUARD = ROOT / "scripts/verify/user_activation_security_contract.py"
PAGE_CONTRACTS_BUILDER = ROOT / "addons/smart_core/core/page_contracts_builder.py"
ACTION_TARGET_SCHEMA = ROOT / "addons/smart_core/core/action_target_schema.py"
PROFESSIONAL_COMPONENT_REGISTRY = ROOT / "frontend/apps/web/src/app/presentation/professionalComponentRegistry.ts"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.is_file() else ""


def _require(text: str, token: str, scope: str, errors: list[str]) -> None:
    if token not in text:
        errors.append(f"{scope} missing token: {token}")


def _forbid(text: str, token: str, scope: str, errors: list[str]) -> None:
    if token in text:
        errors.append(f"{scope} forbidden token present: {token}")


def _require_absent_from_exemption_set(text: str, token: str, scope: str, errors: list[str]) -> None:
    marker = "page_contract_exempt_views = {"
    start = text.find(marker)
    if start < 0:
        errors.append(f"{scope} missing exemption set declaration")
        return
    end = text.find("}", start)
    if end < 0:
        errors.append(f"{scope} exemption set declaration is unterminated")
        return
    exempt_block = text[start:end]
    if token in exempt_block:
        errors.append(f"{scope} exemption set forbidden token present: {token}")


def main() -> int:
    errors: list[str] = []
    login_text = _read(LOGIN)
    activation_text = _read(ACTIVATION)
    recovery_text = _read(RECOVERY)
    api_key_text = _read(API_KEY)
    boundary_text = _read(BOUNDARY_GUARD)
    orchestration_text = _read(ORCHESTRATION_GUARD)
    auth_credential_guard_text = _read(AUTH_CREDENTIAL_GUARD)
    activation_security_guard_text = _read(ACTIVATION_SECURITY_GUARD)
    page_contracts_builder_text = _read(PAGE_CONTRACTS_BUILDER)
    action_target_schema_text = _read(ACTION_TARGET_SCHEMA)
    professional_component_registry_text = _read(PROFESSIONAL_COMPONENT_REGISTRY)

    for path, text in (
        (LOGIN, login_text),
        (ACTIVATION, activation_text),
        (RECOVERY, recovery_text),
        (API_KEY, api_key_text),
        (BOUNDARY_GUARD, boundary_text),
        (ORCHESTRATION_GUARD, orchestration_text),
        (AUTH_CREDENTIAL_GUARD, auth_credential_guard_text),
        (ACTIVATION_SECURITY_GUARD, activation_security_guard_text),
        (PAGE_CONTRACTS_BUILDER, page_contracts_builder_text),
        (ACTION_TARGET_SCHEMA, action_target_schema_text),
        (PROFESSIONAL_COMPONENT_REGISTRY, professional_component_registry_text),
    ):
        if not text:
            errors.append(f"missing file: {path.relative_to(ROOT).as_posix()}")
    if errors:
        print("[frontend_auth_surface_guard] FAIL")
        for err in errors:
            print(f"- {err}")
        return 1

    for scope, text, page_key in (
        ("LoginView.vue", login_text, "login"),
        ("AccountActivationView.vue", activation_text, "account_activation"),
        ("PasswordRecoveryView.vue", recovery_text, "password_recovery"),
    ):
        _require(text, f"const pageContract = usePageContract('{page_key}');", scope, errors)
        _require(text, "import { executePageContractAction } from '../app/pageContractActionRuntime';", scope, errors)
        _require(text, "const pageActionIntent = pageContract.actionIntent;", scope, errors)
        _require(text, "const pageActionTarget = pageContract.actionTarget;", scope, errors)
        _require(text, "await executePageContractAction({", scope, errors)

    _require(boundary_text, '"ApiKeyManagementView.vue"', "frontend_page_contract_boundary_guard.py", errors)
    _require_absent_from_exemption_set(
        boundary_text,
        '"AccountActivationView.vue"',
        "frontend_page_contract_boundary_guard.py",
        errors,
    )
    _require_absent_from_exemption_set(
        boundary_text,
        '"PasswordRecoveryView.vue"',
        "frontend_page_contract_boundary_guard.py",
        errors,
    )

    for token in (
        '"account_activation": {',
        '"password_recovery": {',
        '{"key": "open_login", "label": "返回登录", "intent": "ui.contract"}',
    ):
        _require(page_contracts_builder_text, token, "page_contracts_builder.py", errors)

    for token in (
        'if key == "open_login":',
        'return route_path_target("/login")',
        'if key == "open_account_activation":',
        'return route_path_target("/activate-account")',
        'if key == "open_password_recovery":',
        'return route_path_target("/password-recovery")',
    ):
        _require(action_target_schema_text, token, "action_target_schema.py", errors)

    _require(auth_credential_guard_text, "[auth-credential-frontend-guard] PASS", "auth_credential_frontend_guard.py", errors)
    _require(activation_security_guard_text, "USER_ACTIVATION_SECURITY_CONTRACT=PASS", "user_activation_security_contract.py", errors)
    _require(orchestration_text, "AccountActivationView.vue", "frontend_page_contract_orchestration_consumption_guard.py", errors)
    _require(orchestration_text, "PasswordRecoveryView.vue", "frontend_page_contract_orchestration_consumption_guard.py", errors)
    for token in (
        "registration('sc.auth.credential_entry', 'credential_entry', ['char'])",
        "registration('sc.auth.secret_confirmation', 'secret_confirmation', ['char'])",
        "registration('sc.auth.challenge_status', 'challenge_status', ['char', 'selection', 'text'])",
        "registration('sc.auth.one_time_secret', 'one_time_secret', ['char', 'text'], 'fail_closed')",
        "registration('sc.auth.support_action', 'support_action', ['action'])",
    ):
        _require(
            professional_component_registry_text,
            token,
            "professionalComponentRegistry.ts",
            errors,
        )

    if "const pageContract = usePageContract('api_key_management');" in api_key_text:
        errors.append("ApiKeyManagementView.vue must not silently join the ordinary auth page-contract family without an explicit high-sensitivity decision")

    if errors:
        print("[frontend_auth_surface_guard] FAIL")
        for err in errors:
            print(f"- {err}")
        return 1

    print("[frontend_auth_surface_guard] PASS contract_pages=3 exempt_high_sensitivity=1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
