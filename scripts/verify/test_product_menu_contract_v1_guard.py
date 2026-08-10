from __future__ import annotations

import copy
import unittest

from scripts.verify.product_menu_contract_v1_guard import BASELINE_PATH, CONTRACT_PATH, load_json, validate


class ProductMenuContractGuardTest(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load_json(CONTRACT_PATH)
        self.baseline = load_json(BASELINE_PATH)

    def test_repository_contract_passes(self) -> None:
        self.assertEqual(validate(self.contract, self.baseline), [])

    def test_non_project_third_level_fails(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["centers"][2]["level_two"][0]["children"] = [{"name": "不允许", "delivery": "RELEASED_FOUNDATION"}]
        self.assertTrue(validate(contract, self.baseline))

    def test_project_missing_third_level_fails(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["centers"][1]["level_two"][0].pop("children")
        self.assertTrue(validate(contract, self.baseline))

    def test_contract_daily_names_are_locked(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["centers"][2]["level_two"][3]["name"] = "通用合同"
        self.assertTrue(validate(contract, self.baseline))


if __name__ == "__main__":
    unittest.main()
