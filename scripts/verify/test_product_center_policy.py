from __future__ import annotations

import importlib.util
import unittest
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


CENTER = _load(
    "scene_close_01_product_center_policy",
    "addons/smart_core/delivery/product_center_policy.py",
)
SOURCE = _load(
    "scene_close_01_product_menu_source",
    "addons/smart_construction_core/services/product_menu_source.py",
)


def legacy_resolver(group, index):
    center = SOURCE.center_identity(group.get("group_key")) or SOURCE.center_identity(
        group.get("group_label")
    )
    if not center:
        return None
    return {
        "stable_key": center["stable_key"],
        "key": center["key"],
        "name": center["name"],
        "sequence": center.get("sequence") or (index + 1) * 10,
    }


def legacy_policy():
    return {
        "product_key": "construction.test",
        "menu_groups": [
            {
                "group_key": "construction.项目中心",
                "group_label": "项目中心",
                "menus": [
                    {
                        "menu_xmlid": "smart_construction_core.menu_project",
                        "label": "项目台账",
                    }
                ],
            },
            {
                "group_key": "construction.合同中心",
                "group_label": "合同中心",
                "menus": [
                    {
                        "menu_xmlid": "smart_construction_core.menu_contract",
                        "label": "合同台账",
                    }
                ],
            },
        ],
        "capabilities": [
            {
                "menu_xmlid": "smart_construction_core.menu_project",
                "label": "项目台账",
            }
        ],
    }


class ProductCenterPolicyTest(unittest.TestCase):
    def test_legacy_name_keys_map_once_to_stable_identity(self):
        normalized = CENTER.normalize_product_policy(
            legacy_policy(),
            legacy_center_resolver=legacy_resolver,
        )
        self.assertEqual(
            [row["center_key"] for row in normalized["menu_groups"]],
            [
                "construction.center.project",
                "construction.center.contract",
            ],
        )
        self.assertEqual(
            normalized["menu_groups"][0]["menus"][0]["center_key"],
            "construction.center.project",
        )
        self.assertEqual(
            normalized["capabilities"][0]["center_key"],
            "construction.center.project",
        )

    def test_rename_does_not_change_center_identity(self):
        policy = legacy_policy()
        policy["menu_groups"][0].update(
            center_key="construction.center.project",
            group_key="construction.center.project",
        )
        policy["menu_groups"][1].update(
            center_key="construction.center.contract",
            group_key="construction.center.contract",
        )
        updated = CENTER.apply_product_center_updates(
            policy,
            center_updates=[
                {
                    "center_key": "construction.center.project",
                    "label": "项目交付",
                    "sequence": 5,
                }
            ],
        )
        center = next(
            row
            for row in updated["menu_groups"]
            if row["center_key"] == "construction.center.project"
        )
        self.assertEqual(center["group_label"], "项目交付")
        self.assertEqual(center["sequence"], 5)
        self.assertEqual(
            center["menus"][0]["center_key"],
            "construction.center.project",
        )

    def test_declared_zero_sequence_survives_update_and_renormalization(self):
        policy = legacy_policy()
        for index, key in enumerate(
            ["construction.center.project", "construction.center.contract"]
        ):
            policy["menu_groups"][index].update(center_key=key, group_key=key)
        updated = CENTER.apply_product_center_updates(
            policy,
            center_updates=[
                {
                    "center_key": "construction.center.contract",
                    "label": "合同中心",
                    "sequence": 0,
                }
            ],
        )
        contract = next(
            row
            for row in updated["menu_groups"]
            if row["center_key"] == "construction.center.contract"
        )
        self.assertEqual(contract["sequence"], 0)
        self.assertEqual(contract["menus"][0]["group_sequence"], 0)

    def test_entry_placement_moves_complete_entry_without_losing_fields(self):
        policy = legacy_policy()
        for index, key in enumerate(
            ["construction.center.project", "construction.center.contract"]
        ):
            policy["menu_groups"][index].update(center_key=key, group_key=key)
        updated = CENTER.apply_product_center_updates(
            policy,
            entry_placements=[
                {
                    "menu_xmlid": "smart_construction_core.menu_project",
                    "center_key": "construction.center.contract",
                }
            ],
        )
        contract = next(
            row
            for row in updated["menu_groups"]
            if row["center_key"] == "construction.center.contract"
        )
        moved = next(
            row
            for row in contract["menus"]
            if row["menu_xmlid"] == "smart_construction_core.menu_project"
        )
        self.assertEqual(moved["label"], "项目台账")
        self.assertEqual(moved["center_key"], "construction.center.contract")

    def test_same_key_with_different_definition_fails_closed(self):
        policy = legacy_policy()
        policy["menu_groups"][0]["center_key"] = "construction.center.project"
        policy["menu_groups"][1]["center_key"] = "construction.center.project"
        policy["menu_groups"][1]["sequence"] = 99
        with self.assertRaisesRegex(
            CENTER.ProductCenterPolicyError,
            "PRODUCT_CENTER_DEFINITION_CONFLICT",
        ):
            CENTER.normalize_product_policy(policy)

    def test_duplicate_menu_across_centers_fails_closed(self):
        policy = legacy_policy()
        policy["menu_groups"][1]["menus"][0]["menu_xmlid"] = (
            "smart_construction_core.menu_project"
        )
        with self.assertRaisesRegex(
            CENTER.ProductCenterPolicyError,
            "PRODUCT_CENTER_ENTRY_CONFLICT",
        ):
            CENTER.normalize_product_policy(
                policy,
                legacy_center_resolver=legacy_resolver,
            )

    def test_seed_projection_uses_stable_keys_and_locked_default_order(self):
        contract, publication = SOURCE.project(SOURCE.load_source())
        centers = contract["centers"]
        self.assertEqual(
            [row["center_key"] for row in centers],
            [
                "workspace.home.workbench",
                "construction.center.project",
                "construction.center.contract",
                "construction.center.cost",
                "construction.center.finance",
                "construction.center.tax",
                "construction.center.accounting",
                "construction.center.reporting",
                "construction.center.administration",
                "construction.center.product_configuration",
            ],
        )
        standard = next(
            row
            for row in publication["products"]
            if row["product_key"] == "construction.standard"
        )
        self.assertEqual(
            [row["group_key"] for row in standard["menu_groups"]],
            [row["center_key"] for row in centers],
        )
        self.assertTrue(
            all(
                group["group_key"] == group["center_key"]
                for group in standard["menu_groups"]
            )
        )


if __name__ == "__main__":
    unittest.main()
