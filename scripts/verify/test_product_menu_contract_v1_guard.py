from __future__ import annotations

import copy
import unittest

from scripts.verify.product_menu_contract_v1_guard import BASELINE_PATH, CONTRACT_PATH, EVOLUTION_POLICY_PATH, load_json, validate


class ProductMenuContractGuardTest(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load_json(CONTRACT_PATH)
        self.baseline = load_json(BASELINE_PATH)
        self.evolution_policy = load_json(EVOLUTION_POLICY_PATH)

    def test_repository_contract_passes(self) -> None:
        self.assertEqual(validate(self.contract, self.baseline, self.evolution_policy), [])

    def test_non_project_third_level_fails(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["centers"][2]["level_two"][0]["children"] = [{"name": "不允许", "delivery": "RELEASED_FOUNDATION"}]
        self.assertTrue(validate(contract, self.baseline, self.evolution_policy))

    def test_project_missing_third_level_fails(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["centers"][1]["level_two"][0].pop("children")
        self.assertTrue(validate(contract, self.baseline, self.evolution_policy))

    def test_contract_daily_names_are_locked(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["centers"][2]["level_two"][3]["name"] = "通用合同"
        self.assertTrue(validate(contract, self.baseline, self.evolution_policy))

    def test_seed_customer_cannot_become_primary_goal(self) -> None:
        policy = copy.deepcopy(self.evolution_policy)
        policy["primary_goal"] = "P2_SEED_CUSTOMER_DELIVERY"
        self.assertTrue(validate(self.contract, self.baseline, policy))


if __name__ == "__main__":
    unittest.main()
