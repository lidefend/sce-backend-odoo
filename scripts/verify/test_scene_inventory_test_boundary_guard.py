#!/usr/bin/env python3
"""Unit tests for scene_inventory_test_boundary_guard (hermetic).

Exercises the test-scene boundary rules: R0/R1-only maturity, required
owner_module in the test layer set, and reserved nav_group bucket.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import scene_inventory_test_boundary_guard as guard  # noqa: E402


HEADER = (
    "# Scene Inventory Matrix\n\n## Matrix\n\n"
    "| scene_key | name | domain | route_target | nav_group | maturity_level | owner_module | next_action |\n"
    "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
)


def _build_inventory(rows: list[tuple[str, str, str, str]]) -> str:
    """rows = [(scene_key, maturity, owner_module, nav_group), ...]"""
    lines = [HEADER]
    for scene_key, maturity, owner, nav in rows:
        lines.append(
            f"| {scene_key} | n | d | /s/{scene_key} | {nav} | {maturity} | {owner} | next |\n"
        )
    return "".join(lines)


class TestBoundaryDetectionTests(unittest.TestCase):
    def test_explicit_test_key_detected(self) -> None:
        self.assertTrue(guard._is_test_scene("scene_smoke_default"))

    def test_pattern_smoke_prefix_detected(self) -> None:
        self.assertTrue(guard._is_test_scene("scene_smoke_extra"))

    def test_pattern_test_dot_detected(self) -> None:
        self.assertTrue(guard._is_test_scene("test.something"))

    def test_business_scene_not_flagged(self) -> None:
        # Plain business scenes must not match the smoke/test patterns.
        self.assertFalse(guard._is_test_scene("projects.list"))
        self.assertFalse(guard._is_test_scene("contract.center"))
        # Anything starting with scene_smoke_ is a test scene by design.
        self.assertTrue(guard._is_test_scene("scene_smoke_commercial"))


class TestBoundaryMatrixTests(unittest.TestCase):
    def test_passes_when_test_scene_at_r1_with_test_owner_and_others_nav(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "inv.md"
            path.write_text(
                _build_inventory([("scene_smoke_default", "R1", "smart_construction_scene", "others")]),
                encoding="utf-8",
            )
            loaded = guard._load_inventory(path)
            self.assertIn("scene_smoke_default", loaded)
            row = loaded["scene_smoke_default"]
            self.assertEqual(row["maturity_level"], "R1")
            self.assertEqual(row["owner_module"], "smart_construction_scene")
            self.assertEqual(row["nav_group"], "others")

    def test_r0_test_scene_also_passes_maturity(self) -> None:
        # R0 is in ALLOWED_TEST_MATURITY (R0/R1 only).
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "inv.md"
            path.write_text(
                _build_inventory([("scene_smoke_default", "R0", "smart_construction_scene", "others")]),
                encoding="utf-8",
            )
            loaded = guard._load_inventory(path)
            self.assertEqual(loaded["scene_smoke_default"]["maturity_level"], "R0")

    def test_inventory_loader_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "inv.md"
            path.write_text(
                _build_inventory(
                    [
                        ("scene_smoke_default", "R1", "smart_construction_scene", "others"),
                        ("projects.list", "R3", "smart_construction_scene", "project_management"),
                    ]
                ),
                encoding="utf-8",
            )
            loaded = guard._load_inventory(path)
            self.assertEqual(set(loaded.keys()), {"scene_smoke_default", "projects.list"})

    def test_inventory_loader_rejects_missing_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "inv.md"
            path.write_text(
                "# inv\n\n## Matrix\n\n| scene_key | name |\n| --- | --- |\n| a | b\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                guard._load_inventory(path)

    def test_test_owner_modules_set_includes_runtime_layers(self) -> None:
        # guard rails: changing this set is a deliberate maintainer decision.
        self.assertIn("smart_construction_scene", guard.TEST_OWNER_MODULES)
        self.assertIn("smart_core", guard.TEST_OWNER_MODULES)
        self.assertIn("smart_scene", guard.TEST_OWNER_MODULES)

    def test_test_nav_groups_are_business_isolated(self) -> None:
        # Nav groups must not overlap with business navigation buckets.
        business_navs = {"project_management", "contract_management", "cost_management"}
        self.assertTrue(business_navs.isdisjoint(guard.TEST_NAV_GROUPS))

    def test_pattern_matches_smoke_default_suffix(self) -> None:
        self.assertTrue(guard._is_test_scene("foo_smoke_default"))
        self.assertFalse(guard._is_test_scene("smoke_default_foo"))

    def test_pattern_matches_test_scene_suffix(self) -> None:
        self.assertTrue(guard._is_test_scene("foo_test_scene"))
        self.assertFalse(guard._is_test_scene("test_scene_foo"))


class TestBoundaryViolationLogicTests(unittest.TestCase):
    """Simulate the main() violation rules without invoking sys.exit."""

    def _violations_for(self, scene_key: str, maturity: str, owner: str, nav: str) -> list[str]:
        errors: list[str] = []
        if not guard._is_test_scene(scene_key):
            return errors
        if maturity.upper() not in guard.ALLOWED_TEST_MATURITY:
            errors.append(f"test scene must stay at R0/R1: {scene_key} (maturity_level={maturity})")
        if not owner:
            errors.append(f"test scene missing owner_module: {scene_key}")
        elif owner not in guard.TEST_OWNER_MODULES:
            errors.append(
                f"test scene owner_module must be a test layer: {scene_key} (owner_module={owner})"
            )
        if nav not in guard.TEST_NAV_GROUPS:
            errors.append(
                f"test scene nav_group must be one of {sorted(guard.TEST_NAV_GROUPS)}: {scene_key} (nav_group={nav})"
            )
        return errors

    def test_r2_test_scene_violates(self) -> None:
        v = self._violations_for("scene_smoke_default", "R2", "smart_construction_scene", "others")
        self.assertTrue(any("must stay at R0/R1" in x for x in v))

    def test_r3_test_scene_violates(self) -> None:
        v = self._violations_for("scene_smoke_default", "R3", "smart_construction_scene", "others")
        self.assertTrue(any("must stay at R0/R1" in x for x in v))

    def test_business_owner_violates(self) -> None:
        v = self._violations_for("scene_smoke_default", "R1", "smart_construction_core", "others")
        self.assertTrue(any("owner_module must be a test layer" in x for x in v))

    def test_business_nav_group_violates(self) -> None:
        v = self._violations_for("scene_smoke_default", "R1", "smart_construction_scene", "project_management")
        self.assertTrue(any("nav_group must be one of" in x for x in v))

    def test_missing_owner_violates(self) -> None:
        v = self._violations_for("scene_smoke_default", "R1", "", "others")
        self.assertTrue(any("missing owner_module" in x for x in v))

    def test_compliant_test_scene_has_no_violations(self) -> None:
        v = self._violations_for("scene_smoke_default", "R1", "smart_construction_scene", "others")
        self.assertEqual(v, [])


if __name__ == "__main__":
    unittest.main()
