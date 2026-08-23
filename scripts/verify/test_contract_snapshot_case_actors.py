#!/usr/bin/env python3

import json
import unittest
import xml.etree.ElementTree as ET
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

FINANCE_ACTION_ACTORS = {
    "smart_construction_core.action_payment_request": "demo_role_finance",
    "smart_construction_core.action_sc_operating_drill_overpay_risk_pr": "demo_role_finance",
}

FINANCE_ACTION_CASES = {
    "smart_construction_core.action_payment_request": "payment_request_action_finance",
    "smart_construction_core.action_sc_operating_drill_overpay_risk_pr": (
        "operating_risk_drill_action_finance"
    ),
}

ROLE_FIXTURE = (
    ROOT
    / "demo_addons"
    / "smart_construction_demo"
    / "data"
    / "demo"
    / "role_matrix_demo_users.xml"
)


def _fixture_groups(record_id: str) -> str:
    root = ET.parse(ROLE_FIXTURE).getroot()
    records = root.findall(f".//record[@id='{record_id}']")
    if len(records) != 1:
        raise AssertionError(f"expected one fixture record {record_id}, got {len(records)}")
    fields = records[0].findall("field[@name='groups_id']")
    if len(fields) != 1:
        raise AssertionError(f"expected one groups_id field for {record_id}, got {len(fields)}")
    return fields[0].attrib.get("eval", "")


class SnapshotCaseActorsTest(unittest.TestCase):
    def test_pm_cases_use_governed_fixture_login(self):
        self.assertNotIn('"user": "pm"', CASES)
        self.assertIn('"user": "demo_role_pm"', CASES)
        pm_cases = [
            item
            for item in PARSED_CASES
            if item.get("op") == "action_open"
            and str(item.get("case") or "").endswith("_pm")
        ]
        self.assertTrue(pm_cases)
        self.assertEqual({item.get("user") for item in pm_cases}, {"demo_role_pm"})

    def test_finance_actions_use_governed_finance_fixture(self):
        finance_rows = [
            item
            for item in PARSED_CASES
            if item.get("action_xmlid") in FINANCE_ACTION_ACTORS
        ]
        self.assertEqual(len(finance_rows), len(FINANCE_ACTION_ACTORS))
        actors = {
            item.get("action_xmlid"): item.get("user")
            for item in finance_rows
        }
        self.assertEqual(actors, FINANCE_ACTION_ACTORS)

        cases = {
            item.get("action_xmlid"): item.get("case")
            for item in finance_rows
        }
        self.assertEqual(
            cases,
            FINANCE_ACTION_CASES,
        )

    def test_finance_action_snapshots_bind_the_same_actor_and_case(self):
        for case_name in FINANCE_ACTION_CASES.values():
            with self.subTest(case=case_name):
                snapshot = json.loads(
                    (ROOT / "docs" / "contract" / "snapshots" / f"{case_name}.json").read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(snapshot.get("case"), case_name)
                self.assertEqual(snapshot.get("user"), "demo_role_finance")
                self.assertIsNone(snapshot.get("error"))
                self.assertIsNone(snapshot.get("record_error"))
                self.assertEqual(snapshot.get("snapshot_schema_version"), "1.0.0")

    def test_role_fixtures_preserve_pm_finance_separation(self):
        pm_groups = _fixture_groups("user_demo_role_pm")
        finance_groups = _fixture_groups("user_demo_role_finance")
        self.assertIn("smart_construction_core.group_sc_role_project_manager", pm_groups)
        self.assertNotIn("group_sc_role_finance", pm_groups)
        self.assertIn("smart_construction_core.group_sc_role_finance_manager", finance_groups)

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
