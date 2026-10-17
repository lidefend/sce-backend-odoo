"""Non-zero tests for the entry-target probe's pure violation rules."""
import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().with_name("local_dev_runtime_entry_target_probe.py")
SPEC = importlib.util.spec_from_file_location("entry_target_probe_under_test", MODULE_PATH)
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)


def _row(surface, route, root=""):
    return {"bucket": "admin_actions", "action_xmlid": "x", "menu_id": 1, "action_id": 2,
            "route": route, "root_menu_xmlid": root}


class TestEntryTargetViolations(unittest.TestCase):
    def test_complete_declaration_passes(self):
        found = {"business_config": _row("business_config", "/admin/business-config", "root.menu"),
                 "menu_config": _row("menu_config", "/admin/menu-config")}
        self.assertEqual(PROBE._violations(found), [])

    def test_missing_surface_is_a_violation(self):
        found = {"menu_config": _row("menu_config", "/admin/menu-config")}
        self.assertIn("missing admin_surface=business_config", PROBE._violations(found))

    def test_wrong_route_is_a_violation(self):
        found = {"business_config": _row("business_config", "/a/1", "root.menu"),
                 "menu_config": _row("menu_config", "/admin/menu-config")}
        self.assertIn("business_config route=/a/1 expected=/admin/business-config", PROBE._violations(found))

    def test_missing_root_menu_is_a_violation(self):
        found = {"business_config": _row("business_config", "/admin/business-config"),
                 "menu_config": _row("menu_config", "/admin/menu-config")}
        self.assertIn("business_config missing root_menu_xmlid", PROBE._violations(found))

    def test_undeclared_surface_is_a_violation(self):
        found = {"business_config": _row("business_config", "/admin/business-config", "root.menu"),
                 "menu_config": _row("menu_config", "/admin/menu-config"),
                 "other": _row("other", "/admin/other")}
        self.assertIn("undeclared admin_surface=other", PROBE._violations(found))

    def test_extra_surface_is_not_a_violation_when_only_required_set_is_checked(self):
        found = {"business_config": _row("business_config", "/admin/business-config", "root.menu"),
                 "menu_config": _row("menu_config", "/admin/menu-config")}
        expected = {"business_config": "/admin/business-config"}
        self.assertEqual(PROBE._violations(found, expected, reject_extra=False), [])

    def test_each_principal_declares_its_expected_surface_set(self):
        self.assertEqual(set(PROBE.EXPECTED_BY_PRINCIPAL[21]), {"business_config", "menu_config"})
        self.assertEqual(set(PROBE.EXPECTED_BY_PRINCIPAL[55]), {"business_config"})

    def test_relative_route_is_a_violation(self):
        found = {"business_config": _row("business_config", "admin/business-config", "root.menu"),
                 "menu_config": _row("menu_config", "/admin/menu-config")}
        self.assertIn("business_config route is not absolute: admin/business-config", PROBE._violations(found))

    def test_menu_only_denial_is_a_valid_denial_record(self):
        authority = {"denied_actions": [{
            "action_xmlid": "", "route_kind": "DENIED", "menu_id": 1004,
            "menu_xmlid": "smart_construction_core.menu_sc_root", "action_id": 0,
        }]}
        self.assertEqual(PROBE._denial_violations(authority), [])
        self.assertEqual(PROBE._denied_rows(authority)[0]["menu_id"], 1004)

    def test_denial_without_identity_is_a_violation(self):
        authority = {"denied_actions": [{
            "action_xmlid": "", "route_kind": "DENIED", "menu_id": 0,
            "menu_xmlid": "", "action_id": 0,
        }]}
        self.assertIn("denied_actions[0] has no action_xmlid or menu_xmlid", PROBE._denial_violations(authority))

    def test_denial_keeps_its_executable_route_kind_is_a_violation(self):
        # Publication filtering used to move an unpublished entry into
        # denied_actions while keeping its original route_kind.
        authority = {"denied_actions": [{
            "action_xmlid": "x.unreleased", "route_kind": "PRIMARY_NAV", "menu_id": 507, "action_id": 655,
        }]}
        self.assertIn("denied_actions[0] route_kind=PRIMARY_NAV", PROBE._denial_violations(authority))

    def test_partial_declaration_must_project_to_an_explicit_gap(self):
        from importlib import util as importlib_util
        path = Path(__file__).resolve().parents[2] / "addons/smart_core/core/navigation_entry_target.py"
        spec = importlib_util.spec_from_file_location("navigation_entry_target_probe_test", path)
        module = importlib_util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(PROBE._partial_declaration_violations(module.build_web_surface_entry_target), [])
        self.assertTrue(PROBE._partial_declaration_violations(lambda _: {}))

    def test_collector_reads_only_declared_admin_surface_targets(self):
        authority = {"primary_actions": [{"entry_target": {"type": "compatibility", "route": "/a/1"}}],
                     "admin_actions": [{"action_xmlid": "a", "entry_target": {
                         "type": "admin_surface", "surface": "menu_config", "route": "/admin/menu-config"}}]}
        found = PROBE._collect_admin_surfaces(authority)
        self.assertEqual(list(found), ["menu_config"])
        self.assertEqual(found["menu_config"]["bucket"], "admin_actions")


if __name__ == "__main__":
    unittest.main()
