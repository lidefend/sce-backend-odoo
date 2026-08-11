from __future__ import annotations

import copy
import unittest

from scripts.verify.product_primary_center_baseline_guard import (
    BASELINE_PATH,
    RELEASE_MANIFEST_PATH,
    load_json,
    validate,
)


class ProductPrimaryCenterBaselineGuardTest(unittest.TestCase):
    def setUp(self) -> None:
        self.baseline = load_json(BASELINE_PATH)
        self.release_manifest = load_json(RELEASE_MANIFEST_PATH)

    def test_repository_contract_passes(self) -> None:
        self.assertEqual(validate(self.baseline, self.release_manifest), [])

    def test_center_order_drift_fails(self) -> None:
        baseline = copy.deepcopy(self.baseline)
        baseline["primary_centers"][0], baseline["primary_centers"][1] = (
            baseline["primary_centers"][1], baseline["primary_centers"][0]
        )
        self.assertTrue(validate(baseline, self.release_manifest))

    def test_missing_transition_fails(self) -> None:
        baseline = copy.deepcopy(self.baseline)
        baseline["legacy_center_transitions"].pop()
        self.assertTrue(validate(baseline, self.release_manifest))

    def test_release_manifest_reference_drift_fails(self) -> None:
        release_manifest = copy.deepcopy(self.release_manifest)
        release_manifest["target_primary_center_baseline"]["ref"] = "config/wrong.json"
        self.assertTrue(validate(self.baseline, release_manifest))

    def test_full_menu_contract_reference_drift_fails(self) -> None:
        baseline = copy.deepcopy(self.baseline)
        baseline["menu_contract"]["ref"] = "config/wrong.json"
        self.assertTrue(validate(baseline, self.release_manifest))

    def test_center_level_maturity_policy_fails_closed(self) -> None:
        baseline = copy.deepcopy(self.baseline)
        baseline["center_level_maturity_policy"] = "GA_OR_PILOT_BY_CENTER"
        self.assertTrue(validate(baseline, self.release_manifest))


if __name__ == "__main__":
    unittest.main()
