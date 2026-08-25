import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


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
    class Record:
        def __init__(self, record_id, xmlid, groups=(), parent=None):
            self.id = record_id
            self._xmlid_value = xmlid
            self.groups_id = list(groups)
            self.parent_id = parent

        def get_external_id(self):
            return {self.id: self._xmlid_value}

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
                    "authority": {
                        "semantics": "all_restricted_layers_must_match_one_group",
                        "menu_chain": [
                            {"menu_xmlid": "module.root", "groups": ["module.group_b", "module.group_a"]},
                            {"menu_xmlid": "module.menu", "groups": ["module.group_leaf"]},
                        ],
                        "action_groups": ["module.group_action_b", "module.group_action_a"],
                    },
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
            snapshot["actions"][0]["authority"]["menuChain"][0]["groups"],
            ["module.group_a", "module.group_b"],
        )
        self.assertEqual(
            snapshot["actions"][0]["authority"]["actionGroups"],
            ["module.group_action_a", "module.group_action_b"],
        )
        self.assertIn("demo_addons", snapshot["excludedScopes"])

    def test_authority_preserves_and_of_layers_and_requires_action_policy(self):
        root_group = self.Record(1, "module.group_root")
        leaf_group = self.Record(2, "module.group_leaf")
        action_group = self.Record(3, "module.group_action")
        root = self.Record(10, "module.root", [root_group])
        leaf = self.Record(11, "module.leaf", [leaf_group], root)
        action = SimpleNamespace(groups_id=[action_group])
        authority = runtime._authority_contract(leaf, action)
        self.assertEqual(
            authority,
            {
                "semantics": "all_restricted_layers_must_match_one_group",
                "menu_chain": [
                    {"menu_xmlid": "module.root", "groups": ["module.group_root"]},
                    {"menu_xmlid": "module.leaf", "groups": ["module.group_leaf"]},
                ],
                "action_groups": ["module.group_action"],
            },
        )
        self.assertEqual(runtime._authority_gaps("module.action", authority), [])
        authority["action_groups"] = []
        self.assertEqual(
            runtime._authority_gaps("module.action", authority)[0]["reason"],
            "FORMAL_ACTION_AUTHORITY_GROUP_MISSING",
        )

    def test_active_descendant_enumeration_is_recursive_and_ordered(self):
        class Cursor:
            def __init__(self):
                self.pending = []
                self.responses = {(9,): [(11,), (12,)], (11, 12): [(13,)], (13,): []}

            def execute(self, query, params):
                self.asserted_query = query
                self.pending = tuple(params[0])

            def fetchall(self):
                return self.responses[self.pending]

        env = SimpleNamespace(cr=Cursor())
        self.assertEqual(runtime._active_descendant_ids(env, 9), [11, 12, 13])

    def test_owner_and_anchor_boundaries_are_fail_closed(self):
        self.assertTrue(runtime._is_formal_owner("smart_construction_core.action_x"))
        self.assertFalse(runtime._is_formal_owner("demo_module.action_x"))
        actual = {"smart_construction_core.action_project_initiation"}
        missing = runtime.EXPECTED_ANCHORS - actual
        self.assertIn("smart_construction_core.action_exec_structure_wbs", missing)

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
