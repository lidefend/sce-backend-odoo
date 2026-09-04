#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Guard the inventory test-scene boundary.

A scene is "test-only" when its scene_key matches one of TEST_SCENE_PATTERNS or
appears in TEST_SCENE_KEYS.  Test-only scenes must stay at R1 to avoid leaking
into product dashboards (R3 evaluation) and into business navigation/route
strategies.  This guard fails when:

  1. a test scene is registered at R2+ (would be evaluated by product gates), or
  2. a test scene is registered without an `owner_module` (must trace back to
     the test/runtime owner module so production releases do not adopt it), or
  3. a test scene lives in a business `nav_group` other than the dedicated
     `others` bucket (forbidden to share nav_group with business scenes).

Non-test scenes must keep their maturity at R2+ when present in the matrix
(R0/R1 short-lived entry points are tracked separately in
`addons/smart_construction_scene/scene_registry.py::list_scene_entries`).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Hard-coded registry of test-only scenes.  Update intentionally when adding
# new automated test fixtures that may surface in the matrix.
TEST_SCENE_KEYS: set[str] = {
    "scene_smoke_default",
}

TEST_SCENE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^scene_smoke_"),
    re.compile(r"_smoke_default$"),
    re.compile(r"_test_scene$"),
    re.compile(r"^test\."),
)

# Nav-groups reserved for test fixtures.  Test scenes must live here, never in
# a business nav_group (e.g. project_management, contract_management).
TEST_NAV_GROUPS: set[str] = {"others", "test", "smoke"}

# Owner modules that indicate a scene is owned by a test/runtime layer.
TEST_OWNER_MODULES: set[str] = {
    "smart_construction_scene",  # registry ships test fixtures here
    "smart_core",                # generic core test fixtures
    "smart_scene",               # scene engine test fixtures
    "smart_construction_test",   # dedicated test addon if present
}

ALLOWED_TEST_MATURITY = {"R0", "R1"}


def _load_inventory(path: Path) -> dict[str, dict[str, str]]:
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    matrix_idx = -1
    for index, line in enumerate(lines):
        if line.strip().lower() == "## matrix":
            matrix_idx = index
            break
    if matrix_idx < 0:
        raise ValueError("missing section: ## Matrix")

    table_lines: list[str] = []
    for line in lines[matrix_idx + 1 :]:
        stripped = line.strip()
        if stripped.startswith("## "):
            break
        if "|" in stripped:
            table_lines.append(stripped)
    if len(table_lines) < 2:
        raise ValueError("matrix table missing header/body")

    header = [cell.strip() for cell in table_lines[0].strip().strip("|").split("|")]
    required = ["scene_key", "maturity_level", "owner_module", "nav_group"]
    if any(col not in header for col in required):
        raise ValueError(f"matrix header missing required columns: {required}")

    body = table_lines[1:]
    if body and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in body[0].strip().strip("|").split("|")):
        body = body[1:]

    out: dict[str, dict[str, str]] = {}
    for row in body:
        cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
        if len(cells) != len(header):
            continue
        item = dict(zip(header, cells))
        key = str(item.get("scene_key") or "").strip()
        if key:
            out[key] = item
    return out


def _is_test_scene(scene_key: str) -> bool:
    if scene_key in TEST_SCENE_KEYS:
        return True
    return any(pattern.search(scene_key) for pattern in TEST_SCENE_PATTERNS)


def main() -> int:
    parser = argparse.ArgumentParser(description="Enforce inventory test-scene boundary rules.")
    parser.add_argument("--inventory", default="docs/ops/scene_inventory_matrix_latest.md")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    inventory = _load_inventory(root / args.inventory)

    errors: list[str] = []

    for scene_key, row in sorted(inventory.items()):
        maturity = str(row.get("maturity_level") or "").strip().upper()
        owner = str(row.get("owner_module") or "").strip()
        nav_group = str(row.get("nav_group") or "").strip()

        if not _is_test_scene(scene_key):
            continue

        if maturity not in ALLOWED_TEST_MATURITY:
            errors.append(
                f"test scene must stay at R0/R1: {scene_key} (maturity_level={maturity})"
            )

        if not owner:
            errors.append(f"test scene missing owner_module: {scene_key}")
        elif owner not in TEST_OWNER_MODULES:
            errors.append(
                f"test scene owner_module must be a test layer: {scene_key} (owner_module={owner})"
            )

        if nav_group not in TEST_NAV_GROUPS:
            errors.append(
                f"test scene nav_group must be one of {sorted(TEST_NAV_GROUPS)}: {scene_key} (nav_group={nav_group})"
            )

    if errors:
        print("[scene_inventory_test_boundary_guard] FAIL")
        for item in errors:
            print(f"- {item}")
        return 1

    test_count = sum(1 for key in inventory if _is_test_scene(key))
    print("[scene_inventory_test_boundary_guard] PASS")
    print(f"- inventory_scene_count: {len(inventory)}")
    print(f"- test_scene_count: {test_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
