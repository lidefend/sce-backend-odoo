#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fact-layer authority guard (ARCH-DECISION-010).

Facts (model/view/permission/groups) are the only maintained layer. Mechanisms
(role_surface, scenario projection, frontend) must only read and project facts,
never own them. This guard fails when a mechanism hard-codes product entry
exposure (role -> menu lists) instead of deriving it from native menu/action
groups.

Scope today: smart_construction_core/core_extension_policy_maps.py
ROLE_SURFACE_OVERRIDES must not carry non-empty primary_menu_xmlids lists.
"""
from __future__ import annotations

import ast
import xml.etree.ElementTree as ET
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
POLICY_MAPS = ROOT / "addons/smart_construction_core/core_extension_policy_maps.py"
MODULE_ROOT = ROOT / "addons/smart_construction_core"


def violations() -> list[dict]:
    found: list[dict] = []
    found.extend(_role_surface_exposure_violations())
    found.extend(_role_group_direct_authorization_violations())
    return found


def _role_surface_exposure_violations() -> list[dict]:
    tree = ast.parse(POLICY_MAPS.read_text(encoding="utf-8"))
    found: list[dict] = []
    role_surface = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "ROLE_SURFACE_OVERRIDES" for t in node.targets
        ):
            role_surface = node.value
            break
    if role_surface is None or not isinstance(role_surface, ast.Dict):
        return [{"kind": "role_surface_absent", "message": "ROLE_SURFACE_OVERRIDES not found"}]
    for key, value in zip(role_surface.keys, role_surface.values):
        role = getattr(key, "s", "") if isinstance(key, ast.Constant) else ""
        if not role or not isinstance(value, ast.Dict):
            continue
        for field_key, field_value in zip(value.keys, value.values):
            field = getattr(field_key, "s", "") if isinstance(field_key, ast.Constant) else ""
            if field != "primary_menu_xmlids":
                continue
            count = len(field_value.elts) if isinstance(field_value, ast.List) else -1
            if count != 0:
                found.append({
                    "kind": "role_surface_owns_exposure",
                    "role": role,
                    "field": field,
                    "count": count,
                })
    return found


def _role_group_direct_authorization_violations() -> list[dict]:
    """Reject role-bound entry carriers, not native business field permissions.

    ARCH-010 makes model/view/permission/group data authoritative. A field's
    native groups declaration is not a parallel role-menu exposure list.
    """
    found = []
    for path in MODULE_ROOT.rglob("*.xml"):
        root = ET.parse(path).getroot()
        for node in root.iter():
            if node.tag == "menuitem":
                bindings = node.attrib.get("groups", "")
            elif node.tag == "record" and (node.attrib.get("model", "").startswith("ir.actions.")
                                           or node.attrib.get("model") in ("ir.ui.menu", "ir.ui.view")):
                bindings = " ".join(ET.tostring(field, encoding="unicode") for field in node.findall("field")
                                    if field.attrib.get("name") in ("groups", "groups_id"))
            else:
                continue
            if "group_sc_role_" in bindings:
                found.append({"kind": "role_group_direct_authorization",
                              "file": str(path.relative_to(ROOT)), "carrier": node.attrib.get("id", "")})
    return found


def main() -> int:
    items = violations()
    if not items:
        print("fact_layer_authority_guard PASS: no role_surface hard-coded exposure lists")
        return 0
    print("fact_layer_authority_guard FAIL: mechanisms own fact-layer exposure")
    for item in items:
        print(f"  - {item}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
