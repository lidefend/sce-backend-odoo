#!/usr/bin/env python3
"""Single-application lock for the list preference contract.

The product contract is declared by the server and applied exactly once, by the
frontend consumer, against the declared ``preference_policy``.  The server must
never fold a stored personal choice into a delivered contract, and the frontend
must have exactly one application site.  This guard reads the real files and
proves both halves plus the two registered non-application consumers, so the
"applied once" claim is checkable instead of being an implementation comment.

It is a static structural guard: it does not replace the runtime behaviour
evidence (``verify.local.dev.user_view_preference.runtime.orm``).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CONTRACT_ASSEMBLY_GLOBS = [
    "addons/smart_core/handlers/ui_contract_v2.py",
    "addons/smart_core/handlers/ui_contract_v2_adapters.py",
    "addons/smart_core/handlers/ui_contract_v2_projection.py",
    "addons/smart_core/handlers/ui_contract_v2_authority.py",
    "addons/smart_core/handlers/ui_contract_v2_constants.py",
    "addons/smart_core/handlers/ui_contract.py",
]

PREFERENCE_FORBIDDEN_TOKENS = [
    "sc.user.view.preference",
    "user_view_preference",
    "ListPreferencePolicy",
    "list_preference_policy",
]

PREFERENCE_HANDLER = "addons/smart_core/handlers/user_view_preference.py"
PREFERENCE_APPLY_FN = "_apply_list_preference_policy"

FRONTEND_ROOT = "frontend/apps/web/src"
FRONTEND_PROJECTION_MODULE = "app/runtime/listPreferenceProjection.ts"
FRONTEND_CONSUMERS = ["projectStoredListPreference(", "readStoredListPreference("]

# Registered read-only consumers of the preference store.  They report facts
# for an administrator audit surface; they never project a choice into a
# contract, so they are named here instead of being silently allowed.
NON_APPLICATION_CONSUMERS = {
    "addons/smart_core/handlers/business_config_surface.py": "admin audit overview/count of personal preference rows",
    "addons/smart_core/handlers/form_field_configuration.py": "admin list/search boundary audit of personal preference rows",
}


def _read(relative: str) -> str:
    path = ROOT / relative
    return path.read_text(encoding="utf-8", errors="ignore") if path.is_file() else ""


def _iter_frontend_sources():
    base = ROOT / FRONTEND_ROOT
    if not base.is_dir():
        return
    for path in sorted(base.rglob("*")):
        if path.suffix in (".ts", ".vue", ".js", ".tsx") and path.is_file():
            yield path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="", help="optional JSON report path")
    args = parser.parse_args()

    errors: list[str] = []
    report: dict = {
        "schema": "list-preference-single-application/v1",
        "server_declaration": {},
        "server_never_applies": {},
        "frontend_application_sites": {},
        "non_application_consumers": {},
        "status": "pass",
    }

    # 1. The contract/page-assembly layer must never read the preference store.
    for relative in CONTRACT_ASSEMBLY_GLOBS:
        source = _read(relative)
        if not source:
            errors.append(f"missing contract assembly file: {relative}")
            continue
        hits = [token for token in PREFERENCE_FORBIDDEN_TOKENS if token in source]
        report["server_never_applies"][relative] = {"forbidden_tokens_found": hits}
        if hits:
            errors.append(f"{relative} reaches the preference store/policy: {hits}")

    # 2. The one server-side application helper lives in exactly one file.
    helper_definition = re.compile(rf"\b(?:def|async def)\s+{PREFERENCE_APPLY_FN}\b")
    helper_reference = re.compile(rf"\b{re.escape(PREFERENCE_APPLY_FN)}\b")
    definitions: list[str] = []
    references: list[str] = []
    for path in sorted((ROOT / "addons").rglob("*.py")):
        relative = path.relative_to(ROOT).as_posix()
        if "/tests/" in relative:
            continue
        source = path.read_text(encoding="utf-8", errors="ignore")
        if helper_definition.search(source):
            definitions.append(relative)
        if helper_reference.search(source):
            references.append(relative)
    report["server_declaration"]["application_helper_definitions"] = definitions
    report["server_declaration"]["application_helper_references"] = references
    if definitions != [PREFERENCE_HANDLER]:
        errors.append(f"{PREFERENCE_APPLY_FN} must be defined once in {PREFERENCE_HANDLER}: {definitions}")
    outside = [item for item in references if item != PREFERENCE_HANDLER]
    if outside:
        errors.append(f"{PREFERENCE_APPLY_FN} is applied outside the preference handler: {outside}")

    # 3. The server declares the policy; it does not consume a stored order.
    v2 = _read("addons/smart_core/handlers/ui_contract_v2.py")
    declares_policy = '"preference_policy": {' in v2
    report["server_declaration"]["ui_contract_v2_declares_preference_policy"] = declares_policy
    if not declares_policy:
        errors.append("ui_contract_v2 no longer declares preference_policy for the list profile")

    # 4. The frontend has exactly one application site.
    call_sites: dict[str, list[str]] = {name: [] for name in FRONTEND_CONSUMERS}
    for path in _iter_frontend_sources():
        relative = path.relative_to(ROOT).as_posix()
        source = path.read_text(encoding="utf-8", errors="ignore")
        for name in FRONTEND_CONSUMERS:
            for line_number, line in enumerate(source.splitlines(), start=1):
                if name not in line or line.lstrip().startswith(("import ", "//")):
                    continue
                if relative.endswith(FRONTEND_PROJECTION_MODULE) and line.lstrip().startswith("export function"):
                    continue
                call_sites[name].append(f"{relative}:{line_number}")
    report["frontend_application_sites"] = call_sites
    for name, sites in call_sites.items():
        if len(sites) != 1:
            errors.append(f"{name} must have exactly one frontend consumer, found {sites}")

    # 5. Name the read-only consumers so the split is explicit, not implied.
    for relative, purpose in NON_APPLICATION_CONSUMERS.items():
        source = _read(relative)
        report["non_application_consumers"][relative] = {
            "purpose": purpose,
            "reads_preference_store": "sc.user.view.preference" in source,
            "applies_preference": PREFERENCE_APPLY_FN in source,
        }
        if source and PREFERENCE_APPLY_FN in source:
            errors.append(f"{relative} is a read-only consumer but applies the preference policy")

    report["errors"] = errors
    report["status"] = "pass" if not errors else "fail"
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    print(payload)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
