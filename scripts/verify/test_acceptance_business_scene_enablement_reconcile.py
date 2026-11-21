from __future__ import annotations

import unittest

from scripts.ops import acceptance_business_scene_enablement_reconcile as reconcile


DESIRED = ("work.my_queue", "project.initiation", "project.team")
LEGACY = ("project.management", "quality.management")


class AcceptanceBusinessSceneEnablementReconcileTest(unittest.TestCase):
    def test_legacy_enablements_are_preserved_and_current_scenarios_created(self):
        rows = [
            {"company_id": 2, "scene_key": "business.v1:project.management", "enabled": True},
            {"company_id": 2, "scene_key": "business.v1:quality.management", "enabled": True},
            {"company_id": 3, "scene_key": "business.v1:project.management", "enabled": True},
            {"company_id": 3, "scene_key": "business.v1:quality.management", "enabled": True},
        ]
        plan = reconcile.build_plan(
            company_ids=[2, 3],
            desired_keys=DESIRED,
            legacy_keys=LEGACY,
            rows=rows,
            released_by_key={key: True for key in DESIRED},
        )
        self.assertTrue(plan["ok"], plan["errors"])
        self.assertEqual(plan["planned_writes"], 6)
        self.assertEqual(plan["expected_enabled_per_company"], 5)
        for company in plan["companies"]:
            self.assertEqual(company["create_and_enable"], sorted(DESIRED))
            self.assertEqual(company["preserved_legacy"], sorted(LEGACY))

    def test_reconciled_state_is_idempotent(self):
        rows = []
        for company_id in (2, 3):
            rows.extend(
                {"company_id": company_id, "scene_key": f"business.v1:{key}", "enabled": True}
                for key in DESIRED
            )
            rows.extend(
                {"company_id": company_id, "scene_key": f"business.v1:{key}", "enabled": True}
                for key in LEGACY
            )
        plan = reconcile.build_plan(
            company_ids=[2, 3],
            desired_keys=DESIRED,
            legacy_keys=LEGACY,
            rows=rows,
            released_by_key={key: True for key in DESIRED},
        )
        self.assertTrue(plan["ok"], plan["errors"])
        self.assertEqual(plan["planned_writes"], 0)
        self.assertEqual(plan["expected_enabled_total"], 10)

    def test_unknown_enabled_key_fails_closed(self):
        rows = [
            {"company_id": 2, "scene_key": "business.v1:unknown", "enabled": True},
            {"company_id": 3, "scene_key": "business.v1:unknown", "enabled": True},
        ]
        plan = reconcile.build_plan(
            company_ids=[2, 3],
            desired_keys=DESIRED,
            legacy_keys=LEGACY,
            rows=rows,
            released_by_key={key: True for key in DESIRED},
        )
        self.assertFalse(plan["ok"])
        self.assertTrue(any("outside the authorized scope" in error for error in plan["errors"]))

    def test_unreleased_desired_scenario_fails_closed(self):
        plan = reconcile.build_plan(
            company_ids=[2, 3],
            desired_keys=DESIRED,
            legacy_keys=LEGACY,
            rows=[],
            released_by_key={**{key: True for key in DESIRED}, "project.team": False},
        )
        self.assertFalse(plan["ok"])
        self.assertIn("desired scenario is not product-released: project.team", plan["errors"])


if __name__ == "__main__":
    unittest.main()
