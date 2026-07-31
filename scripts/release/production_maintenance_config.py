#!/usr/bin/env python3
"""Fail-closed validation for short-lived production maintenance containers."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path


EXPECTED_CONFIG = Path("/opt/sce-runtime/config/odoo.conf")
EXPECTED_DATABASE = "sc_production"
EXPECTED_DATA_DIR = Path("/opt/sce-runtime")
LEGACY_ATTACHMENTS = Path("/data/odoo/legacy_attachments")
TENANT = re.compile(r"^[a-z][a-z0-9_]{2,62}$")
MODULE = re.compile(r"^[a-z][a-z0-9_]{1,62}$")
REQUIRED_ADDONS = {
    "/usr/lib/python3/dist-packages/odoo/addons",
    "/mnt/product-addons",
    "/mnt/customer-addons",
}
CUSTOMER_ADDONS = Path("/mnt/customer-addons")


class MaintenanceConfigError(ValueError):
    pass


def parse_config(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", ";", "[")) or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def validate(path: Path, env: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ if env is None else env)
    if path != EXPECTED_CONFIG or not path.is_file() or path.is_symlink():
        raise MaintenanceConfigError("MAINTENANCE_CONFIG_PATH_INVALID")
    values = parse_config(path)
    database = (env.get("TARGET_DB") or env.get("ODOO_DB") or "").strip()
    tenant = (env.get("SC_TENANT_PAYLOAD_TENANT_KEY") or "").strip()
    modules = tuple(
        item.strip()
        for item in env.get("SC_PRODUCTION_CUSTOMER_MODULES", "").split(",")
        if item.strip()
    )
    if database != EXPECTED_DATABASE or values.get("db_name") != EXPECTED_DATABASE:
        raise MaintenanceConfigError("MAINTENANCE_DATABASE_MISMATCH")
    if env.get("PLATFORM_RELEASE_DB") != EXPECTED_DATABASE:
        raise MaintenanceConfigError("MAINTENANCE_PLATFORM_DATABASE_MISMATCH")
    if not TENANT.fullmatch(tenant):
        raise MaintenanceConfigError("MAINTENANCE_TENANT_MISMATCH")
    if (
        not modules
        or len(modules) != len(set(modules))
        or any(not MODULE.fullmatch(name) or name.endswith("_legacy") for name in modules)
    ):
        raise MaintenanceConfigError("MAINTENANCE_CUSTOMER_MODULE_CONTRACT_INVALID")
    if values.get("dbfilter") != r"^sc_production$":
        raise MaintenanceConfigError("MAINTENANCE_DBFILTER_MISMATCH")
    if values.get("list_db", "").lower() not in {"false", "0"}:
        raise MaintenanceConfigError("MAINTENANCE_LIST_DB_MUST_BE_DISABLED")
    if values.get("without_demo", "").lower() not in {"true", "1"}:
        raise MaintenanceConfigError("MAINTENANCE_DEMO_DATA_MUST_BE_DISABLED")
    if env.get("SC_MAINTENANCE_HTTP_DISABLED") != "1":
        raise MaintenanceConfigError("MAINTENANCE_HTTP_MUST_BE_DISABLED")
    data_dir = Path(values.get("data_dir", "")).resolve(strict=False)
    legacy = LEGACY_ATTACHMENTS.resolve(strict=False)
    if data_dir != EXPECTED_DATA_DIR or data_dir == legacy or legacy in data_dir.parents or data_dir in legacy.parents:
        raise MaintenanceConfigError("MAINTENANCE_DATA_DIR_INVALID")
    addons = {item.strip() for item in values.get("addons_path", "").split(",") if item.strip()}
    if not REQUIRED_ADDONS.issubset(addons):
        raise MaintenanceConfigError("MAINTENANCE_ADDONS_PATH_INCOMPLETE")
    expected_paths = {CUSTOMER_ADDONS / name for name in modules}
    if any(not path.is_dir() or not (path / "__manifest__.py").is_file() for path in expected_paths):
        raise MaintenanceConfigError("MAINTENANCE_CUSTOMER_MODULE_MISSING")
    actual_paths = {
        path
        for path in CUSTOMER_ADDONS.iterdir()
        if path.is_dir() and (path / "__manifest__.py").is_file()
    }
    if actual_paths != expected_paths:
        raise MaintenanceConfigError("MAINTENANCE_CUSTOMER_MODULE_SET_MISMATCH")
    if not re.fullmatch(r"[^:\s]+", values.get("db_host", "")):
        raise MaintenanceConfigError("MAINTENANCE_DATABASE_HOST_INVALID")
    return values


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) == 2 else Path("")
    try:
        values = validate(path)
    except (OSError, UnicodeError, MaintenanceConfigError) as exc:
        raise SystemExit(f"[production.maintenance-config] BLOCKED: {exc}") from exc
    print(
        "[production.maintenance-config] PASS "
        f"database={values['db_name']} config={EXPECTED_CONFIG} data_dir={EXPECTED_DATA_DIR}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
