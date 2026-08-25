import importlib.util
import unittest
from pathlib import Path
from unittest.mock import ANY, patch


ROOT = Path(__file__).resolve().parents[2]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runtime = load_module(
    "frontend_settlement_domain_rollout",
    ROOT / "scripts/verify/frontend_settlement_domain_rollout.py",
)
reporter = load_module(
    "frontend_settlement_domain_rollout_report",
    ROOT / "scripts/verify/frontend_settlement_domain_rollout_report.py",
)


class TestFrontendSettlementDomainRollout(unittest.TestCase):
    def test_browser_verifier_requires_task_and_first_business_route_edit(self):
        source = (ROOT / "scripts/verify/frontend_settlement_domain_browser.mjs").read_text(
            encoding="utf-8"
        )
        self.assertIn("presentationMode') === 'task'", source)
        self.assertIn("businessNavigationSequence[0]", source)
        self.assertIn("passed through a readonly business route", source)

    def test_hierarchical_worksheet_exposes_accessible_record_open(self):
        source = (
            ROOT
            / "frontend/apps/web/src/components/action/HierarchicalWorksheet.vue"
        ).read_text(encoding="utf-8")
        self.assertIn('data-semantic-action="record.open"', source)
        self.assertIn('@keyup="openRecordFromKeyboard($event, entry.record)"', source)
        self.assertIn("shouldOpenWorksheetRecordFromKeyboard", source)

    def test_settlement_domain_uses_formal_center_authority(self):
        self.assertEqual(runtime.DOMAIN_KEY, "settlement")
        self.assertEqual(
            runtime.ROOT_MENU_XMLIDS,
            (
                "smart_construction_core.menu_sc_p1_income_settlement",
                "smart_construction_core.menu_sc_p1_expense_settlement",
            ),
        )
        self.assertEqual(runtime.OWNER_MODULE, "smart_construction_core")
        self.assertEqual(
            runtime.EXPECTED_ANCHORS,
            {
                "smart_construction_core.action_sc_settlement_order_income",
                "smart_construction_core.action_sc_settlement_order_expense",
            },
        )

    def test_collect_delegates_exact_settlement_identity(self):
        expected = {"status": "PASS", "gaps": []}
        with patch.object(runtime, "collect_domain", return_value=expected) as collector:
            self.assertIs(runtime.collect(object()), expected)
        collector.assert_called_once_with(
            ANY,
            domain_key="settlement",
            root_menu_xmlids=runtime.ROOT_MENU_XMLIDS,
            owner_module=runtime.OWNER_MODULE,
            expected_anchors=runtime.EXPECTED_ANCHORS,
        )

    def test_reporter_emits_settlement_title_without_database_identity(self):
        payload = {
            "schemaVersion": "frontend_domain_rollout.v1",
            "status": "PASS",
            "domain": "settlement",
            "database": "must-not-leak",
            "root_menu_xmlid": runtime.ROOT_MENU_XMLIDS[0],
            "root_menu_xmlids": list(runtime.ROOT_MENU_XMLIDS),
            "owner_module": runtime.OWNER_MODULE,
            "summary": {
                "action_count": 0,
                "model_count": 0,
                "ready_surface_count": 0,
                "readable_fallback_count": 0,
                "structural_form_count": 0,
                "fail_closed_count": 0,
                "excluded_count": 0,
                "gap_count": 0,
            },
            "actions": [],
            "excluded": [],
            "gaps": [],
        }
        snapshot = reporter.normalized_snapshot(payload)
        self.assertNotIn("database", snapshot)
        rendered = reporter.markdown(snapshot, "Settlement Domain Frontend Rollout v1")
        self.assertIn("# Settlement Domain Frontend Rollout v1", rendered)
        self.assertIn("formal settlement-center entries", rendered)


if __name__ == "__main__":
    unittest.main()
