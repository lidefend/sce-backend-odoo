#!/usr/bin/env python3
"""Fail-closed hardening of the sole active production Web administrator."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from typing import Any


TARGET_DATABASE = "sc_production"
TARGET_LOGIN = "admin"
CONFIRMATION = "YES_HARDEN_FRESH_PRODUCTION_ADMIN"
SECRET_NAME = "SC_BOOTSTRAP_ADMIN_PASSWORD"


class AdminHardenError(RuntimeError):
    pass


def _secret(active_env: Mapping[str, str]) -> str:
    value = active_env.get(SECRET_NAME, "")
    if not value:
        raise AdminHardenError(f"{SECRET_NAME} is required")
    if len(value) < 20:
        raise AdminHardenError(f"{SECRET_NAME} must contain at least 20 characters")
    if not (
        any(character.islower() for character in value)
        and any(character.isupper() for character in value)
        and any(character.isdigit() for character in value)
        and any(not character.isalnum() for character in value)
    ):
        raise AdminHardenError(
            f"{SECRET_NAME} must contain upper, lower, digit, and symbol characters"
        )
    if value.casefold() == TARGET_LOGIN.casefold():
        raise AdminHardenError(f"{SECRET_NAME} must not be the default credential")
    return value


def validate_control_plane(active_env: Mapping[str, str]) -> None:
    if active_env.get("ENV") != "prod":
        raise AdminHardenError("ENV=prod is required")
    if active_env.get("PROD_DANGER") != "1":
        raise AdminHardenError("PROD_DANGER=1 is required")
    if active_env.get("TARGET_DB") != TARGET_DATABASE:
        raise AdminHardenError("TARGET_DB must be sc_production")
    if active_env.get("CONFIRM_ADMIN_HARDEN") != CONFIRMATION:
        raise AdminHardenError(
            "CONFIRM_ADMIN_HARDEN=YES_HARDEN_FRESH_PRODUCTION_ADMIN is required"
        )
    _secret(active_env)


def harden_admin(odoo_env: Any, active_env: Mapping[str, str]) -> dict[str, Any]:
    validate_control_plane(active_env)
    password = _secret(active_env)

    users = odoo_env["res.users"].sudo()
    target = users.with_context(active_test=False).search(
        [("login", "=", TARGET_LOGIN)]
    )
    if len(target) != 1:
        raise AdminHardenError("expected exactly one Web administrator login=admin")
    if not target.active:
        raise AdminHardenError("the Web administrator login=admin is inactive")

    system_group = odoo_env.ref("base.group_system")
    active_system_admins = system_group.users.filtered(lambda user: user.active)
    if len(active_system_admins) != 1 or active_system_admins.id != target.id:
        raise AdminHardenError(
            "active system administrator inventory differs from the approved account"
        )

    target.write({"password": password})
    odoo_env.cr.commit()
    return {"status": "PASS", "login": TARGET_LOGIN, "user_id": target.id}


def main() -> int:
    try:
        if "env" in globals():
            result = harden_admin(globals()["env"], os.environ)
            print("[production.admin.harden] " + json.dumps(result, sort_keys=True))
        else:
            validate_control_plane(os.environ)
            print(
                "[production.admin.harden] PREFLIGHT PASS "
                f"database={TARGET_DATABASE} login={TARGET_LOGIN}"
            )
    except AdminHardenError as exc:
        raise SystemExit(f"[production.admin.harden] BLOCKED: {exc}") from exc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
