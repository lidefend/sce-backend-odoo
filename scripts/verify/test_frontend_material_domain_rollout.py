import importlib.util
import unittest
from pathlib import Path
from unittest.mock import ANY, patch

import yaml


ROOT = Path(__file__).resolve().parents[2]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runtime = load_module(
    "frontend_material_domain_rollout",
    ROOT / "scripts/verify/frontend_material_domain_rollout.py",
)
reporter = load_module(
    "frontend_material_domain_rollout_report",
    ROOT / "scripts/verify/frontend_material_domain_rollout_report.py",
)


class TestFrontendMaterialDomainRollout(unittest.TestCase):
    def test_workflow_advances_from_material_to_quality_safety(self):
        workflow = yaml.safe_load(
            (ROOT / ".agent/workflows/frontend-professionalization.yaml").read_text(
                encoding="utf-8"
            )
        )["workflow"]
        phase_10 = workflow["phases"]["phase_10"]
        self.assertIn("material", phase_10["delivered"])
        self.assertEqual(phase_10["active_domain"], "quality_safety")
        self.assertEqual(
            workflow["next_action"]["task"], "quality_safety_domain_rollout"
        )

    def test_browser_verifier_requires_task_and_terminal_record_downgrade(self):
        source = (ROOT / "scripts/verify/frontend_material_domain_browser.mjs").read_text(
            encoding="utf-8"
        )
        self.assertIn("presentationMode') === 'task'", source)
        self.assertIn("findKey(listContract, 'modelRights')?.write === true", source)
        self.assertIn("effectiveRecordCapabilities')?.write === false", source)
        self.assertIn("effectiveRenderProfile') === 'readonly'", source)
        self.assertIn("businessNavigationSequence[0]", source)
        self.assertIn("passed through a readonly business route", source)

    def test_material_domain_uses_only_current_formal_direct_entries(self):
        self.assertEqual(runtime.DOMAIN_KEY, "material")
        self.assertEqual(
            runtime.ROOT_MENU_XMLIDS,
            (
                "smart_construction_core.menu_sc_material_inbound",
                "smart_construction_core.menu_sc_material_outbound",
                "smart_construction_core.menu_sc_product_material_return_v1",
            ),
        )
        self.assertNotIn(
            "smart_construction_core.menu_sc_material_center", runtime.ROOT_MENU_XMLIDS
        )
        self.assertNotIn(
            "smart_construction_core.menu_sc_material_management_group",
            runtime.ROOT_MENU_XMLIDS,
        )
        self.assertEqual(runtime.OWNER_MODULE, "smart_construction_core")
        self.assertEqual(
            runtime.EXPECTED_ANCHORS,
            {
                "smart_construction_core.action_sc_material_inbound_handling",
                "smart_construction_core.action_sc_material_outbound",
                "smart_construction_core.action_sc_material_supplier_return",
            },
        )

    def test_collect_delegates_exact_multi_root_identity(self):
        expected = {"status": "PASS", "gaps": []}
        with patch.object(runtime, "collect_domain", return_value=expected) as collector:
            self.assertIs(runtime.collect(object()), expected)
        collector.assert_called_once_with(
            ANY,
            domain_key="material",
            root_menu_xmlids=runtime.ROOT_MENU_XMLIDS,
            owner_module=runtime.OWNER_MODULE,
            expected_anchors=runtime.EXPECTED_ANCHORS,
        )

    def test_reporter_emits_material_title_without_database_identity(self):
        payload = {
            "schemaVersion": "frontend_domain_rollout.v1",
            "status": "PASS",
            "domain": "material",
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
        rendered = reporter.markdown(snapshot, "Material Domain Frontend Rollout v1")
        self.assertIn("# Material Domain Frontend Rollout v1", rendered)
        self.assertIn("formal material-center entries", rendered)


if __name__ == "__main__":
    unittest.main()
