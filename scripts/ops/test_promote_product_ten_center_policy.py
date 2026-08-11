#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import unittest

from scripts.ops.promote_product_ten_center_policy import (
    ACCOUNTING_MENUS,
    BASELINE,
    REPLACED_NATIVE_ACCOUNTING_MENU_XMLIDS,
    TARGET_CENTERS,
    promote,
)


class ProductTenCenterPolicyPromotionTests(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads(BASELINE.read_text(encoding="utf-8"))

    def test_promotion_is_idempotent_and_preserves_unique_identity(self):
        first = promote(copy.deepcopy(self.payload))
        second = promote(copy.deepcopy(first))
        self.assertEqual(first, second)
        for product in second["products"]:
            self.assertEqual([group["group_label"] for group in product["menu_groups"]], list(TARGET_CENTERS))
            rows = [menu for group in product["menu_groups"] for menu in group["menus"]]
            xmlids = [row["menu_xmlid"] for row in rows]
            self.assertEqual(len(rows), 169)
            self.assertEqual(len(xmlids), len(set(xmlids)))

    def test_retired_centers_are_absent_and_accounting_is_real(self):
        promoted = promote(copy.deepcopy(self.payload))
        product = promoted["products"][0]
        groups = {group["group_label"]: group for group in product["menu_groups"]}
        self.assertFalse({"物资与分包", "施工管理", "组织行政", "配置中心"}.intersection(groups))
        expected = {definition[1] for definition in ACCOUNTING_MENUS}
        actual = {row["menu_xmlid"] for row in groups["会计账务中心"]["menus"]}
        self.assertEqual(actual, expected)
        self.assertFalse(actual.intersection(REPLACED_NATIVE_ACCOUNTING_MENU_XMLIDS))
        self.assertEqual(
            sum(xmlid.startswith("smart_construction_core.") for xmlid in actual),
            3,
        )
        self.assertTrue(all(row.get("action_xmlid") and row.get("res_model") for row in groups["会计账务中心"]["menus"]))

    def test_unapproved_first_level_center_fails_closed(self):
        payload = copy.deepcopy(self.payload)
        payload["products"][0]["menu_groups"][0]["group_label"] = "临时中心"
        with self.assertRaisesRegex(ValueError, "unapproved first-level"):
            promote(payload)


if __name__ == "__main__":
    unittest.main()
