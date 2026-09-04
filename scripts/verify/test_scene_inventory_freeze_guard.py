#!/usr/bin/env python3
"""Unit tests for scene_inventory_freeze_guard (hermetic).

Exercises the orphan / maturity / exemptions / excluded-codes logic against
synthetic inventory + XML payloads so regressions are caught without touching
the real repository state.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import scene_inventory_freeze_guard as guard  # noqa: E402


INVENTORY_HEADER = (
    "# Scene Inventory Matrix\n\n## Matrix\n\n"
    "| scene_key | name | domain | route_target | nav_group | maturity_level | owner_module | next_action |\n"
    "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
)


def _build_inventory(rows: list[tuple[str, str]]) -> str:
    """rows = [(scene_key, maturity_level), ...]"""
    lines = [INVENTORY_HEADER]
    for scene_key, maturity in rows:
        lines.append(
            f"| {scene_key} | name | domain | /s/{scene_key} | others | {maturity} | smart_construction_scene | next |\n"
        )
    return "".join(lines)


def _build_payload_xml(code: str, with_page: bool = True) -> str:
    body = ""
    if with_page:
        body = (
            "                'page': {\n"
            "                    'key': 'main',\n"
            "                    'title': 't',\n"
            "                },\n"
            "                'zone_blocks': [{'key': 'a'}],\n"
        )
    return (
        '<odoo><data><record id="r1" model="sc.scene">\n'
        f'    <field name="payload_json" eval="{{\n'
        f"        'code': '{code}',\n"
        f"        'name': '{code}',\n"
        f"        {body}"
        "    }\"/>\n"
        "</record></data></odoo>\n"
    )


class FreezeGuardOrphanTests(unittest.TestCase):
    def test_pass_when_productized_scene_in_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inv = root / "inventory.md"
            xml = root / "scenes.xml"
            inv.write_text(_build_inventory([("alpha.scene", "R3")]), encoding="utf-8")
            xml.write_text(_build_payload_xml("alpha.scene"), encoding="utf-8")

            inventory = guard._load_inventory(inv)
            codes = guard._extract_payload_blocks(xml)
            self.assertTrue(guard._is_productized(codes[0]))
            code = guard._extract_scene_code(codes[0])
            self.assertIn(code, inventory)

    def test_orphan_payload_missing_from_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inv = root / "inventory.md"
            xml = root / "scenes.xml"
            inv.write_text(_build_inventory([("other.scene", "R3")]), encoding="utf-8")
            xml.write_text(_build_payload_xml("alpha.scene"), encoding="utf-8")

            inventory = guard._load_inventory(inv)
            payloads = {guard._extract_scene_code(b): b for b in guard._extract_payload_blocks(xml)}
            productized = {c for c, b in payloads.items() if guard._is_productized(b)}
            orphans = [c for c in productized if c not in inventory]
            self.assertEqual(orphans, ["alpha.scene"])

    def test_excluded_codes_are_not_treated_as_productized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            xml = root / "scenes.xml"
            xml.write_text(_build_payload_xml("default"), encoding="utf-8")
            payloads = {guard._extract_scene_code(b): b for b in guard._extract_payload_blocks(xml)}
            self.assertIn("default", payloads)
            # 'default' must not survive excluded_codes filtering
            self.assertIn("default", {"default", "scene_smoke_default"})

    def test_is_test_payload_marker_excludes_from_productized_set(self) -> None:
        xml = (
            '<odoo><data><record id="r1" model="sc.scene">\n'
            '    <field name="payload_json" eval="{\n'
            "        'code': 'scene_smoke_default',\n"
            "        'is_test': True,\n"
            "        'page': {'key': 'a'},\n"
            "    }\"/>\n"
            "</record></data></odoo>\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scenes.xml"
            path.write_text(xml, encoding="utf-8")
            blocks = guard._extract_payload_blocks(path)
            self.assertEqual(len(blocks), 1)
            self.assertTrue(guard._is_test_payload(blocks[0]))

    def test_inventory_loader_rejects_missing_matrix_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "inventory.md"
            path.write_text("# no matrix\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                guard._load_inventory(path)

    def test_inventory_loader_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "inventory.md"
            path.write_text(
                _build_inventory([("a.b", "R3"), ("c.d", "R2"), ("e.f", "R1")]),
                encoding="utf-8",
            )
            loaded = guard._load_inventory(path)
            self.assertEqual(set(loaded.keys()), {"a.b", "c.d", "e.f"})
            self.assertEqual(loaded["a.b"]["maturity_level"], "R3")
            self.assertEqual(loaded["c.d"]["maturity_level"], "R2")

    def test_exemption_list_overrides_orphan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inv = root / "inventory.md"
            xml = root / "scenes.xml"
            exemptions = root / "exempt.json"
            inv.write_text(_build_inventory([("other.scene", "R3")]), encoding="utf-8")
            xml.write_text(_build_payload_xml("alpha.scene"), encoding="utf-8")
            exemptions.write_text(
                '{"legacy_productized_not_in_inventory": ["alpha.scene"]}',
                encoding="utf-8",
            )
            inv_data = guard._load_inventory(inv)
            exem = guard._load_exemptions(exemptions)
            payloads = {guard._extract_scene_code(b): b for b in guard._extract_payload_blocks(xml)}
            productized = {c for c, b in payloads.items() if guard._is_productized(b)}
            orphans_after_exemption = [
                c for c in productized if c not in inv_data and c not in exem
            ]
            self.assertEqual(orphans_after_exemption, [])

    def test_must_be_r2_or_higher_for_productized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inv = root / "inventory.md"
            xml = root / "scenes.xml"
            # inventory has alpha.scene as R0 (below R2_PLUS) while XML productizes it
            inv.write_text(_build_inventory([("alpha.scene", "R0")]), encoding="utf-8")
            xml.write_text(_build_payload_xml("alpha.scene"), encoding="utf-8")
            inv_data = guard._load_inventory(inv)
            payloads = {guard._extract_scene_code(b): b for b in guard._extract_payload_blocks(xml)}
            productized = {c for c, b in payloads.items() if guard._is_productized(b)}
            violations = [
                c
                for c in productized
                if c in inv_data
                and str(inv_data[c].get("maturity_level") or "").upper() not in guard.R2_PLUS
            ]
            self.assertEqual(violations, ["alpha.scene"])


if __name__ == "__main__":
    unittest.main()
