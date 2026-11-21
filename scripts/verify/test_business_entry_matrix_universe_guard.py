from __future__ import annotations

import json
import unittest

from scripts.verify import business_entry_matrix_universe_guard as guard


def _row(menu, action="smart_construction_core.action_demo", status="pending"):
    return {
        "menu_xmlid": menu,
        "label": menu,
        "domain": "demo",
        "model": "demo.model",
        "scope_disposition": "本轮验收",
        "batch": "F4",
        "role_authority": json.dumps({
            "semantics": "all_restricted_layers_must_match_one_group",
            "menu_chain": [{"menu_xmlid": "smart_construction_core.menu_sc_root", "groups": []}],
            "action_groups": ["base.group_user"],
        }),
        "action_xmlid": action,
        "rendering_path": "tree:table [ready]; form:form_structure [structural]",
        "query_responsibility": "list/detail",
        "write_responsibility": "pending",
        "acceptance_status": status,
        "evidence": "",
        "gap": "",
    }


class BusinessEntryAcceptanceUniverseGuardTest(unittest.TestCase):
    def _documents(self, count=132):
        menu_keys = [f"demo.menu_{index:03d}" for index in range(count - 1)]
        scenario = {
            "scenarios": [{
                "key": "demo",
                "pages": [{"menu_xmlid": menu} for menu in menu_keys] + [
                    {"menu_xmlid": "demo.scene_home"}
                ],
            }],
        }
        matrix = [_row(menu) for menu in menu_keys]
        exposure = {
            "non_action_delivery_entries": {
                "demo.scene_home": {
                    "scene_key": "workspace.home",
                    "route": "/s/workspace.home",
                    "entry_target_type": "scene",
                },
            },
        }
        policy = {
            "policy_strategy": {
                "effective_menu_count_per_product": 132,
                "menu_count_by_product": {"construction.standard": 132},
            },
        }
        return scenario, matrix, exposure, policy

    def test_current_documents_are_complete(self):
        report = guard.build_report()
        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(report["counts"]["scenario_pages"], 132)
        self.assertEqual(report["counts"]["matrix_action_rows"], 131)
        self.assertEqual(report["counts"]["scene_rows"], 1)
        self.assertEqual(report["counts"]["declared_units"], 132)
        self.assertEqual(report["counts"]["fixture_scenarios"], 46)

    def test_complete_fixture_is_accepted(self):
        scenario, matrix, exposure, policy = self._documents()
        report = guard.validate_documents(
            scenario,
            matrix,
            exposure,
            policy,
            fixture_scenarios=[row["key"] for row in scenario["scenarios"]],
        )
        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(report["counts"]["declared_units"], 132)

    def test_missing_action_row_fails_closed(self):
        scenario, matrix, exposure, policy = self._documents()
        report = guard.validate_documents(
            scenario,
            matrix[:-1],
            exposure,
            policy,
            fixture_scenarios=[row["key"] for row in scenario["scenarios"]],
        )
        self.assertFalse(report["ok"])
        self.assertIn("matrix action rows=130 expected=131", report["errors"])
        self.assertEqual(report["missing"], ["demo.menu_130"])

    def test_duplicate_or_actionless_row_fails_closed(self):
        scenario, matrix, exposure, policy = self._documents()
        duplicate = list(matrix)
        duplicate.append(dict(matrix[0]))
        report = guard.validate_documents(
            scenario,
            duplicate,
            exposure,
            policy,
            fixture_scenarios=[row["key"] for row in scenario["scenarios"]],
        )
        self.assertFalse(report["ok"])
        self.assertIn("duplicate matrix action row: demo.menu_000", report["errors"])

        actionless = list(matrix)
        actionless[0] = {**actionless[0], "action_xmlid": ""}
        report = guard.validate_documents(
            scenario,
            actionless,
            exposure,
            policy,
            fixture_scenarios=[row["key"] for row in scenario["scenarios"]],
        )
        self.assertFalse(report["ok"])
        self.assertIn("demo.menu_000: empty action_xmlid", report["errors"])

    def test_fixture_scenario_drift_fails_closed(self):
        scenario, matrix, exposure, policy = self._documents()
        report = guard.validate_documents(
            scenario,
            matrix,
            exposure,
            policy,
            fixture_scenarios=[],
        )
        self.assertFalse(report["ok"])
        self.assertIn(
            "acceptance fixture scenario keys drift missing=['demo'] extra=[]",
            report["errors"],
        )


if __name__ == "__main__":
    unittest.main()
