#!/usr/bin/env python3
"""Prevent the migrated acceptance entrypoints from regaining environment debt."""
from __future__ import annotations

import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
MIGRATED = (
    "scripts/verify/frontend_full_product_audit.mjs",
    "scripts/verify/frontend_form_system_audit.mjs",
    "scripts/verify/frontend_geometry_scroll_audit.mjs",
)


def main() -> int:
    errors: list[str] = []
    environments = json.loads((ROOT / "config/frontend/acceptance_environments_v1.json").read_text(encoding="utf-8"))
    tools = json.loads((ROOT / "config/frontend/acceptance_tool_matrix_v1.json").read_text(encoding="utf-8"))
    if "base_url" in environments["profiles"]["daily"]:
        errors.append("daily profile must not embed a deployment address")
    if "base_url" in environments["profiles"]["production"]:
        errors.append("production profile must not embed a deployment address")
    if tools["tools"]["form-system-audit"]["profiles"] != ["local", "test"]:
        errors.append("full form-system audit must remain isolated from daily/production")
    managed = environments["profiles"]["local"].get("managed_runtime") or {}
    if managed.get("database_filter") != "^sc_frontend_acceptance$":
        errors.append("local managed runtime must exact-lock sc_frontend_acceptance")
    volumes = managed.get("volumes") or {}
    if len({volumes.get("database"), volumes.get("redis"), volumes.get("odoo")}) != 3:
        errors.append("local managed runtime must declare three distinct volume identities")
    if managed.get("credential_container") != f'{managed.get("compose_project")}-odoo-1':
        errors.append("local credential authority must be the managed compose Odoo container")
    runtime_entry = (ROOT / "scripts/dev/frontend_acceptance_runtime.sh").read_text(encoding="utf-8")
    for marker in (
        "preflight",
        "DB_DATA",
        "REDIS_DATA",
        "ODOO_DATA",
        "ODOO_DBFILTER",
        "validate_backend_runtime",
        "validate_frontend_runtime",
        "SC_SOURCE_REVISION",
        "SC_SOURCE_FINGERPRINT",
        "/mnt/source-addons",
        "POSTGRES_PASSWORD",
        "REUSED governed pid=",
    ):
        if marker not in runtime_entry:
            errors.append(f"managed runtime entry missing marker: {marker}")
    smart_core_upgrade = runtime_entry.find('SC_GOVERNED_MODULE_LIFECYCLE_ENTRY=1 MODULE=smart_core bash "$ROOT_DIR/scripts/mod/upgrade.sh"')
    construction_upgrade = runtime_entry.find(
        'SC_GOVERNED_MODULE_LIFECYCLE_ENTRY=1 MODULE=smart_construction_core bash "$ROOT_DIR/scripts/mod/upgrade.sh"'
    )
    if smart_core_upgrade < 0 or construction_upgrade < 0 or smart_core_upgrade >= construction_upgrade:
        errors.append("managed baseline upgrade must run smart_core before smart_construction_core")
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    for marker in ("DB_NAME: ${DB_NAME}", "ODOO_DBFILTER: ${ODOO_DBFILTER}", "LIST_DB: ${LIST_DB:-false}"):
        if marker not in compose:
            errors.append(f"Odoo compose environment missing managed identity marker: {marker}")
    for relative in MIGRATED:
        source = (ROOT / relative).read_text(encoding="utf-8")
        checks = {
            "daily host literal": r"1\.95\.85\.92",
            "database fallback": r"\|\|\s*['\"]sc_(?:demo|prod|prod_sim|frontend_acceptance)['\"]",
            "weak password fallback": r"\|\|\s*['\"](?:123456|demo|activity-tabs-acceptance-password)['\"]",
            "cwd dependency": r"process\.cwd\(\)",
            "ungoverned browser launch": r"\blaunchChromium\(",
            "numeric route fallback": r"['\"`]\/(?:a|m|r)\/\d+",
        }
        for label, pattern in checks.items():
            if re.search(pattern, source):
                errors.append(f"{relative}: {label}")
        if "resolveAcceptanceEnvironment" not in source or "acquireAcceptanceLease" not in source:
            errors.append(f"{relative}: canonical resolver/lease integration missing")
    form = (ROOT / MIGRATED[1]).read_text(encoding="utf-8")
    if "mode: 'exclusive-write'" not in form or "operation: 'isolated-write'" not in form:
        errors.append("form-system audit must declare isolated-write and exclusive-write")
    for relative in (MIGRATED[0], MIGRATED[2]):
        if "mode: 'shared-read'" not in (ROOT / relative).read_text(encoding="utf-8"):
            errors.append(f"{relative}: readonly shared lease missing")
    if errors:
        print("[frontend_acceptance_environment_source_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("[frontend_acceptance_environment_source_guard] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
