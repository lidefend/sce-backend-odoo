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
    def test_workflow_records_completed_material_domain(self):
        workflow = yaml.safe_load(
            (ROOT / ".agent/workflows/frontend-professionalization.yaml").read_text(
                encoding="utf-8"
            )
        )["workflow"]
        phase_10 = workflow["phases"]["phase_10"]
        self.assertIn("material", phase_10["delivered"])
        self.assertEqual(phase_10["active_domain"], "none")
        self.assertEqual(
            workflow["next_action"]["task"],
            "hand_off_completed_systemwide_frontend_product",
        )

    def test_browser_verifier_requires_task_and_terminal_record_downgrade(self):
        source = (ROOT / "scripts/verify/frontend_material_domain_browser.mjs").read_text(
            encoding="utf-8"
        )
        self.assertIn("presentationMode') === 'task'", source)
        self.assertIn("material-inbound-terminal-readonly-top.png", source)
        self.assertIn("material-inbound-terminal-readonly-detail.png", source)
        self.assertIn("material-inbound-terminal-readonly-bottom.png", source)
        self.assertIn("material-inbound-create-top.png", source)
        self.assertIn("missingCreateFacts.length === 0", source)
        self.assertIn("readonlyCreateFacts.length === 0", source)
        self.assertIn("factsAfterDetail.length === 0", source)
        self.assertIn("hasRowChangeColumn", source)
        self.assertIn("hasTechnicalRelationLabel", source)
        self.assertIn("material create form has no reachable detail entry", source)
        self.assertIn("FRONTEND_MATERIAL_SAMPLE_REVIEW", source)
        self.assertIn("FRONTEND_MATERIAL_SAMPLE_VIEWPORTS", source)
        self.assertIn("FRONTEND_MATERIAL_EVIDENCE_CAPTURE", source)
        self.assertIn("CANDIDATE_WORKTREE_FINGERPRINT", source)
        self.assertIn("screenshotEvidence()", source)
        self.assertIn("createHash('sha256')", source)
        self.assertIn("inbound_sample_affected_regions", source)
        self.assertIn("const handlingEntrySpecs", source)
        self.assertNotIn("return: {", source)
        self.assertNotIn("supplier_return: {", source)
        self.assertIn("target.formal_return_path", source)
        self.assertIn("product_decision_required", source)
        self.assertIn("informationOrganization.headerStatusbars === 1", source)
        self.assertIn("material inbound status, quantity, or amount has more than one visible owner", source)
        self.assertIn("no_formal_menu_or_authorized_category_path", (
            ROOT / "scripts/verify/local_dev_material_domain_ids.py"
        ).read_text(encoding="utf-8"))
        self.assertIn("draftNoteRetention", source)
        self.assertIn("top navigation did not reveal, locate, and highlight", source)
        self.assertIn("inspectNonMaterialNavigationCounterexample", source)
        self.assertIn("FRONTEND_MATERIAL_HANDLING_ENTRIES", source)
        self.assertIn("FRONTEND_MATERIAL_HANDLING_SKIP_COUNTEREXAMPLE", source)
        self.assertIn("uc2-material-", source)
        self.assertIn("readonly source name is not fully accessible", source)
        self.assertIn("header-owned status remains duplicated", source)
        self.assertIn("material inbound still depends on compatibility structure", source)
        self.assertIn("resolvedViewId === 1428", source)
        self.assertIn("readonly and create chapters do not share one native source authority", source)
        self.assertIn("material inbound load-acceptance operation is missing from the native contract", source)
        self.assertIn("createBodyStatusFields + createHeaderStatusbars === 1", source)
        self.assertIn("material inbound source field is missing", source)
        self.assertIn("readonly sample exposes no populated source trace fact", source)
        self.assertIn("getByText('S80-MA-001', { exact: false }).filter({ visible: true })", source)
        self.assertIn("['入库明细', '说明与附件', '来源追溯']", source)
        self.assertIn("inbound_evidence_capture_only", source)
        self.assertIn("resetActualScrollTop", source)
        self.assertIn("routerHost.scrollTop = 0", source)
        self.assertIn("fullPage: false", source)
        self.assertIn("navigationBehavior", source)
        self.assertIn("capture_only_reuses_prior_business_acceptance", source)
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
