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
    "frontend_contract_domain_rollout",
    ROOT / "scripts/verify/frontend_contract_domain_rollout.py",
)
reporter = load_module(
    "frontend_contract_domain_rollout_report",
    ROOT / "scripts/verify/frontend_contract_domain_rollout_report.py",
)


class TestFrontendContractDomainRollout(unittest.TestCase):
    def test_contract_domain_uses_formal_runtime_authority(self):
        self.assertEqual(runtime.DOMAIN_KEY, "contract")
        self.assertEqual(
            runtime.ROOT_MENU_XMLID,
            "smart_construction_core.menu_sc_contract_center",
        )
        self.assertEqual(runtime.OWNER_MODULE, "smart_construction_core")
        self.assertIn(
            "smart_construction_core.action_construction_contract_income",
            runtime.EXPECTED_ANCHORS,
        )
        self.assertEqual(len(runtime.EXPECTED_ANCHORS), 7)

    def test_shared_runtime_has_governed_container_mount_fallback(self):
        source = (ROOT / "scripts/verify/frontend_contract_domain_rollout.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("/mnt/scripts/verify/frontend_project_domain_rollout.py", source)
        self.assertNotIn("sys.path", source)
        reporter_source = (
            ROOT / "scripts/verify/frontend_contract_domain_rollout_report.py"
        ).read_text(encoding="utf-8")
        self.assertIn('with_name("frontend_project_domain_rollout_report.py")', reporter_source)
        self.assertNotIn("sys.path", reporter_source)

    def test_collect_delegates_exact_domain_identity(self):
        expected = {"status": "PASS", "gaps": []}
        with patch.object(runtime, "collect_domain", return_value=expected) as collector:
            self.assertIs(runtime.collect(object()), expected)
        collector.assert_called_once_with(
            ANY,
            domain_key="contract",
            root_menu_xmlid=runtime.ROOT_MENU_XMLID,
            owner_module=runtime.OWNER_MODULE,
            expected_anchors=runtime.EXPECTED_ANCHORS,
        )

    def test_reporter_emits_contract_title_and_no_database_identity(self):
        payload = {
            "schemaVersion": "frontend_domain_rollout.v1",
            "status": "PASS",
            "domain": "contract",
            "database": "must-not-leak",
            "root_menu_xmlid": runtime.ROOT_MENU_XMLID,
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
        self.assertIn(
            "# Contract Domain Frontend Rollout v1",
            reporter.markdown(snapshot, "Contract Domain Frontend Rollout v1"),
        )


if __name__ == "__main__":
    unittest.main()
