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
