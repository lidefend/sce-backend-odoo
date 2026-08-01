#!/usr/bin/env python3
"""Governed, interactive password reset for one production internal user.

The password is collected exclusively from ``/dev/tty`` with ``getpass``.  It
is never accepted through argv, environment variables, stdin, or a file.
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import re
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


TARGET_DATABASE = "sc_production"
TARGET_ENVIRONMENT = "prod"
MINIMUM_PASSWORD_LENGTH = 12
LOGIN_PATTERN = re.compile(r"^[A-Za-z0-9_.@+-]{1,128}$")
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


class PasswordResetError(RuntimeError):
    pass


def _digest(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def validate_request(database: str, login: str, active_env: Mapping[str, str]) -> None:
    if database != TARGET_DATABASE:
        raise PasswordResetError("database must be sc_production")
    if not LOGIN_PATTERN.fullmatch(login):
        raise PasswordResetError("login format is invalid")
    if active_env.get("ENV") != TARGET_ENVIRONMENT or active_env.get("PROD_DANGER") != "1":
        raise PasswordResetError("ENV=prod and PROD_DANGER=1 are required")


def validate_tool_root(tool_root: Path) -> str:
    if not tool_root.is_absolute() or tool_root.is_symlink():
        raise PasswordResetError("immutable deployment-tool root is required")
    resolved = tool_root.resolve(strict=True)
    marker = resolved / "DEPLOYMENT_TOOL_SHA"
    if not marker.is_file() or marker.is_symlink():
        raise PasswordResetError("deployment-tool identity marker is missing")
    source_sha = marker.read_text(encoding="utf-8").strip()
    if not FULL_SHA.fullmatch(source_sha) or resolved.name != source_sha:
        raise PasswordResetError("deployment-tool identity differs")
    expected_script = resolved / "scripts/ops/production_user_password_reset.py"
    if expected_script.resolve(strict=True) != Path(__file__).resolve(strict=True):
        raise PasswordResetError("password-reset script is outside the immutable tool root")
    return source_sha


def validate_password(password: str, login: str) -> None:
    if len(password) < MINIMUM_PASSWORD_LENGTH:
        raise PasswordResetError("new password must contain at least 12 characters")
    if not any(character.isalpha() for character in password):
        raise PasswordResetError("new password must contain a letter")
    if not any(character.isdigit() for character in password):
        raise PasswordResetError("new password must contain a digit")
    if password.casefold() == login.casefold():
        raise PasswordResetError("new password must differ from the login")


def prompt_password(
    login: str,
    *,
    prompt: Callable[..., str] = getpass.getpass,
) -> str:
    first = prompt(f"New password for {login}: ")
    second = prompt("Repeat new password: ")
    if first != second:
        raise PasswordResetError("password entries do not match")
    validate_password(first, login)
    return first


def _record_xmlids(records: Any) -> list[str]:
    if not records:
        return []
    mapping = records.get_external_id()
    return sorted(mapping.get(record.id) or f"{record._name}:dbid:{record.id}" for record in records)


def _scope_snapshot(odoo_env: Any, user: Any) -> dict[str, Any]:
    employee = getattr(user, "employee_id", False)
    job = employee.job_id if employee and getattr(employee, "job_id", False) else False
    visible_menu_ids = sorted(
        odoo_env["ir.ui.menu"].with_user(user).with_context(debug=False)._visible_menu_ids()
    )
    return {
        "login": str(user.login),
        "active": bool(user.active),
        "share": bool(user.share),
        "groups": _record_xmlids(user.groups_id),
        "primary_company": _record_xmlids(user.company_id),
        "allowed_companies": _record_xmlids(user.company_ids),
        "job": _record_xmlids(job),
        "visible_menu_ids": visible_menu_ids,
    }


def _other_users_fingerprint(odoo_env: Any, target_id: int) -> str:
    rows = []
    users = odoo_env["res.users"].sudo().with_context(active_test=False).search(
        [("id", "!=", target_id)], order="id"
    )
    for user in users:
        rows.append(
            {
                "id": user.id,
                "login": user.login,
                "active": bool(user.active),
                "share": bool(user.share),
                "groups": sorted(user.groups_id.ids),
                "company": user.company_id.id,
                "companies": sorted(user.company_ids.ids),
                "write_date": str(user.write_date or ""),
            }
        )
    return _digest(rows)


def _resolve_target(odoo_env: Any, login: str) -> tuple[Any, str]:
    users = odoo_env["res.users"].sudo().with_context(active_test=False)
    target = users.search([("login", "=", login)])
    internal_group = odoo_env.ref("base.group_user", raise_if_not_found=False)
    portal_group = odoo_env.ref("base.group_portal", raise_if_not_found=False)
    if len(target) != 1:
        raise PasswordResetError("login must resolve to exactly one user")
    if not target.active:
        raise PasswordResetError("target user must be active")
    if target.share or not internal_group or internal_group not in target.groups_id:
        raise PasswordResetError("target user must be internal and non-share")
    if portal_group and portal_group in target.groups_id:
        raise PasswordResetError("target user must not belong to the portal group")

    tenant_key = str(
        odoo_env["ir.config_parameter"].sudo().get_param("sc.runtime.tenant_key", "") or ""
    ).strip()
    try:
        identity_model = odoo_env["sc.tenant.payload.external.identity"]
    except KeyError:
        identity_model = None
    if not tenant_key or not identity_model:
        raise PasswordResetError("production tenant identity is unresolved")
    identities = identity_model.sudo().search(
        [
            ("tenant_key", "=", tenant_key),
            ("model_name", "=", "res.users"),
            ("res_id", "=", target.id),
        ]
    )
    if len(identities) != 1 or not identities.external_key:
        raise PasswordResetError("target immutable user identity must resolve uniquely")
    return target, _digest(str(identities.external_key))


def reset_password(odoo_env: Any, login: str, password: str) -> dict[str, Any]:
    target, immutable_id_digest = _resolve_target(odoo_env, login)
    before = _scope_snapshot(odoo_env, target)
    other_users_before = _other_users_fingerprint(odoo_env, target.id)

    try:
        target.write({"password": password})
    except Exception as exc:
        raise PasswordResetError(
            f"Odoo ORM password write failed ({type(exc).__name__})"
        ) from None

    after = _scope_snapshot(odoo_env, target)
    other_users_after = _other_users_fingerprint(odoo_env, target.id)
    preserved_keys = (
        "login",
        "active",
        "share",
        "groups",
        "primary_company",
        "allowed_companies",
        "job",
        "visible_menu_ids",
    )
    if any(before[key] != after[key] for key in preserved_keys):
        raise PasswordResetError("target role, job, company, or menu scope changed")
    if other_users_before != other_users_after:
        raise PasswordResetError("another user changed during the password reset transaction")

    return {
        "LOGIN": login,
        "UNIQUE_USER_MATCH": True,
        "INTERNAL_USER": True,
        "USER_ACTIVE": True,
        "IMMUTABLE_USER_ID_SHA256": immutable_id_digest,
        "NAME_SHA256": _digest(str(target.name or "")),
        "PASSWORD_RESET": "PASS",
        "ROLE_SCOPE_PRESERVED": True,
        "COMPANY_SCOPE_PRESERVED": True,
        "MENU_SCOPE_PRESERVED": True,
        "OTHER_USER_WRITES": 0,
        "LOGIN_WRITES": 0,
        "ROLE_WRITES": 0,
        "COMPANY_SCOPE_WRITES": 0,
        "BUSINESS_DATA_WRITES": 0,
        "WUTAO_PASSWORD_WRITES" if login == "wutao" else "TARGET_PASSWORD_WRITES": 1,
    }


def _load_http_helpers(tool_root: Path) -> Any:
    import importlib.util

    helper_path = tool_root / "scripts/ops/production_acceptance_harness.py"
    spec = importlib.util.spec_from_file_location("governed_password_reset_http", helper_path)
    if not spec or not spec.loader:
        raise PasswordResetError("HTTP verification helper is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _first_menu_id(value: Any) -> int:
    if not isinstance(value, list):
        return 0
    for node in value:
        if not isinstance(node, dict):
            continue
        children = node.get("children")
        nested = _first_menu_id(children)
        if nested:
            return nested
        raw = node.get("menu_id") or node.get("id")
        try:
            menu_id = int(raw or 0)
        except (TypeError, ValueError):
            menu_id = 0
        if menu_id > 0:
            return menu_id
    return 0


def verify_http_access(tool_root: Path, base_url: str, database: str, login: str, password: str) -> dict[str, Any]:
    if not base_url.startswith(("http://", "https://")):
        raise PasswordResetError("HTTP verification base URL is invalid")
    helper = _load_http_helpers(tool_root)
    endpoint = base_url.rstrip("/") + "/api/v1/intent?db=" + database
    db_headers = {"X-Odoo-DB": database, "X-DB": database}
    login_status, login_payload = helper.http_json(
        endpoint,
        {"intent": "login", "params": {"db": database, "login": login, "password": password}},
        headers={**db_headers, "X-Anonymous-Intent": "1"},
    )
    login_data = helper.unwrap_data(login_payload)
    token = str(login_data.get("token") or "").strip()
    if login_status != 200 or login_payload.get("ok") is not True or not token:
        raise PasswordResetError("new-password HTTP login verification failed")
    headers = {**db_headers, "Authorization": f"Bearer {token}"}
    init_status, init_payload = helper.http_json(
        endpoint,
        {"intent": "system.init", "params": {"db": database, "with": ["workspace_home"]}},
        headers=headers,
    )
    init_data = helper.unwrap_data(init_payload)
    navigation = []
    for key in ("nav", "menus", "navigation"):
        if isinstance(init_data.get(key), list):
            navigation = init_data[key]
            break
    if not navigation and isinstance(init_data.get("workspace_home"), dict):
        workspace = init_data["workspace_home"]
        for key in ("nav", "menus", "navigation"):
            if isinstance(workspace.get(key), list):
                navigation = workspace[key]
                break
    menu_id = _first_menu_id(navigation)
    if init_status != 200 or init_payload.get("ok") is not True or not menu_id:
        raise PasswordResetError("system.init or authorized navigation verification failed")
    menu_status, menu_payload = helper.http_json(
        endpoint,
        {
            "intent": "ui.contract",
            "params": {
                "db": database,
                "op": "get",
                "subject": "menu",
                "id": menu_id,
                "with_data": True,
                "limit": 1,
            },
        },
        headers=headers,
    )
    if menu_status != 200 or menu_payload.get("ok") is not True:
        raise PasswordResetError("authorized menu access verification failed")
    return {
        "LOGIN_VERIFICATION": "PASS",
        "SYSTEM_INIT": "PASS",
        "AUTHORIZED_MENU_ACCESS": "PASS",
    }


def _odoo_environment(config_path: str, database: str) -> Any:
    import odoo
    from odoo.tools import config

    config.parse_config(["--config", config_path, "--database", database, "--no-http"])
    odoo.service.server.start(preload=[], stop=True)
    registry = odoo.registry(database)
    return odoo, registry


def execute(database: str, login: str, config_path: str, base_url: str, tool_root: Path) -> dict[str, Any]:
    validate_request(database, login, os.environ)
    source_sha = validate_tool_root(tool_root)
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise PasswordResetError("a real interactive terminal is required")
    stage = "odoo_bootstrap"
    try:
        odoo, registry = _odoo_environment(config_path, database)
        stage = "target_preflight"
        with registry.cursor() as cursor:
            context_env = odoo.api.Environment(cursor, odoo.SUPERUSER_ID, {})
            context = context_env["res.users"].context_get()
            odoo_env = odoo.api.Environment(cursor, odoo.SUPERUSER_ID, context)
            target, _immutable_id = _resolve_target(odoo_env, login)
            before = _scope_snapshot(odoo_env, target)
            print(
                "[ops.user.password-reset] PREFLIGHT PASS "
                + json.dumps(
                    {
                        "database": database,
                        "login": login,
                        "user_id": target.id,
                        "active": before["active"],
                        "share": before["share"],
                        "role_scope_sha256": _digest(before["groups"]),
                        "company_scope_sha256": _digest(
                            [before["primary_company"], before["allowed_companies"]]
                        ),
                        "menu_scope_sha256": _digest(before["visible_menu_ids"]),
                        "tool_source_sha": source_sha,
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
            stage = "password_prompt"
            password = prompt_password(login)
            stage = "orm_password_reset"
            result = reset_password(odoo_env, login, password)
            cursor.commit()
        stage = "http_verification"
        result.update(verify_http_access(tool_root, base_url, database, login, password))
    except PasswordResetError:
        raise
    except Exception as exc:
        raise PasswordResetError(f"{stage} failed ({type(exc).__name__})") from None
    password = ""  # Drop the last application reference before reporting.
    result.update(
        {
            "RESULT": "PASS",
            "WUTAO_USER_ACCESS_READY" if login == "wutao" else "TARGET_USER_ACCESS_READY": True,
            "TOOL_SOURCE_SHA": source_sha,
        }
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True)
    parser.add_argument("--login", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--tool-root", required=True)
    args = parser.parse_args()
    try:
        result = execute(
            args.database,
            args.login,
            args.config,
            args.base_url,
            Path(args.tool_root),
        )
    except PasswordResetError as exc:
        raise SystemExit(f"[ops.user.password-reset] BLOCKED: {exc}") from exc
    except Exception as exc:
        raise SystemExit(
            "[ops.user.password-reset] BLOCKED: unexpected failure "
            f"({type(exc).__name__})"
        ) from None
    print("[ops.user.password-reset] " + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
