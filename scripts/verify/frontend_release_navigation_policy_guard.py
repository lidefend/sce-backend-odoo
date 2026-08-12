#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "config/frontend/authoritative_navigation_v1.json"
POLICY = ROOT / "addons/smart_construction_core/core_extension_policy_maps.py"
ROLE_MAP = {
    "finance": "finance",
    "project_a_member": "project_member",
    "pm": "pm",
    "owner": "owner",
}


def _load_role_policy() -> dict:
    tree = ast.parse(POLICY.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "ROLE_SURFACE_OVERRIDES"
            for target in node.targets
        ):
            value = ast.literal_eval(node.value)
            if isinstance(value, dict):
                return value
    raise ValueError("ROLE_SURFACE_OVERRIDES is missing")


def validate(manifest: dict, policies: dict) -> list[str]:
    expected_roles = manifest.get("roles") if isinstance(manifest, dict) else {}
    errors: list[str] = []

    for manifest_role, policy_role in ROLE_MAP.items():
        expected_row = expected_roles.get(manifest_role) or {}
        browser_keys = {str(key).strip() for key in expected_row.get("browser_leaf_keys") or []}
        browser_count = int(expected_row.get("browser_expected_count") or 0)
        expected = {
            str(key).split("|", 1)[0]
            for key in expected_row.get("leaf_keys") or []
            if str(key).strip()
        }
        policy = policies.get(policy_role) or {}
        released = {
            str(xmlid).strip()
            for field in ("primary_menu_xmlids", "role_home_menu_xmlids")
            for xmlid in policy.get(field) or []
            if str(xmlid).strip()
        }
        contextual = {str(item).strip() for item in policy.get("contextual_menu_xmlids") or []}
        denied = {str(item).strip() for item in policy.get("denied_menu_xmlids") or []}
        declared_count = int(expected_row.get("expected_count") or 0)
        if declared_count != len(expected):
            errors.append(
                f"{manifest_role}: expected_count={declared_count} identity_count={len(expected)}"
            )
        if browser_count != len(browser_keys) or not browser_keys:
            errors.append(
                f"{manifest_role}: browser_expected_count={browser_count} "
                f"identity_count={len(browser_keys)}"
            )
        browser_menu_xmlids = {key.split("|", 1)[0] for key in browser_keys}
        if not browser_menu_xmlids.issubset(expected):
            errors.append(
                f"{manifest_role}: browser projection outside released policy="
                f"{sorted(browser_menu_xmlids - expected)}"
            )
        if released != expected:
            errors.append(
                f"{manifest_role}: release projection differs "
                f"missing={sorted(expected - released)} unexpected={sorted(released - expected)}"
            )
        if released & contextual:
            errors.append(f"{manifest_role}: released/contextual overlap={sorted(released & contextual)}")
        if released & denied:
            errors.append(f"{manifest_role}: released/denied overlap={sorted(released & denied)}")
    return errors


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    errors = validate(manifest, _load_role_policy())
    if errors:
        print("[frontend_release_navigation_policy_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        return 2
    roles = manifest.get("roles") if isinstance(manifest, dict) else {}
    released_leaf_identities = sum(
        len((roles.get(role) or {}).get("leaf_keys") or [])
        for role in ROLE_MAP
    )
    print(
        "[frontend_release_navigation_policy_guard] PASS "
        f"roles={len(ROLE_MAP)} released_leaf_identities={released_leaf_identities}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
