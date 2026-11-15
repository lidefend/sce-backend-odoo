import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "services"
    / "platform_capability_explorer_contributions.py"
)
SPEC = importlib.util.spec_from_file_location(
    "platform_capability_explorer_contributions_under_test",
    MODULE_PATH,
)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ReleaseCenterContributionTests(unittest.TestCase):
    def test_release_center_maps_declared_native_menu_xmlid_without_name_guessing(self):
        source = {
            "product_contract": {
                "centers": [
                    {
                        "key": "project_management",
                        "name": "项目管理",
                        "sequence": 10,
                        "level_two": [
                            {
                                "binding": {
                                    "menu_xmlid": "smart_construction_core.menu_project_ledger"
                                }
                            }
                        ],
                    }
                ]
            }
        }
        centers, conflicts = MODULE._release_center_map(source)
        self.assertEqual(conflicts, [])
        self.assertEqual(
            centers["smart_construction_core.menu_project_ledger"]["key"],
            "project_management",
        )

    def test_conflicting_center_claims_do_not_overwrite_an_authority(self):
        leaf = {"binding": {"menu_xmlid": "smart_construction_core.menu_same"}}
        source = {
            "product_contract": {
                "centers": [
                    {
                        "key": "center.a",
                        "name": "A",
                        "sequence": 10,
                        "level_two": [leaf],
                    },
                    {
                        "key": "center.b",
                        "name": "B",
                        "sequence": 20,
                        "level_two": [leaf],
                    },
                ]
            }
        }
        centers, conflicts = MODULE._release_center_map(source)
        self.assertEqual(
            centers["smart_construction_core.menu_same"]["key"],
            "center.a",
        )
        self.assertEqual(conflicts[0]["kind"], "release_center")
        self.assertEqual(conflicts[0]["center_keys"], ["center.a", "center.b"])

    def test_contribution_is_orm_read_only(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        for forbidden in (".write(", ".create(", ".unlink(", ".sudo().create("):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)
        self.assertIn("get_platform_capability_explorer_scope", source)
        self.assertIn("get_platform_capability_explorer_contributions", source)


if __name__ == "__main__":
    unittest.main()
