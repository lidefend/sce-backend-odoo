import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "delivery"
    / "runtime_capability_catalog.py"
)
SPEC = importlib.util.spec_from_file_location(
    "runtime_capability_catalog_under_test",
    MODULE_PATH,
)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
RuntimeCapabilityCatalogService = MODULE.RuntimeCapabilityCatalogService


class FakeGroup:
    def __init__(self, xmlid):
        self.id = abs(hash(xmlid)) % 100000
        self.xmlid = xmlid

    def get_external_id(self):
        return {self.id: self.xmlid}


class FakeAction:
    def __init__(
        self,
        action_id,
        *,
        xmlid="",
        res_model="project.project",
        view_mode="list,form",
        groups=None,
    ):
        self.id = action_id
        self._xmlid = xmlid
        self.res_model = res_model
        self.view_mode = view_mode
        self.groups_id = list(groups or [])
        self._name = "ir.actions.act_window"

    def get_external_id(self):
        return {self.id: self._xmlid}


class FakeMenu:
    def __init__(
        self,
        menu_id,
        name,
        *,
        xmlid="",
        parent=None,
        action=None,
        active=True,
        sequence=10,
        groups=None,
    ):
        self.id = menu_id
        self.name = name
        self._xmlid = xmlid
        self.parent_id = parent
        self.action = action
        self.active = active
        self.sequence = sequence
        self.groups_id = list(groups or [])
        self.child_id = []
        if parent is not None:
            parent.child_id.append(self)

    def get_external_id(self):
        return {self.id: self._xmlid}


class RuntimeCapabilityCatalogTests(unittest.TestCase):
    def setUp(self):
        self.root = FakeMenu(
            1,
            "智慧施工管理平台",
            xmlid="smart_construction_core.menu_sc_root",
        )
        self.center = FakeMenu(
            2,
            "项目中心",
            xmlid="smart_construction_core.menu_sc_project_center",
            parent=self.root,
        )
        self.group = FakeMenu(
            3,
            "项目管理",
            xmlid="smart_construction_core.menu_sc_project_management_group",
            parent=self.center,
        )
        self.action = FakeAction(
            20,
            xmlid="smart_construction_core.action_project_dashboard",
            groups=[FakeGroup("smart_construction_core.group_sc_cap_project_read")],
        )
        self.leaf = FakeMenu(
            4,
            "项目台账",
            xmlid="smart_construction_core.menu_sc_project_project",
            parent=self.group,
            action=self.action,
            groups=[FakeGroup("smart_construction_core.group_sc_entry_p01")],
        )
        self.service = RuntimeCapabilityCatalogService(env=None)

    def collect(self, **overrides):
        options = {
            "xmlid_prefix": "smart_construction_core.",
            "root_label": "智慧施工管理平台",
            "leaf_actions_only": True,
            "candidate_menus": [self.root, self.center, self.group, self.leaf],
        }
        options.update(overrides)
        return self.service.collect(**options)

    def test_native_identity_tuple_cannot_collide_at_xmlid_separator(self):
        left = MODULE.capability_identity(menu_id=1, menu_xmlid="m.a.b", action_id=2, action_xmlid="c.d")[0]
        right = MODULE.capability_identity(menu_id=3, menu_xmlid="m.a", action_id=4, action_xmlid="b.c.d")[0]
        self.assertNotEqual(left, right)

    def test_capability_identity_uses_native_entry_identity_without_route(self):
        projection = self.collect()
        self.assertEqual(len(projection.rows), 1)
        row = projection.rows[0]
        self.assertEqual(
            row["capability_key"],
            "native.entry.smart_construction_core.menu_sc_project_project."
            "smart_construction_core.action_project_dashboard",
        )
        self.assertTrue(row["identity_stable"])
        self.assertEqual(row["owner_module"], "smart_construction_core")
        self.assertEqual(row["menu_id"], 4)
        self.assertEqual(row["action_id"], 20)
        self.assertEqual(row["res_model"], "project.project")
        self.assertEqual(row["view_modes"], ["list", "form"])
        self.assertNotIn("route", row)

    def test_action_directory_is_not_a_leaf_capability(self):
        self.center.action = FakeAction(
            19,
            xmlid="smart_construction_core.action_center",
            res_model="project.project",
        )
        projection = self.collect()
        self.assertEqual(
            [row["menu_id"] for row in projection.rows],
            [4],
        )
        self.assertEqual(projection.diagnostics["skipped_container_count"], 1)

    def test_inactive_non_product_and_actionless_entries_are_excluded(self):
        inactive = FakeMenu(
            5,
            "停用页面",
            xmlid="smart_construction_core.menu_inactive",
            parent=self.group,
            action=FakeAction(21, xmlid="smart_construction_core.action_inactive"),
            active=False,
        )
        native = FakeMenu(
            6,
            "原生菜单",
            xmlid="project.menu_main_pm",
            action=FakeAction(22, xmlid="project.action_main"),
        )
        actionless = FakeMenu(
            7,
            "目录",
            xmlid="smart_construction_core.menu_actionless",
            parent=self.group,
        )
        projection = self.collect(
            candidate_menus=[
                self.root,
                self.center,
                self.group,
                self.leaf,
                inactive,
                native,
                actionless,
            ]
        )
        self.assertEqual([row["menu_id"] for row in projection.rows], [4])
        self.assertEqual(projection.diagnostics["skipped_inactive_count"], 1)
        self.assertEqual(projection.diagnostics["skipped_prefix_count"], 1)
        self.assertEqual(projection.diagnostics["skipped_no_action_count"], 4)

    def test_group_identity_comes_from_native_groups(self):
        row = self.collect().rows[0]
        self.assertEqual(
            row["menu_group_xmlids"],
            ["smart_construction_core.group_sc_entry_p01"],
        )
        self.assertEqual(
            row["action_group_xmlids"],
            ["smart_construction_core.group_sc_cap_project_read"],
        )
        self.assertTrue(
            row["source_authority"]["no_publication_authority"]
        )
        self.assertTrue(
            row["source_authority"]["no_tenant_authority"]
        )

    def test_same_label_and_model_keep_distinct_native_entries(self):
        other = FakeMenu(5, self.leaf.name, parent=self.group,
                         action=FakeAction(21))
        self.leaf._xmlid = ""
        self.action._xmlid = ""
        rows = self.collect(xmlid_prefix="", candidate_menus=[self.leaf, other]).rows
        self.assertEqual(len(rows), 2)
        self.assertNotEqual(rows[0]["capability_key"], rows[1]["capability_key"])
        self.assertEqual({r["identity_scope"] for r in rows}, {"current_database"})

    def test_module_scope_does_not_depend_on_root_title(self):
        before = self.collect(module="smart_construction_core").rows
        self.root.name = "Renamed root"
        after = self.collect(module="smart_construction_core").rows
        self.assertEqual([r["capability_key"] for r in before],
                         [r["capability_key"] for r in after])

    def test_missing_module_never_queries_all_menus(self):
        class Data:
            def sudo(self):
                return self
            def search(self, domain):
                return []
        class Env:
            def __getitem__(self, model):
                if model != "ir.model.data":
                    raise AssertionError("module lookup expanded to all menus")
                return Data()
        projection = RuntimeCapabilityCatalogService(Env()).collect(module="missing")
        self.assertEqual(projection.rows, [])
        self.assertEqual(projection.diagnostics["empty_reason"], "MODULE_HAS_NO_MENU_CANDIDATES")

    def test_product_policy_catalog_reuses_the_runtime_capability_projection(self):
        source = (
            Path(__file__).resolve().parents[1]
            / "delivery"
            / "product_policy_catalog_sync_service.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "RuntimeCapabilityCatalogService(source_env).collect(",
            source,
        )
        self.assertNotIn("def _candidate_user_menus(", source)
        self.assertNotIn("def _menu_path(", source)
        self.assertNotIn("def _action_model(", source)


if __name__ == "__main__":
    unittest.main()
