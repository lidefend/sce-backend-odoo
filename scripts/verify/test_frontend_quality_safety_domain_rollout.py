import importlib.util
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import ANY, patch


ROOT = Path(__file__).resolve().parents[2]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runtime = load_module(
    "frontend_quality_safety_domain_rollout",
    ROOT / "scripts/verify/frontend_quality_safety_domain_rollout.py",
)
reporter = load_module(
    "frontend_quality_safety_domain_rollout_report",
    ROOT / "scripts/verify/frontend_quality_safety_domain_rollout_report.py",
)


class TestFrontendQualitySafetyDomainRollout(unittest.TestCase):
    def test_task_contracts_are_bound_to_exact_action_and_view(self):
        tree = ET.parse(
            ROOT
            / "addons/smart_construction_core/data/quality_safety_form_productization_contract.xml"
        )
        records = tree.findall(".//record[@model='ui.business.config.contract']")
        self.assertEqual(len(records), 2)
        bindings = {
            (
                record.find("field[@name='model']").text,
                record.find("field[@name='action_id']").get("ref"),
                record.find("field[@name='view_id']").get("ref"),
            )
            for record in records
        }
        self.assertEqual(
            bindings,
            {
                (
                    "sc.safety.issue",
                    "smart_construction_core.action_sc_safety_issue",
                    "smart_construction_core.view_sc_safety_issue_form",
                ),
                (
                    "sc.quality.acceptance",
                    "smart_construction_core.action_sc_product_quality_acceptance_v1",
                    "smart_construction_core.view_sc_quality_acceptance_form",
                ),
            },
        )
        for record in records:
            contract = record.find("field[@name='contract_json']").get("eval")
            self.assertIn("'composition_mode': 'entry_semantic_surface'", contract)
            self.assertIn("'sections':", contract)

        action_view_records = tree.findall(".//record[@model='ir.actions.act_window.view']")
        self.assertEqual(len(action_view_records), 2)
        self.assertEqual(
            {
                (
                    record.find("field[@name='act_window_id']").get("ref"),
                    record.find("field[@name='view_id']").get("ref"),
                    record.find("field[@name='view_mode']").text,
                )
                for record in action_view_records
            },
            {
                (
                    "smart_construction_core.action_sc_safety_issue",
                    "smart_construction_core.view_sc_safety_issue_form",
                    "form",
                ),
                (
                    "smart_construction_core.action_sc_product_quality_acceptance_v1",
                    "smart_construction_core.view_sc_quality_acceptance_form",
                    "form",
                ),
            },
        )

    def test_browser_verifier_requires_direct_edit_and_security_denial(self):
        source = (
            ROOT / "scripts/verify/frontend_quality_safety_domain_browser.mjs"
        ).read_text(encoding="utf-8")
        self.assertIn("presentationMode') === 'task'", source)
        self.assertIn("effectiveRecordCapabilities')?.write === true", source)
        self.assertIn("effectiveRenderProfile') === 'edit'", source)
        self.assertIn("editableFields > 0 && saveActions === 1", source)
        self.assertIn("passed through readonly", source)
        self.assertIn("url.pathname === '/access-denied'", source)
        self.assertIn("driverErrors", source)
        self.assertIn("data-v2-shadow-error", source)

    def test_browser_target_uses_formal_finance_security_principal(self):
        source = (
            ROOT / "scripts/verify/local_dev_quality_safety_domain_ids.py"
        ).read_text(encoding="utf-8")
        self.assertIn("smart_construction_demo.user_demo_role_finance", source)
        self.assertNotIn("user_demo_finance_read", source)

    def test_native_source_carries_resolved_form_view_into_structure_selection(self):
        assembler = (
            ROOT
            / "addons/smart_core/app_config_engine/services/assemblers/page_assembler.py"
        ).read_text(encoding="utf-8")
        handler = (
            ROOT / "addons/smart_core/handlers/ui_contract_v2.py"
        ).read_text(encoding="utf-8")
        self.assertIn('data["view_ids_by_type"] = resolved_view_ids_by_type', assembler)
        self.assertIn("vcfg.source_view_id.id", assembler)
        self.assertIn('resolved_view_ids.get("form")', handler)
        contract_assembler = (
            ROOT / "addons/smart_core/core/unified_page_contract_v2_assembler.py"
        ).read_text(encoding="utf-8")
        self.assertIn('field_type == "many2one" and relation == "res.users"', contract_assembler)

    def test_uses_only_current_formal_direct_entries(self):
        self.assertEqual(runtime.DOMAIN_KEY, "quality_safety")
        self.assertEqual(
            runtime.ROOT_MENU_XMLIDS,
            (
                "smart_construction_core.menu_sc_safety_issue",
                "smart_construction_core.menu_sc_product_quality_acceptance_v1",
            ),
        )
        self.assertNotIn(
            "smart_construction_core.menu_sc_quality_delivery_group_v2",
            runtime.ROOT_MENU_XMLIDS,
        )
        self.assertNotIn(
            "smart_construction_core.menu_sc_safety_delivery_group_v2",
            runtime.ROOT_MENU_XMLIDS,
        )
        self.assertEqual(runtime.OWNER_MODULE, "smart_construction_core")
        self.assertEqual(
            runtime.EXPECTED_ANCHORS,
            {
                "smart_construction_core.action_sc_safety_issue",
                "smart_construction_core.action_sc_product_quality_acceptance_v1",
            },
        )

    def test_collect_delegates_exact_multi_root_identity(self):
        expected = {"status": "PASS", "gaps": []}
        with patch.object(runtime, "collect_domain", return_value=expected) as collector:
            self.assertIs(runtime.collect(object()), expected)
        collector.assert_called_once_with(
            ANY,
            domain_key="quality_safety",
            root_menu_xmlids=runtime.ROOT_MENU_XMLIDS,
            owner_module=runtime.OWNER_MODULE,
            expected_anchors=runtime.EXPECTED_ANCHORS,
        )

    def test_reporter_emits_domain_title_without_database_identity(self):
        payload = {
            "schemaVersion": "frontend_domain_rollout.v1",
            "status": "PASS",
            "domain": "quality_safety",
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
        rendered = reporter.markdown(snapshot, "Quality-Safety Domain Frontend Rollout v1")
        self.assertIn("# Quality-Safety Domain Frontend Rollout v1", rendered)


if __name__ == "__main__":
    unittest.main()
