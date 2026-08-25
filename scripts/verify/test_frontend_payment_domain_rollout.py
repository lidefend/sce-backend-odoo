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
    "frontend_payment_domain_rollout",
    ROOT / "scripts/verify/frontend_payment_domain_rollout.py",
)
reporter = load_module(
    "frontend_payment_domain_rollout_report",
    ROOT / "scripts/verify/frontend_payment_domain_rollout_report.py",
)


class TestFrontendPaymentDomainRollout(unittest.TestCase):
    def test_payment_domain_uses_current_formal_multi_root_authority(self):
        self.assertEqual(runtime.DOMAIN_KEY, "payment")
        self.assertEqual(
            runtime.ROOT_MENU_XMLIDS,
            (
                "smart_construction_core.menu_sc_user_payment_apply",
                "smart_construction_core.menu_sc_payment_execution",
            ),
        )
        self.assertNotIn("smart_construction_core.menu_sc_finance_center", runtime.ROOT_MENU_XMLIDS)
        self.assertEqual(runtime.OWNER_MODULE, "smart_construction_core")
        self.assertEqual(
            runtime.EXPECTED_ANCHORS,
            {
                "smart_construction_core.action_payment_request_user_payment_apply",
                "smart_construction_core.action_sc_payment_execution_actual_outflow",
            },
        )

    def test_collect_delegates_exact_multi_root_identity(self):
        expected = {"status": "PASS", "gaps": []}
        with patch.object(runtime, "collect_domain", return_value=expected) as collector:
            self.assertIs(runtime.collect(object()), expected)
        collector.assert_called_once_with(
            ANY,
            domain_key="payment",
            root_menu_xmlids=runtime.ROOT_MENU_XMLIDS,
            owner_module=runtime.OWNER_MODULE,
            expected_anchors=runtime.EXPECTED_ANCHORS,
        )

    def test_reporter_emits_payment_title_without_database_identity(self):
        payload = {
            "schemaVersion": "frontend_domain_rollout.v1",
            "status": "PASS",
            "domain": "payment",
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
        self.assertEqual(snapshot["rootMenuXmlids"], list(runtime.ROOT_MENU_XMLIDS))
        rendered = reporter.markdown(snapshot, "Payment Domain Frontend Rollout v1")
        self.assertIn("# Payment Domain Frontend Rollout v1", rendered)
        self.assertIn("formal payment-center entries", rendered)


if __name__ == "__main__":
    unittest.main()
