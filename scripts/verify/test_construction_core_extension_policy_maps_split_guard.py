"""Source-bound regressions for the PR #800 native workspace fact migration."""
from __future__ import annotations

import ast
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from xml.etree import ElementTree as ET

from scripts.verify import construction_core_extension_policy_maps_split_guard as guard


class NativeWorkspaceFactGuardTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for relative in (
            'addons/smart_construction_core/__manifest__.py',
            'addons/smart_construction_core/views/support/my_work_views.xml',
            'addons/smart_construction_scene/core_extension.py',
            'addons/smart_construction_scene/profiles/scene_registry_content.py',
            'addons/smart_core/core/navigation_entry_target.py',
        ):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(guard.ROOT / relative, target)
        self.xml = self.root / 'addons/smart_construction_core/views/support/my_work_views.xml'
        self.maps = SimpleNamespace(CRITICAL_SCENE_TARGET_ROUTE_OVERRIDES={})

    def errors(self):
        return guard.my_work_fact_errors(self.root, self.maps)

    def test_real_native_fact_and_both_projections_pass(self):
        self.assertEqual([], self.errors())

    def test_mainline_operation_user_precedence_is_locked(self):
        module = guard._load(
            guard.POLICY_MAPS, "construction_core_policy_maps_precedence_test"
        )
        expected = (
            "system_admin",
            "experience",
            "business_config_admin",
            "business_full",
            "executive",
            "owner",
            "pm",
            "operation_user",
            "finance",
            "cost",
            "accounting",
        )
        self.assertEqual(expected, module.ROLE_PRECEDENCE)

    def test_maintained_native_name_is_consumed_without_route_or_map_changes(self):
        tree = ET.parse(self.xml)
        action = tree.find(".//record[@id='action_sc_my_work']")
        context = action.find("field[@name='context']")
        facts = ast.literal_eval(context.text)
        self.assertNotIn('sc_web_route', facts)
        action.find("field[@name='name']").text = 'Configured workspace'
        tree.write(self.xml, encoding='unicode')
        self.assertEqual([], self.errors())

    def test_legacy_context_route_is_rejected(self):
        tree = ET.parse(self.xml)
        field = tree.find(".//record[@id='action_sc_my_work']/field[@name='context']")
        facts = ast.literal_eval(field.text)
        facts['sc_web_route'] = '/my-work'
        field.text = repr(facts)
        tree.write(self.xml, encoding='unicode')
        self.assertTrue(any('forbidden' in error for error in self.errors()))

    def test_unloaded_native_declaration_is_rejected(self):
        path = self.root / 'addons/smart_construction_core/__manifest__.py'
        manifest = ast.literal_eval(path.read_text())
        manifest['data'].remove('views/support/my_work_views.xml')
        path.write_text(repr(manifest))
        self.assertTrue(any('manifest' in error for error in self.errors()))

    def test_menu_action_identity_must_be_preserved(self):
        tree = ET.parse(self.xml)
        tree.find(".//menuitem[@id='menu_sc_my_work']").set('action', 'unrelated.action')
        tree.write(self.xml, encoding='unicode')
        self.assertTrue(any('bind its declared action' in error for error in self.errors()))

    def test_restored_core_route_override_is_rejected(self):
        self.maps.CRITICAL_SCENE_TARGET_ROUTE_OVERRIDES['my_work.workspace'] = '/my-work'
        self.assertTrue(any('policy-map override' in error for error in self.errors()))

    def test_restored_scene_extension_override_is_rejected(self):
        path = self.root / 'addons/smart_construction_scene/core_extension.py'
        original = path.read_text()
        changed = original.replace('CRITICAL_SCENE_TARGET_ROUTE_OVERRIDES = {}',
                                   'CRITICAL_SCENE_TARGET_ROUTE_OVERRIDES = {"my_work.workspace": "/my-work"}')
        self.assertNotEqual(original, changed)
        path.write_text(changed)
        self.assertTrue(any('scene extension must not override' in error for error in self.errors()))

    def test_hardcoded_scene_route_or_name_fails_the_changed_fact_case(self):
        path = self.root / 'addons/smart_construction_scene/profiles/scene_registry_content.py'
        original = path.read_text()
        for expression, frozen in (('target["route"] = f"/s/{scene_key}"', 'target["route"] = "/my-work"'),
                                   ('fact.get("name") or "我的工作"', '"我的工作"')):
            with self.subTest(expression=expression):
                changed = original.replace(expression, frozen)
                self.assertNotEqual(original, changed)
                path.write_text(changed)
                self.assertTrue(self.errors())

    def test_hardcoded_runtime_route_is_rejected(self):
        path = self.root / 'addons/smart_core/core/navigation_entry_target.py'
        original = path.read_text()
        changed = original.replace('return f"{SCENE_ROUTE_PREFIX}{key}" if key else ""',
                                   'return "/my-work"', 1)
        self.assertNotEqual(original, changed)
        path.write_text(changed)
        self.assertTrue(any('derive the scene route' in error for error in self.errors()))


if __name__ == '__main__':
    unittest.main()
