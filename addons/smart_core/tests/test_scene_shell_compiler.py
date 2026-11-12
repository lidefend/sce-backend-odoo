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

    def native_leaf(self, xmlid="module.menu", action_id=20):
        return _leaf(10, action_id, label="Same label", menu_xmlid=xmlid,
                     action_xmlid="module.action", route=f"/a/{action_id}")

    def test_lossy_xmlids_have_distinct_stable_routes(self):
        nodes = [self.native_leaf(value) for value in
                 ("module.Menu", "module.menu", "module.a-b", "module.a_b", "module.x0_4d")]
        result = self.compiler.compile(nodes, designed_scene_keys=set())
        self.assertEqual(len({r["scene_key"] for r in result.nav}), len(nodes))
        reverse = self.compiler.compile(list(reversed(nodes)), designed_scene_keys=set())
        self.assertEqual({r["scene_key"] for r in result.nav}, {r["scene_key"] for r in reverse.nav})

    def test_same_native_target_can_be_reused_but_conflicting_target_cannot(self):
        node = self.native_leaf()
        result = self.compiler.compile([node, node], designed_scene_keys=set())
        self.assertEqual(len(result.nav), 2)
        self.assertEqual(len(result.scene_shell_rows), 1)
        with self.assertRaisesRegex(ValueError, "conflicting native targets"):
            self.compiler.compile([node, self.native_leaf(action_id=21)], designed_scene_keys=set())

    def test_database_local_menus_sharing_an_xmlid_action_remain_distinct(self):
        first = self.native_leaf("")
        second = self.native_leaf("")
        second["menu_id"] = 11
        second["meta"]["menu_id"] = 11
        result = self.compiler.compile([first, second], designed_scene_keys=set())
        self.assertEqual(len(set(result.native_delegate_scene_keys)), 2)

    def test_scene_ready_merge_rejects_a_designed_native_collision(self):
        result = self.compiler.compile([self.native_leaf()], designed_scene_keys=set())
        key = result.native_delegate_scene_keys[0]
        with self.assertRaisesRegex(ValueError, "conflicting execution meaning"):
            self.compiler.merge_scene_ready_contract({"scenes": [{"scene": {"key": key}, "target": {"action_id": 99}}]}, result.scene_shell_rows)

    def test_designed_native_collision_rejected_in_both_orders(self):
        native = self.native_leaf()
        designed = self.native_leaf("module.designed")
        designed["scene_key"] = "entry.module.menu"
        for nodes in ([native, designed], [designed, native]):
            with self.assertRaisesRegex(ValueError, "conflicting execution kinds"):
                self.compiler.compile(nodes, designed_scene_keys={"entry.module.menu"})

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
