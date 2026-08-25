import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runtime = load_module(
    "frontend_project_domain_rollout",
    ROOT / "scripts/verify/frontend_project_domain_rollout.py",
)
reporter = load_module(
    "frontend_project_domain_rollout_report",
    ROOT / "scripts/verify/frontend_project_domain_rollout_report.py",
)


class TestFrontendProjectDomainRollout(unittest.TestCase):
    def test_standard_and_professional_surfaces_are_registered(self):
        self.assertEqual(runtime.classify_surface("tree", "")["semantic"], "table")
        self.assertEqual(runtime.classify_surface("kanban", "")["semantic"], "card")
        self.assertEqual(
            runtime.classify_surface("tree", "smart_hierarchy_browser"),
            {"semantic": "hierarchy_browser", "readiness": "ready", "reason": ""},
        )
        self.assertEqual(runtime.classify_surface("form", "")["readiness"], "structural")

    def test_unknown_smart_view_class_fails_closed(self):
        result = runtime.classify_surface("tree", "smart_unregistered_driver")
        self.assertEqual(result["readiness"], "fail_closed")
        self.assertEqual(result["reason"], "UNREGISTERED_SMART_VIEW_CLASS")

    def test_planned_native_modes_remain_explicit_readable_fallbacks(self):
        result = runtime.classify_surface("pivot", "")
        self.assertEqual(result["readiness"], "readable_fallback")
        self.assertEqual(result["reason"], "RENDERER_PIVOT_PLANNED")

    def test_snapshot_drops_database_identity_and_sorts_authority(self):
        payload = {
            "schemaVersion": "frontend_project_domain_rollout.v1",
            "status": "PASS",
            "domain": "project",
            "database": "must-not-leak",
            "root_menu_xmlid": runtime.ROOT_MENU_XMLID,
            "owner_module": runtime.OWNER_MODULE,
            "summary": {"action_count": 1},
            "actions": [
                {
                    "menu_xmlid": "module.menu",
                    "menu_name": "Menu",
                    "action_xmlid": "module.action",
                    "action_name": "Action",
                    "model": "x.model",
                    "view_mode": "tree,form",
                    "authority_groups": ["module.group_b", "module.group_a"],
                    "views": [
                        {
                            "view_type": "tree",
                            "view_xmlid": "module.view",
                            "js_class": "",
                            "semantic": "table",
                            "readiness": "ready",
                            "reason": "",
                        }
                    ],
                }
            ],
            "gaps": [],
        }
        snapshot = reporter.normalized_snapshot(payload)
        self.assertNotIn("database", snapshot)
        self.assertEqual(
            snapshot["actions"][0]["authorityGroups"],
            ["module.group_a", "module.group_b"],
        )
        self.assertIn("demo_addons", snapshot["excludedScopes"])

    def test_report_output_is_deterministic(self):
        snapshot = {
            "status": "PASS",
            "summary": {
                "action_count": 0,
                "model_count": 0,
                "ready_surface_count": 0,
                "readable_fallback_count": 0,
                "structural_form_count": 0,
                "fail_closed_count": 0,
                "gap_count": 0,
            },
            "actions": [],
            "gaps": [],
        }
        first = reporter.markdown(snapshot)
        second = reporter.markdown(json.loads(json.dumps(snapshot)))
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
