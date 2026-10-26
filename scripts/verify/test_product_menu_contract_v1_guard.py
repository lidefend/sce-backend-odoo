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

    def test_preview_requires_explicit_preview_state(self) -> None:
        for state in (None, "released", "draft"):
            contract = copy.deepcopy(self.contract)
            leaf = next(child for center in contract["centers"] for item in center["level_two"]
                        for child in (item.get("children") or [item]) if child.get("delivery") == "PREVIEW_FOUNDATION")
            leaf["release_state"] = state
            self.assertTrue(any("delivery/release_state mismatch" in error for error in validate(contract, self.baseline)))

    def test_released_cannot_silently_become_preview(self) -> None:
        contract = copy.deepcopy(self.contract)
        leaf = next(child for center in contract["centers"] for item in center["level_two"]
                    for child in (item.get("children") or [item]) if child.get("delivery") == "RELEASED_FOUNDATION")
        leaf["release_state"] = "preview"
        self.assertTrue(any("delivery/release_state mismatch" in error for error in validate(contract, self.baseline)))

    def test_project_missing_third_level_fails(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["centers"][1]["level_two"][0].pop("children")
        self.assertTrue(validate(contract, self.baseline, self.evolution_policy))

    def test_contract_daily_names_are_locked(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["centers"][2]["level_two"][3]["name"] = "通用合同"
        self.assertTrue(validate(contract, self.baseline, self.evolution_policy))

    def test_contract_preview_cannot_be_removed_replaced_or_promoted(self) -> None:
        for mutation in ("remove", "replace", "promote"):
            with self.subTest(mutation=mutation):
                contract = copy.deepcopy(self.contract)
                center = next(row for row in contract["centers"] if row["key"] == "contract")
                if mutation == "remove":
                    center["level_two"].pop()
                elif mutation == "replace":
                    center["level_two"][-1]["name"] = "未声明入口"
                else:
                    center["level_two"][-1].update(delivery="RELEASED_FOUNDATION", release_state="released")
                self.assertTrue(validate(contract, self.baseline, self.evolution_policy))

    def test_seed_customer_cannot_become_primary_goal(self) -> None:
        policy = copy.deepcopy(self.evolution_policy)
        policy["primary_goal"] = "P2_SEED_CUSTOMER_DELIVERY"
        self.assertTrue(validate(self.contract, self.baseline, policy))


if __name__ == "__main__":
    unittest.main()
