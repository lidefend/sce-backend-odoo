import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "delivery" / "scene_shell_compiler.py"
SPEC = importlib.util.spec_from_file_location("scene_shell_compiler_under_test", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
SceneShellCompiler = MODULE.SceneShellCompiler


def _leaf(
    menu_id,
    action_id,
    *,
    label,
    menu_xmlid,
    action_xmlid,
    route,
    scene_key="",
):
    return {
        "key": f"menu_{menu_id}",
        "label": label,
        "menu_id": menu_id,
        "action_id": action_id,
        "route": route,
        "scene_key": scene_key,
        "meta": {
            "menu_id": menu_id,
            "menu_xmlid": menu_xmlid,
            "action_id": action_id,
            "action_xmlid": action_xmlid,
            "model": "project.project",
            "view_modes": ["list", "form"],
            "route": route,
            "scene_key": scene_key,
        },
        "children": [],
    }


class SceneShellCompilerTests(unittest.TestCase):
    def setUp(self):
        self.compiler = SceneShellCompiler()

    def test_designed_scene_keeps_its_explicit_contract(self):
        nav = [{
            "key": "group:workspace",
            "label": "工作台",
            "children": [
                _leaf(
                    719,
                    962,
                    label="我的工作",
                    menu_xmlid="smart_construction_core.menu_sc_my_work",
                    action_xmlid="smart_construction_core.action_sc_my_work",
                    route="/a/962?menu_id=719",
                    scene_key="my_work.workspace",
                )
            ],
        }]
        result = self.compiler.compile(nav, designed_scene_keys={"my_work.workspace"})
        node = result.nav[0]["children"][0]
        self.assertEqual(node["scene_key"], "my_work.workspace")
        self.assertEqual(node["route"], "/s/my_work.workspace")
        self.assertEqual(node["content_kind"], "designed_scene")
        self.assertEqual(result.scene_shell_rows, [])

    def test_ordinary_action_page_gets_native_delegate_shell(self):
        nav = [{
            "key": "group:project",
            "label": "项目中心",
            "children": [
                _leaf(
                    379,
                    506,
                    label="项目台账",
                    menu_xmlid="smart_construction_core.menu_sc_project_project",
                    action_xmlid="smart_construction_core.action_sc_project_project",
                    route="/a/506?menu_id=379",
                )
            ],
        }]
        result = self.compiler.compile(nav, designed_scene_keys=set())
        node = result.nav[0]["children"][0]
        self.assertEqual(
            node["scene_key"],
            "entry.smart_construction_core.menu_sc_project_project",
        )
        self.assertEqual(
            node["route"],
            "/s/entry.smart_construction_core.menu_sc_project_project",
        )
        self.assertEqual(node["content_kind"], "native_delegate")
        self.assertEqual(
            node["entry_target"]["native_target"]["action_id"],
            506,
        )
        self.assertEqual(
            node["entry_target"]["native_target"]["menu_id"],
            379,
        )
        self.assertEqual(len(result.scene_shell_rows), 1)
        shell = result.scene_shell_rows[0]
        self.assertEqual(shell["target"]["action_id"], 506)
        self.assertEqual(shell["target"]["menu_id"], 379)
        self.assertNotIn("entry_intent", shell["target"])
        self.assertEqual(shell["meta"]["content_kind"], "native_delegate")

    def test_directory_has_no_published_path(self):
        nav = [{
            "key": "group:project",
            "label": "项目中心",
            "menu_id": 305,
            "route": "/m/305",
            "entry_target": {"type": "compatibility", "route": "/m/305"},
            "children": [
                _leaf(
                    379,
                    506,
                    label="项目台账",
                    menu_xmlid="smart_construction_core.menu_sc_project_project",
                    action_xmlid="smart_construction_core.action_sc_project_project",
                    route="/a/506?menu_id=379",
                )
            ],
        }]
        result = self.compiler.compile(nav, designed_scene_keys=set())
        directory = result.nav[0]
        self.assertEqual(directory["content_kind"], "container")
        self.assertNotIn("route", directory)
        self.assertNotIn("scene_key", directory)
        self.assertEqual(directory["children"][0]["content_kind"], "native_delegate")

    def test_unknown_scene_target_fails_closed(self):
        nav = [
            _leaf(
                714,
                962,
                label="我的工作",
                menu_xmlid="smart_construction_core.menu_sc_my_work",
                action_xmlid="smart_construction_core.action_sc_my_work",
                route="/a/962?menu_id=714",
                scene_key="my_work.workspace",
            )
        ]
        with self.assertRaisesRegex(ValueError, "explicitly designed scene contract"):
            self.compiler.compile(nav, designed_scene_keys=set())

    def test_generated_scene_key_is_deterministic(self):
        nav = [
            _leaf(
                379,
                506,
                label="项目台账",
                menu_xmlid="smart_construction_core.menu_sc_project_project",
                action_xmlid="smart_construction_core.action_sc_project_project",
                route="/a/506?menu_id=379",
            )
        ]
        first = self.compiler.compile(nav, designed_scene_keys=set())
        second = self.compiler.compile(nav, designed_scene_keys=set())
        self.assertEqual(first.nav[0]["scene_key"], second.nav[0]["scene_key"])

    def test_generated_shell_rows_merge_into_scene_ready_contract(self):
        nav = [
            _leaf(
                379,
                506,
                label="项目台账",
                menu_xmlid="smart_construction_core.menu_sc_project_project",
                action_xmlid="smart_construction_core.action_sc_project_project",
                route="/a/506?menu_id=379",
            )
        ]
        result = self.compiler.compile(nav, designed_scene_keys=set())
        contract = self.compiler.merge_scene_ready_contract(
            {"scenes": [], "meta": {"scene_count": 0}},
            result.scene_shell_rows,
        )
        self.assertEqual(len(contract["scenes"]), 1)
        self.assertEqual(contract["meta"]["scene_shell_count"], 1)
        self.assertEqual(contract["scenes"][0]["target"]["action_id"], 506)


if __name__ == "__main__":
    unittest.main()
