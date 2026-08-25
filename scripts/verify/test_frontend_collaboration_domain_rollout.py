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
    "frontend_collaboration_domain_rollout",
    ROOT / "scripts/verify/frontend_collaboration_domain_rollout.py",
)
reporter = load_module(
    "frontend_collaboration_domain_rollout_report",
    ROOT / "scripts/verify/frontend_collaboration_domain_rollout_report.py",
)


class TestFrontendCollaborationDomainRollout(unittest.TestCase):
    def test_notification_contract_is_bound_to_exact_action_and_view(self):
        tree = ET.parse(
            ROOT
            / "addons/smart_construction_core/data/mail_notification_product_contract.xml"
        )
        records = tree.findall(".//record[@model='ui.business.config.contract']")
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record.find("field[@name='model']").text, "mail.notification")
        self.assertEqual(
            record.find("field[@name='action_id']").get("ref"),
            "smart_construction_core.action_sc_product_message_notification_v1",
        )
        self.assertEqual(
            record.find("field[@name='view_id']").get("ref"),
            "smart_construction_core.view_sc_product_mail_notification_form",
        )
        contract = record.find("field[@name='contract_json']").get("eval")
        self.assertIn("'composition_mode': 'entry_semantic_surface'", contract)
        self.assertIn("'readonly': True", contract)
        self.assertIn("'name': 'action_sc_open_source'", contract)

        action_tree = ET.parse(
            ROOT
            / "addons/smart_construction_core/views/menu_product_contract_completion_v1.xml"
        )
        binding = action_tree.find(
            ".//record[@id='action_sc_product_message_notification_v1']"
        )
        self.assertIsNotNone(binding)
        self.assertEqual(
            binding.find("field[@name='res_model']").text,
            "mail.notification",
        )
        view_ids = binding.find("field[@name='view_ids']").get("eval")
        self.assertIn(
            "ref('smart_construction_core.view_sc_product_mail_notification_form')",
            view_ids,
        )
        self.assertIn("'view_mode': 'form'", view_ids)

    def test_uses_only_current_formal_collaboration_entry(self):
        self.assertEqual(runtime.DOMAIN_KEY, "collaboration")
        self.assertEqual(
            runtime.ROOT_MENU_XMLIDS,
            ("smart_construction_core.menu_sc_product_message_notification_v1",),
        )
        self.assertEqual(runtime.OWNER_MODULE, "smart_construction_core")
        self.assertEqual(
            runtime.EXPECTED_ANCHORS,
            {"smart_construction_core.action_sc_product_message_notification_v1"},
        )
        source = (ROOT / "scripts/verify/frontend_collaboration_domain_rollout.py").read_text(
            encoding="utf-8"
        )
        for inactive in (
            "menu_sc_project_collaboration_group_v2",
            "menu_sc_supply_collaboration_roadmap_v2",
            "menu_sc_bim_collaboration_roadmap_v2",
        ):
            self.assertNotIn(inactive, source)

    def test_collect_delegates_exact_identity(self):
        expected = {"status": "PASS", "gaps": []}
        form_runtime = {"presentation_mode": "task"}
        with (
            patch.object(runtime, "collect_domain", return_value=expected) as collector,
            patch.object(
                runtime,
                "collect_form_contract_runtime",
                return_value=form_runtime,
            ) as form_probe,
        ):
            self.assertIs(runtime.collect(object()), expected)
        collector.assert_called_once_with(
            ANY,
            domain_key="collaboration",
            root_menu_xmlids=runtime.ROOT_MENU_XMLIDS,
            owner_module=runtime.OWNER_MODULE,
            expected_anchors=runtime.EXPECTED_ANCHORS,
        )
        form_probe.assert_called_once_with(ANY)
        self.assertEqual(expected["form_contract_runtime"], form_runtime)

    def test_runtime_probe_uses_production_selector_and_v2_handler(self):
        source = (
            ROOT / "scripts/verify/frontend_collaboration_domain_rollout.py"
        ).read_text(encoding="utf-8")
        self.assertIn("._effective_view_orchestration_contracts(", source)
        self.assertIn("UiContractV2Handler(user_env", source)
        self.assertIn(
            '"smart_construction_core.business_config_contract_mail_notification_form_v1"',
            source,
        )
        self.assertIn('structure.get("presentationMode") != "task"', source)
        self.assertIn('effective_profile != "readonly"', source)

    def test_browser_verifier_uses_real_list_identity_and_security_denial(self):
        source = (
            ROOT / "scripts/verify/frontend_collaboration_domain_browser.mjs"
        ).read_text(encoding="utf-8")
        self.assertIn("model === 'mail.notification'", source)
        self.assertIn("tables === 1 || report.primary.result.emptyStates === 1", source)
        self.assertIn("url.pathname === '/access-denied'", source)
        self.assertIn("mutations.length === 0", source)

    def test_browser_target_uses_existing_governed_principals_without_writes(self):
        source = (
            ROOT / "scripts/verify/local_dev_collaboration_domain_ids.py"
        ).read_text(encoding="utf-8")
        self.assertIn("smart_construction_demo.sc_demo_user_test_admin", source)
        self.assertIn("smart_construction_demo.user_demo_role_finance", source)
        self.assertNotIn(".create(", source)
        self.assertNotIn(".write(", source)

    def test_reporter_emits_domain_title_without_database_identity(self):
        payload = {
            "schemaVersion": "frontend_domain_rollout.v1",
            "status": "PASS",
            "domain": "collaboration",
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
        rendered = reporter.markdown(snapshot, "Collaboration Domain Frontend Rollout v1")
        self.assertIn("# Collaboration Domain Frontend Rollout v1", rendered)

    def test_reporter_preserves_sanitized_exact_form_runtime_evidence(self):
        payload = {
            "schemaVersion": "frontend_domain_rollout.v1",
            "status": "PASS",
            "domain": "collaboration",
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
            "form_contract_runtime": {
                "action_xmlid": "module.action",
                "view_xmlid": "module.view",
                "selected_contract_xmlid": "module.contract",
                "presentation_mode": "task",
                "effective_render_profile": "readonly",
                "form_structure_authority": "entry_semantic_surface",
            },
        }
        snapshot = reporter.normalized_snapshot(payload)
        self.assertEqual(
            snapshot["formContractRuntime"]["selectedContractXmlid"],
            "module.contract",
        )
        rendered = reporter.markdown(
            snapshot, "Collaboration Domain Frontend Rollout v1"
        )
        self.assertIn("## Exact form Contract V2 runtime", rendered)
        self.assertIn("`readonly`", rendered)


if __name__ == "__main__":
    unittest.main()
