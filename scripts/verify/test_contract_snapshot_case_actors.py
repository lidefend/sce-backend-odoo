#!/usr/bin/env python3

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CASES = (ROOT / "docs" / "contract" / "cases.yml").read_text(encoding="utf-8")
PARSED_CASES = json.loads(CASES)

PRIVILEGED_INTENTS = {
    "api.onchange",
    "chatter.activity.schedule",
    "chatter.activity.update",
    "chatter.post",
    "execute_button",
    "file.upload",
    "global.message.read",
    "global.message.send",
    "payment.request.submit",
    "risk.action.execute",
    "scene.governance.export_contract",
    "scene.governance.pin_stable",
    "scene.governance.rollback",
    "scene.governance.set_channel",
    "scene.package.dry_run_import",
    "scene.package.export",
    "scene.package.import",
    "scene.package.list",
    "scene.packages.installed",
    "system.ping.construction",
}


class SnapshotCaseActorsTest(unittest.TestCase):
    def test_pm_cases_use_governed_fixture_login(self):
        self.assertNotIn('"user": "pm"', CASES)
        self.assertIn('"user": "demo_role_pm"', CASES)

    def test_privileged_intents_use_full_ability_fixture(self):
        actors = {
            item.get("intent"): item.get("user")
            for item in PARSED_CASES
            if item.get("intent") in PRIVILEGED_INTENTS
        }
        self.assertEqual(set(actors), PRIVILEGED_INTENTS)
        self.assertEqual(set(actors.values()), {"sc_test_admin"})

    def test_full_ability_fixture_declares_platform_authorities(self):
        fixture = (
            ROOT
            / "demo_addons"
            / "smart_construction_demo"
            / "data"
            / "scenario"
            / "s90_users_roles"
            / "10_users.xml"
        ).read_text(encoding="utf-8")
        self.assertIn("smart_core.group_smart_core_finance_approver", fixture)
        self.assertIn("smart_core.group_smart_core_scene_admin", fixture)


if __name__ == "__main__":
    unittest.main()
